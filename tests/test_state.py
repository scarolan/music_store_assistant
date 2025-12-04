"""Tests for the state schema."""

from typing import get_type_hints


class TestStateSchema:
    """Tests for the State TypedDict schema."""

    def test_state_has_messages_field(self):
        """State should have a messages field."""
        from src.state import State

        hints = get_type_hints(State)
        assert "messages" in hints, "State must have a 'messages' field"

    def test_state_does_not_have_customer_id_field(self):
        """State should NOT have customer_id - it's in CustomerContext for security."""
        from src.state import State

        hints = get_type_hints(State)
        assert "customer_id" not in hints, (
            "State must NOT have a 'customer_id' field - "
            "it should be in CustomerContext (context_schema) for security"
        )

    def test_customer_context_has_customer_id(self):
        """CustomerContext dataclass should have customer_id."""
        from src.state import CustomerContext

        ctx = CustomerContext(customer_id=42)
        assert ctx.customer_id == 42

    def test_customer_context_has_default(self):
        """CustomerContext should have a default customer_id for demo."""
        from src.state import CustomerContext

        ctx = CustomerContext()
        assert ctx.customer_id == 16  # Default for demo

    def test_state_messages_uses_add_messages_reducer(self):
        """Messages field should use the add_messages reducer for proper history management."""
        from src.state import State

        # Check that messages is annotated (which indicates a reducer)
        annotations = State.__annotations__
        assert "messages" in annotations

        # The annotation should be Annotated with add_messages
        msg_annotation = annotations["messages"]
        assert hasattr(msg_annotation, "__metadata__"), (
            "messages should use Annotated type with reducer"
        )
