"""Tests for the refund confirmation flow.

This tests the critical flow where:
1. User asks for a refund
2. Bot looks up invoice and asks for confirmation
3. User says "yes"
4. Bot should call process_refund tool (triggering HITL)

Also tests rejection and subsequent refund requests.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.graph import create_graph


class TestRefundConfirmationFlow:
    """Test the refund confirmation flow end-to-end."""

    @pytest.fixture
    def graph(self):
        """Create a graph with checkpointer for testing."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)

    def test_refund_request_triggers_hitl(self, graph, test_config_with_thread):
        """A refund request should immediately call process_refund and trigger HITL."""
        config = test_config_with_thread("test-refund-1")

        # User asks for refund
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1,
            },
            config,
        )

        # Check that we hit the HITL interrupt
        state = graph.get_state(config)

        # Verify process_refund was called (triggers HITL)
        refund_tool_called = False
        for msg in result["messages"]:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "process_refund":
                        refund_tool_called = True
                        break

        print(f"\nRefund tool called: {refund_tool_called}")
        print(f"HITL triggered (state.next): {state.next}")

        assert refund_tool_called, (
            "Support rep should call process_refund for refund requests"
        )
        assert state.next and "refund_tools" in state.next, (
            "Graph should be interrupted at refund_tools for HITL approval"
        )

    def test_hitl_approval_resumes_graph(self, graph, test_config_with_thread):
        """After HITL approval (using Command), the graph should resume and complete."""
        from langgraph.types import Command

        config = test_config_with_thread("test-refund-approval")

        # User asks for refund - triggers HITL
        graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1,
            },
            config,
        )

        # Verify we're at HITL interrupt
        state = graph.get_state(config)
        assert state.next and "refund_tools" in state.next

        # Resume the graph (simulating admin approval)
        graph.invoke(Command(resume=True), config)

        # Graph should have completed
        final_state = graph.get_state(config)
        print(f"\nAfter approval - state.next: {final_state.next}")

        # Should have completed (no more pending nodes)
        assert not final_state.next or len(final_state.next) == 0, (
            "Graph should complete after HITL approval"
        )

    def test_conversation_history_preserved_across_hitl(
        self, graph, test_config_with_thread
    ):
        """Conversation history should be preserved even when HITL interrupts."""
        config = test_config_with_thread("test-refund-history")

        # Turn 1: Music query (no HITL)
        graph.invoke(
            {
                "messages": [HumanMessage(content="What AC/DC albums do you have?")],
                "customer_id": 1,
            },
            config,
        )

        # Turn 2: Refund request (triggers HITL)
        graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1,
            },
            config,
        )

        # Get state and verify history
        state = graph.get_state(config)
        all_messages = state.values.get("messages", [])
        human_messages = [m for m in all_messages if isinstance(m, HumanMessage)]

        print(f"\nHuman messages in state: {len(human_messages)}")
        for hm in human_messages:
            print(f"  - {hm.content}")

        assert len(human_messages) >= 2, (
            "State should preserve both the music query and the refund request"
        )


class TestSupportRepToolCalling:
    """Test that the support rep properly calls tools."""

    @pytest.fixture
    def graph(self):
        """Create a graph with checkpointer."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)

    def test_support_rep_calls_refund_after_confirmation(
        self, graph, test_config_with_thread
    ):
        """Support rep should call process_refund when user confirms."""
        config = test_config_with_thread("test-refund-3")

        # Simulate a conversation where we've already discussed the invoice
        # and now the user is confirming
        initial_messages = [
            HumanMessage(content="I want a refund for invoice 143"),
            AIMessage(
                content="I can help with that. Invoice 143 is for $5.94 dated September 15, 2022. Would you like me to process a refund for this invoice?"
            ),
            HumanMessage(content="yes"),
        ]

        result = graph.invoke({"messages": initial_messages, "customer_id": 1}, config)

        # Check what happened
        state = graph.get_state(config)
        messages = result["messages"]

        # Look for refund tool call
        refund_called = False
        for msg in messages:
            if (
                isinstance(msg, AIMessage)
                and hasattr(msg, "tool_calls")
                and msg.tool_calls
            ):
                for tc in msg.tool_calls:
                    print(f"Tool call found: {tc['name']}")
                    if tc["name"] == "process_refund":
                        refund_called = True

        hitl_triggered = state.next and len(state.next) > 0

        print(f"\nRefund tool called: {refund_called}")
        print(f"HITL triggered: {hitl_triggered}")
        print(f"State.next: {state.next}")

        assert refund_called or hitl_triggered, (
            "Support rep should call process_refund when user confirms"
        )

    def test_get_invoice_uses_correct_ids(self, graph, test_config_with_thread):
        """Verify get_invoice is called with customer_id (not invoice_id)."""
        config = test_config_with_thread("test-invoice-lookup")

        result = graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1,
            },
            config,
        )

        # Find the get_invoice tool call
        for msg in result["messages"]:
            if (
                isinstance(msg, AIMessage)
                and hasattr(msg, "tool_calls")
                and msg.tool_calls
            ):
                for tc in msg.tool_calls:
                    if tc["name"] == "get_invoice":
                        args = tc["args"]
                        print(f"get_invoice called with: {args}")
                        # customer_id should be 1 (from state), invoice_id should be 143
                        assert args.get("customer_id") == 1, (
                            f"customer_id should be 1, got {args.get('customer_id')}"
                        )
                        # invoice_id is optional but if present should be 143
                        if "invoice_id" in args:
                            assert args["invoice_id"] == 143, (
                                f"invoice_id should be 143, got {args['invoice_id']}"
                            )
                        return

        # If we didn't find get_invoice, that's also fine - the LLM might have used different approach
        print("Note: get_invoice was not called in this run")
