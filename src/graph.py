"""LangGraph definition for the Music Store Assistant.

This module defines the StateGraph with:
- Supervisor node: Routes user intent to appropriate worker
- Music_Expert node: Handles read-only catalog queries (supports Gemini or OpenAI)
- Support_Rep node: Handles sensitive account operations (with HITL for refunds)

Environment Variables:
- MUSIC_EXPERT_MODEL: Set to "gemini" to use Gemini, otherwise uses OpenAI (default)
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from src.state import State
from src.tools.music import MUSIC_TOOLS
from src.tools.support import (
    SUPPORT_TOOLS,
    SAFE_SUPPORT_TOOLS,
    HITL_SUPPORT_TOOLS,
    HITL_TOOLS,
)


# --- Prompts ---

SUPERVISOR_PROMPT = """You are the front-desk supervisor for Algorhythm, a music store.
Your job is to route customers to the right specialist based on their CURRENT request.

ROUTING OPTIONS:
- "music" - Questions about songs, albums, artists, genres, catalog browsing
- "support" - Account info, invoices, refunds, purchases, order history

ROUTING RULES (in priority order):
1. ALWAYS prioritize the LATEST message - if the user changes topics, follow the new topic
2. Route based on keywords in the LATEST message:
   - Music keywords: artist, album, song, track, genre, band, music, play, listen → "music"
   - Support keywords: refund, invoice, account, purchase, order, payment, receipt → "support"
3. ONLY use conversation history for AMBIGUOUS messages like "yes", "ok", "sure", "that one"
   - These should continue with whatever topic was being discussed
4. Greetings like "hi", "hello" → route to "support"

EXAMPLES:
- "I want a refund" → support
- "What Led Zeppelin albums do you have?" → music  
- [After discussing refunds] "Actually, what rock bands do you have?" → music (NEW topic)
- [After discussing music] "yes please" → music (continues previous topic)

You MUST always route to either "music" or "support". Never respond directly."""


MUSIC_EXPERT_PROMPT = """You are the Music Expert at Algorhythm music store.
Your specialty is helping customers discover and find music in OUR CATALOG ONLY.

CRITICAL: You can ONLY recommend music that exists in our database.
- You MUST use your tools to search before answering
- If a tool returns empty results, tell the customer we don't have that artist/album
- NEVER make up or guess album names - only report what the tools return
- NEVER use your general knowledge about music - ONLY use tool results

Your tools:
- get_albums_by_artist: Find all albums by an artist in our catalog
- get_tracks_by_artist: Find all songs/tracks by an artist in our catalog
- check_for_songs: Search for songs by title in our catalog
- get_artists_by_genre: Find artists by genre (rock, jazz, metal, blues, etc.)
- list_genres: Show all available genres in our catalog

WORKFLOW:
1. Customer mentions an artist → call get_albums_by_artist immediately
2. Customer asks about a genre → call get_artists_by_genre immediately  
3. Customer asks "what genres/music do you have?" → call list_genres
4. Customer asks for similar artists → use get_artists_by_genre with relevant genre
5. If tool returns results → share those specific results
6. If tool returns empty/no results → say "Sorry, we don't have that in our catalog"
7. NEVER respond about music without first calling a tool

Example: "I like Led Zeppelin, find similar artists" → call get_artists_by_genre("rock") to find other rock artists"""


SUPPORT_REP_PROMPT = """You are a Customer Support Representative at Algorhythm music store.
You handle account-related queries including profile information, invoices, and refunds.

AUTHENTICATION:
- The customer's ID is provided below from their authenticated session
- If the customer ID shows as "unknown", tell them: "Please log in to access your account information."
- NEVER ask the customer for their ID - it comes from their login session automatically

CUSTOMER ID vs INVOICE ID:
- CUSTOMER ID: Provided to you automatically (see below) - use this for get_customer_info and get_invoice
- INVOICE ID: The customer tells you this (e.g., "invoice 143") - use this for get_invoice and process_refund
- These are DIFFERENT numbers! Always use the correct ID for each parameter.

TOOLS (YOU MUST USE THESE - never pretend to do actions without calling the appropriate tool):
- get_customer_info(customer_id): Look up customer profile - use the customer_id from context
- get_invoice(customer_id, invoice_id): Look up a specific invoice
- process_refund(invoice_id): Process a refund (requires HITL approval)

CRITICAL WORKFLOW:
1. Customer asks about their account → MUST call get_customer_info with the customer_id from context
2. Customer asks about an invoice → MUST call get_invoice with customer_id AND the invoice_id they mention
3. Customer requests a refund (says "refund" + invoice number) → MUST call process_refund IMMEDIATELY
   - Do NOT look up the invoice first
   - Do NOT ask for confirmation
   - Just call process_refund(invoice_id) - the HITL system will handle approval

IMPORTANT: You cannot process refunds, look up accounts, or check invoices without calling the appropriate tool.
Never say "I've initiated" or "I'll process" without actually calling the tool first.

Be helpful and empathetic, especially when handling complaints or refund requests."""


# --- Router Schema ---


class RouteDecision(BaseModel):
    """Decision on how to route the customer's request."""

    reasoning: str = Field(description="Brief explanation of why this route was chosen")
    route: Literal["music", "support"] = Field(
        description="Where to route: 'music' for catalog/artist queries, 'support' for account/invoices/refunds/general"
    )


# --- Node Functions ---


