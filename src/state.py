"""State schema for the Music Store Assistant graph.

This module defines the TypedDict state that flows through the LangGraph.
The customer_id is injected via configuration to simulate an authenticated session.
"""

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """State schema for the customer support graph.
    
    Attributes:
        messages: Conversation history with add_messages reducer for proper merging.
        customer_id: The authenticated customer's ID (injected via config, simulates JWT).
        route: Internal routing decision from supervisor (music, support, respond).
    """
    messages: Annotated[list, add_messages]
    customer_id: int
    route: str
