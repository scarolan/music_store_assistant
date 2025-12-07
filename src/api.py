"""FastAPI backend for the Music Store Assistant chat interface."""

import os
import uuid
from typing import Optional

# Load environment variables FIRST, before any LangChain/LangGraph imports
# This ensures LANGCHAIN_PROJECT is set before LangSmith tracing initializes
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver

from src.graph import create_graph

# Initialize the app
app = FastAPI(
    title="Algorhythm Music Store Assistant",
    description="Customer support chatbot for the Algorhythm music store",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared checkpointer for HITL support
checkpointer = MemorySaver()

# Create the graph with checkpointer
graph = create_graph(checkpointer=checkpointer)

# Track pending approvals for admin dashboard
# In production, this would be in a database
pending_approvals: dict[str, dict] = {}

# Store the last response for rejected threads (since we don't resume the graph)
rejected_responses: dict[str, str] = {}


def build_config(thread_id: str, customer_id: int) -> dict:
    """Build a config dict for graph invocation.

    Note: customer_id is passed separately via context= parameter (context_schema),
    NOT in configurable. This keeps it secure from LLM manipulation.

    Adds source and environment tags for LangSmith filtering:
    - source:webui - identifies requests from the web interface
    - test - added when LANGSMITH_TEST_MODE is set
    - ci-cd - added via LANGCHAIN_TAGS when running in GitHub Actions
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "run_name": "music_store_assistant_webui",  # Shows in LangSmith Name column
    }

    tags = ["source:webui"]  # Always tag web UI requests

    # Add test tag when in test mode
    if os.getenv("LANGSMITH_TEST_MODE"):
        tags.append("test")

    # Add additional tags from environment (e.g., 'ci-cd' from GitHub Actions)
    extra_tags = os.getenv("LANGCHAIN_TAGS", "")
    if extra_tags:
        tags.extend(tag.strip() for tag in extra_tags.split(",") if tag.strip())

    config["tags"] = tags

    return config


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    message: str
    thread_id: Optional[str] = None
    customer_id: int = 16  # Default customer for demo


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""

    response: str
    thread_id: str
    requires_approval: bool = False
    pending_tool: Optional[str] = None


class ApproveResponse(BaseModel):
    """Response body for the /approve endpoint."""

    response: str
    thread_id: str


# --- Helper Functions ---


def extract_assistant_response(result: dict) -> str:
    """Extract the last assistant message from the graph result.

    Uses LangChain v1's standard content_blocks API for provider-agnostic
    access to message content (works with OpenAI, Gemini, Anthropic, etc.)
    """
    from langchain_core.messages import AIMessage

    messages = result.get("messages", [])
    for msg in reversed(messages):
        # Only look at AI messages
        if not isinstance(msg, AIMessage):
            continue
        # Skip routing messages from supervisor
        if hasattr(msg, "name") and msg.name == "supervisor":
            continue
        # Extract text using standard content_blocks API (LangChain v1)
        if hasattr(msg, "content_blocks") and msg.content_blocks:
            text_parts = [
                block.get("text", "")
                for block in msg.content_blocks
                if block.get("type") == "text"
            ]
            if text_parts:
                return "".join(text_parts)
        # Fallback for simple string content
        if msg.content and isinstance(msg.content, str):
            return msg.content
    return "I'm not sure how to help with that."


def check_pending_approval(
    thread_id: str, customer_id: int
) -> tuple[bool, Optional[str]]:
    """Check if a thread has a pending HITL approval.

    Only checks our active tracking - use check_graph_interrupted for graph state.
    """
    # Only check our active pending approvals tracking
    if thread_id in pending_approvals:
        return True, "process_refund"

    return False, None


def check_graph_interrupted(
    thread_id: str, customer_id: int
) -> tuple[bool, Optional[str]]:
    """Check if the graph is currently interrupted (after invoke)."""
    config = build_config(thread_id, customer_id)
    state = graph.get_state(config)

    if state and state.next:
        return True, "process_refund"

    return False, None


# --- Endpoints ---


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Handle a chat message from the user."""
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())

    config = build_config(thread_id, request.customer_id)

    # Check if there's already a pending approval for this thread
    pending, tool = check_pending_approval(thread_id, request.customer_id)
    if pending:
        return ChatResponse(
            response="⚠️ There's a pending refund request that needs approval. Please approve or reject it first.",
            thread_id=thread_id,
            requires_approval=True,
            pending_tool=tool,
        )

    # Invoke the graph
    # NOTE: customer_id is passed via context= (secure, not in state)
    # The graph uses context_schema=CustomerContext to receive it
    try:
        result = graph.invoke(
            {
                "messages": [("user", request.message)],
            },
            config,
            context={"customer_id": request.customer_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Check if the graph was interrupted (HITL) - use graph state check here
    interrupted, tool = check_graph_interrupted(thread_id, request.customer_id)

    if interrupted:
        # Track this pending approval for admin dashboard
        pending_approvals[thread_id] = {
            "thread_id": thread_id,
            "customer_id": request.customer_id,
            "tool": tool,
        }
        return ChatResponse(
            response="🔒 **Refund Request Requires Approval**\n\nI've prepared the refund request. A supervisor needs to approve this action before it can be processed.\n\n⏳ Waiting for supervisor approval...",
            thread_id=thread_id,
            requires_approval=True,
            pending_tool=tool,
        )

    # Extract and return the response
    response_text = extract_assistant_response(result)

    return ChatResponse(
        response=response_text, thread_id=thread_id, requires_approval=False
    )


@app.post("/approve/{thread_id}", response_model=ApproveResponse)
def approve_action(thread_id: str, customer_id: int = 16):
    """Approve a pending HITL action and continue the graph."""
    config = build_config(thread_id, customer_id)

    # Check if there's actually something pending
    pending, _ = check_pending_approval(thread_id, customer_id)
    if not pending:
        raise HTTPException(
            status_code=400, detail="No pending approval for this thread"
        )

    # Resume the graph (pass None to continue with existing state)
    # NOTE: Must also pass context= when resuming for tools to access customer_id
    try:
        result = graph.invoke(None, config, context={"customer_id": customer_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Remove from pending approvals
    pending_approvals.pop(thread_id, None)

    response_text = extract_assistant_response(result)

    return ApproveResponse(
        response=f"✅ **Approved!**\n\n{response_text}", thread_id=thread_id
    )


@app.post("/reject/{thread_id}", response_model=ApproveResponse)
def reject_action(thread_id: str, customer_id: int = 16):
    """Reject a pending HITL action."""
    # Check if there's actually something pending
    pending, _ = check_pending_approval(thread_id, customer_id)
    if not pending:
        raise HTTPException(
            status_code=400, detail="No pending approval for this thread"
        )

    # Remove from pending approvals
    pending_approvals.pop(thread_id, None)

    # For rejection, we don't resume the graph - just return a canned response
    # This avoids confusing the LLM with fake user messages
    rejection_message = "We're sorry, but we are unable to provide a refund for this order. If you believe this is an error, please contact our customer service team for further assistance."

    # Store the rejection response so the polling endpoint can find it
    rejected_responses[thread_id] = rejection_message

    return ApproveResponse(response=rejection_message, thread_id=thread_id)


# --- Admin Endpoints ---


@app.get("/admin/pending")
def get_pending_approvals():
    """Get all pending approvals for the admin dashboard."""
    return {"pending": list(pending_approvals.values())}


@app.get("/status/{thread_id}")
def get_thread_status(thread_id: str, customer_id: int = 16):
    """Check the status of a thread (for customer polling)."""

    # First check if this thread was rejected (we stored a canned response)
    if thread_id in rejected_responses:
        # Don't pop - keep returning the rejection until client stops polling
        return {"status": "completed", "message": rejected_responses[thread_id]}

    # Check if actively pending approval in our tracking
    if thread_id in pending_approvals:
        return {"status": "pending", "message": "⏳ Waiting for supervisor approval..."}

    # Check the graph state
    config = build_config(thread_id, customer_id)
    state = graph.get_state(config)

    # If graph has no state, thread doesn't exist
    if not state or not state.values.get("messages"):
        return {"status": "unknown", "message": "Thread not found"}

    # If graph has no pending next steps, it's completed
    if not state.next:
        response_text = extract_assistant_response(state.values)
        return {"status": "completed", "message": response_text}

    # Graph has pending next steps but not in our tracking -
    # This is a stale interrupt (was rejected but graph still shows interrupted)
    # Return completed with a generic message
    return {
        "status": "completed",
        "message": "Your request has been processed. Is there anything else I can help you with?",
    }


@app.get("/admin")
def serve_admin():
    """Serve the admin dashboard."""
    return FileResponse("static/admin.html")


@app.get("/favicon.ico")
def serve_favicon():
    """Serve the favicon."""
    return FileResponse("static/favicon.ico")


# Serve static files (will add the HTML frontend here)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")