def create_supervisor_node(model: ChatOpenAI):
    """Create the supervisor node that routes requests."""

    def supervisor(state: State) -> dict:
        """Route the user's request to the appropriate worker."""
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]

        # Use structured output for routing decision
        router_model = model.with_structured_output(RouteDecision)
        decision = router_model.invoke(messages)

        # Add a routing note (will be skipped in output extraction)
        routing_msg = AIMessage(
            content=f"[Routing to {decision.route}: {decision.reasoning}]",
            name="supervisor",
        )

        return {"messages": [routing_msg], "route": decision.route}

    return supervisor


def create_music_expert_node(model: BaseChatModel):
    """Create the music expert node.

    Args:
        model: The LLM to use for music queries (can be OpenAI or Gemini).
    """
    music_model = model.bind_tools(MUSIC_TOOLS)

    def music_expert(state: State) -> dict:
        """Handle music catalog queries."""
        messages = [SystemMessage(content=MUSIC_EXPERT_PROMPT)] + state["messages"]
        response = music_model.invoke(messages)
        return {"messages": [response]}

    return music_expert


def create_support_rep_node(model: ChatOpenAI):
    """Create the support rep node."""
    support_model = model.bind_tools(SUPPORT_TOOLS)

    def support_rep(state: State) -> dict:
        """Handle account and support queries."""
        # Inject customer context into the prompt
        customer_id = state.get("customer_id", "unknown")
        context_prompt = f"{SUPPORT_REP_PROMPT}\n\nCurrent customer ID: {customer_id}"

        messages = [SystemMessage(content=context_prompt)] + state["messages"]
        response = support_model.invoke(messages)
        return {"messages": [response]}

    return support_rep


# --- Routing Logic ---


def route_supervisor(state: State) -> Literal["music_expert", "support_rep"]:
    """Route from supervisor to the appropriate worker."""
    route = state.get("route", "support")  # Default to support

    if route == "music":
        return "music_expert"
    else:
        return "support_rep"


def should_continue_music(state: State) -> Literal["music_tools", "__end__"]:
    """Check if music expert needs to call tools or is done."""
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "music_tools"
    return "__end__"


def should_continue_support(
    state: State,
) -> Literal["support_tools", "support_hitl", "__end__"]:
    """Check if support rep needs tools, HITL approval, or is done."""
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # Check if any tool call requires HITL
        for tool_call in last_message.tool_calls:
            if tool_call["name"] in HITL_TOOLS:
                return "support_hitl"
        return "support_tools"
    return "__end__"


def route_after_tools(state: State) -> Literal["music_expert", "support_rep"]:
    """Route back to the appropriate worker after tool execution."""
    # Look for the last AI message with a name to determine which worker was active
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and hasattr(msg, "name"):
            if msg.name == "music_expert":
                return "music_expert"
            elif msg.name == "support_rep":
                return "support_rep"

    # Default based on tool type in last tool message
    return "support_rep"


# --- Graph Factory ---


def get_music_expert_model() -> BaseChatModel:
    """Get the model for the music expert based on environment config.

    Set MUSIC_EXPERT_MODEL=gemini to use Google Gemini.
    Defaults to OpenAI GPT-4o.
    """
    model_choice = os.getenv("MUSIC_EXPERT_MODEL", "openai").lower()

    if model_choice == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            print("🎵 Music Expert: Using Gemini (gemini-2.0-flash)")
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0.7,  # Slightly creative for music recommendations
            )
        except ImportError:
            print("⚠️ langchain-google-genai not installed, falling back to OpenAI")
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    else:
        print("🎵 Music Expert: Using OpenAI (gpt-4o-mini)")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


def create_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """Create and compile the customer support graph.

    Args:
        checkpointer: Optional checkpointer for persistence and HITL support.

    Returns:
        Compiled StateGraph ready for invocation.

    Environment Variables:
        MUSIC_EXPERT_MODEL: Set to "gemini" to use Gemini for music queries.
    """
    # Initialize models
    # Supervisor uses cheaper model - routing is simple classification
    supervisor_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Support Rep uses GPT-4o for complex customer interactions
    support_model = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

    # Music Expert can use Gemini or OpenAI based on config
    music_model = get_music_expert_model()

    # Create the graph
    builder = StateGraph(State)

    # Add nodes
    builder.add_node("supervisor", create_supervisor_node(supervisor_model))
    builder.add_node("music_expert", create_music_expert_node(music_model))
    builder.add_node("support_rep", create_support_rep_node(support_model))
    builder.add_node("music_tools", ToolNode(MUSIC_TOOLS))
    builder.add_node("support_tools", ToolNode(SAFE_SUPPORT_TOOLS))
    builder.add_node(
        "refund_tools", ToolNode(HITL_SUPPORT_TOOLS)
    )  # Separate node for HITL

    # Set entry point
    builder.set_entry_point("supervisor")

    # Add edges from supervisor (always routes to a worker, never ends directly)
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "music_expert": "music_expert",
            "support_rep": "support_rep",
        },
    )

    # Add edges from music expert
    builder.add_conditional_edges(
        "music_expert",
        should_continue_music,
        {
            "music_tools": "music_tools",
            END: END,
        },
    )

    # Add edges from support rep (with HITL check)
    builder.add_conditional_edges(
        "support_rep",
        should_continue_support,
        {
            "support_tools": "support_tools",
            "support_hitl": "refund_tools",  # Route to separate HITL node
            END: END,
        },
    )

    # Add edges from tools back to workers
    builder.add_edge("music_tools", "music_expert")
    builder.add_edge("support_tools", "support_rep")
    builder.add_edge(
        "refund_tools", "support_rep"
    )  # Refund tools also return to support_rep

    # Compile with optional checkpointer and HITL interrupt
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
        # Only interrupt before refund_tools, not all support tools
        compile_kwargs["interrupt_before"] = ["refund_tools"]

    return builder.compile(**compile_kwargs)
