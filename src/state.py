"""State schema for the Music Store Assistant graph.

This module defines the TypedDict state that flows through the LangGraph,
and the CustomerContext dataclass for secure runtime context injection.

SECURITY NOTE: customer_id is passed via context_schema (Runtime context),
NOT in state. This prevents LLM manipulation while allowing Studio to
configure it via Assistants.
"""

from dataclasses import dataclass
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


@dataclass
class CustomerContext:
    """Runtime context for authenticated customer sessions.

    This context is injected at runtime via graph.invoke(..., context={...})
    and is accessible to nodes via Runtime and tools via ToolRuntime.

    It is NOT part of the graph state and cannot be modified by the LLM.

    Attributes:
        customer_id: The authenticated customer's ID (simulates JWT claim).
    """

    customer_id: int = 1  # Default for demo purposes


class State(TypedDict):
    """State schema for the customer support graph.

    Attributes:
        messages: Conversation history with add_messages reducer for proper merging.
        route: Internal routing decision from supervisor (music, support, respond).

    Note:
        customer_id is NOT in state - it's in CustomerContext for security.
    """

    messages: Annotated[list, add_messages]
    route: str
