"""LangGraph definition for the Music Store Assistant.

This module defines the StateGraph with:
- Supervisor node: Routes user intent to appropriate worker
- Music_Expert node: Handles read-only catalog queries (supports Gemini or OpenAI)
- Support_Rep node: Handles sensitive account operations (with HITL for refunds)

Environment Variables:
- MUSIC_EXPERT_MODEL: Set to "gemini" to use Gemini, otherwise uses OpenAI (default)
"""

import os
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from src.state import State
from src.tools.music import MUSIC_TOOLS
from src.tools.support import SUPPORT_TOOLS, SAFE_SUPPORT_TOOLS, HITL_SUPPORT_TOOLS, HITL_TOOLS, get_customer_info, get_invoice, process_refund


# Separate tools into safe and HITL-requiring
SAFE_SUPPORT_TOOLS = [get_customer_info, get_invoice]
HITL_SUPPORT_TOOLS = [process_refund]


# --- Prompts ---

SUPERVISOR_PROMPT = """You are the front-desk supervisor for Algorhythm, a music store.
Your job is to understand customer needs and route them to the right specialist.

ROUTING OPTIONS:
- "music" - Questions about songs, albums, artists, catalog browsing
- "support" - Account info, invoices, refunds, purchases, order history, confirmations

CRITICAL RULES:
1. Look at the ENTIRE conversation history, not just the last message
2. If previous messages discuss refunds, invoices, or purchases → route to "support"
3. If previous messages discuss music, songs, or artists → route to "music"
4. Short confirmations like "yes", "ok", "please", "that one" → continue the SAME topic as before
5. Greetings and general questions → route to "support" (they can handle general inquiries)

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

IMPORTANT - Customer ID vs Invoice ID:
- The CUSTOMER ID is provided to you in the context below (from their authenticated session)
- The INVOICE ID is what the customer mentions when requesting a refund (e.g., "invoice 143")
- These are DIFFERENT numbers! Always use the correct ID for each parameter.

For refunds:
1. Use get_invoice with the customer_id AND invoice_id to look up the specific invoice
2. If customer confirms, call process_refund with the invoice_id
3. When customer says "yes" or confirms, IMMEDIATELY call process_refund - don't ask again

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
            name="supervisor"
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
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "music_tools"
    return END


def should_continue_support(state: State) -> Literal["support_tools", "support_hitl", "__end__"]:
    """Check if support rep needs tools, HITL approval, or is done."""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check if any tool call requires HITL
        for tool_call in last_message.tool_calls:
            if tool_call["name"] in HITL_TOOLS:
                return "support_hitl"
        return "support_tools"
    return END


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


def create_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Create and compile the customer support graph.
    
    Args:
        checkpointer: Optional checkpointer for persistence and HITL support.
        
    Returns:
        Compiled StateGraph ready for invocation.
    
    Environment Variables:
        MUSIC_EXPERT_MODEL: Set to "gemini" to use Gemini for music queries.
    """
    # Initialize models
    # Supervisor and Support Rep always use GPT-4o for reliability
    openai_model = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    
    # Music Expert can use Gemini or OpenAI based on config
    music_model = get_music_expert_model()
    
    # Create the graph
    builder = StateGraph(State)
    
    # Add nodes
    builder.add_node("supervisor", create_supervisor_node(openai_model))
    builder.add_node("music_expert", create_music_expert_node(music_model))
    builder.add_node("support_rep", create_support_rep_node(openai_model))
    builder.add_node("music_tools", ToolNode(MUSIC_TOOLS))
    builder.add_node("support_tools", ToolNode(SAFE_SUPPORT_TOOLS))
    builder.add_node("refund_tools", ToolNode(HITL_SUPPORT_TOOLS))  # Separate node for HITL
    
    # Set entry point
    builder.set_entry_point("supervisor")
    
    # Add edges from supervisor (always routes to a worker, never ends directly)
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "music_expert": "music_expert",
            "support_rep": "support_rep"
        }
    )
    
    # Add edges from music expert
    builder.add_conditional_edges(
        "music_expert",
        should_continue_music,
        {
            "music_tools": "music_tools",
            END: END
        }
    )
    
    # Add edges from support rep (with HITL check)
    builder.add_conditional_edges(
        "support_rep",
        should_continue_support,
        {
            "support_tools": "support_tools",
            "support_hitl": "refund_tools",  # Route to separate HITL node
            END: END
        }
    )
    
    # Add edges from tools back to workers
    builder.add_edge("music_tools", "music_expert")
    builder.add_edge("support_tools", "support_rep")
    builder.add_edge("refund_tools", "support_rep")  # Refund tools also return to support_rep
    
    # Compile with optional checkpointer and HITL interrupt
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
        # Only interrupt before refund_tools, not all support tools
        compile_kwargs["interrupt_before"] = ["refund_tools"]
    
    return builder.compile(**compile_kwargs)
