"""Tests for the state schema."""

import pytest
from typing import get_type_hints


class TestStateSchema:
    """Tests for the State TypedDict schema."""
    
    def test_state_has_messages_field(self):
        """State should have a messages field."""
        from src.state import State
        
        hints = get_type_hints(State)
        assert "messages" in hints, "State must have a 'messages' field"

    def test_state_has_customer_id_field(self):
        """State should have a customer_id field for authenticated sessions."""
        from src.state import State
        
        hints = get_type_hints(State)
        assert "customer_id" in hints, "State must have a 'customer_id' field"

    def test_state_messages_uses_add_messages_reducer(self):
        """Messages field should use the add_messages reducer for proper history management."""
        from src.state import State
        from typing import get_type_hints, Annotated
        import typing
        
        # Check that messages is annotated (which indicates a reducer)
        annotations = State.__annotations__
        assert "messages" in annotations
        
        # The annotation should be Annotated with add_messages
        msg_annotation = annotations["messages"]
        assert hasattr(msg_annotation, "__metadata__"), "messages should use Annotated type with reducer"
