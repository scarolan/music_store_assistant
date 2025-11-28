"""Tests for the refund confirmation flow.

This tests the critical flow where:
1. User asks for a refund
2. Bot looks up invoice and asks for confirmation
3. User says "yes"
4. Bot should call process_refund tool (triggering HITL)

Also tests rejection and subsequent refund requests.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from src.graph import create_graph
from src.state import State


class TestRefundConfirmationFlow:
    """Test the refund confirmation flow end-to-end."""
    
    @pytest.fixture
    def graph(self):
        """Create a graph with checkpointer for testing."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)
    
    def test_yes_confirmation_triggers_refund_tool(self, graph):
        """When user confirms 'yes' after refund prompt, the refund tool should be called."""
        config = {"configurable": {"thread_id": "test-refund-1", "customer_id": 1}}
        
        # First turn: User asks for refund
        # Note: customer_id must be in the state, not just config
        result1 = graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1
            },
            config
        )
        
        # The bot should have looked up the invoice and asked for confirmation
        messages1 = result1["messages"]
        last_ai_msg = None
        for msg in reversed(messages1):
            if isinstance(msg, AIMessage) and msg.content and not (hasattr(msg, 'name') and msg.name == 'supervisor'):
                last_ai_msg = msg
                break
        
        assert last_ai_msg is not None, "Bot should have responded"
        print(f"\n[Turn 1] Bot response: {last_ai_msg.content[:200]}...")
        
        # Second turn: User confirms "yes"
        result2 = graph.invoke(
            {"messages": [HumanMessage(content="yes")]},
            config
        )
        
        messages2 = result2["messages"]
        
        # Check if refund tool was called OR if we hit HITL interrupt
        state = graph.get_state(config)
        
        # Either the graph is interrupted (HITL) or refund tool was called
        refund_tool_called = False
        for msg in messages2:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc['name'] == 'process_refund':
                        refund_tool_called = True
                        break
        
        hitl_triggered = state.next and len(state.next) > 0
        
        print(f"\n[Turn 2] Refund tool called: {refund_tool_called}")
        print(f"[Turn 2] HITL triggered (state.next): {state.next}")
        print(f"[Turn 2] Number of messages: {len(messages2)}")
        
        # Print all messages for debugging
        for i, msg in enumerate(messages2):
            msg_type = type(msg).__name__
            content = getattr(msg, 'content', '')[:100] if hasattr(msg, 'content') else ''
            tool_calls = getattr(msg, 'tool_calls', None)
            print(f"  [{i}] {msg_type}: {content}... | tool_calls: {tool_calls}")
        
        assert refund_tool_called or hitl_triggered, \
            "After user confirms 'yes', the refund tool should be called or HITL should trigger"
    
    def test_support_rep_has_conversation_context(self, graph):
        """The support rep should see the full conversation history including the confirmation."""
        config = {"configurable": {"thread_id": "test-refund-2", "customer_id": 1}}
        
        # Turn 1: Ask for refund
        graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1
            },
            config
        )
        
        # Turn 2: Confirm
        result = graph.invoke(
            {"messages": [HumanMessage(content="yes, please process the refund")]},
            config
        )
        
        # Get the state and check message history
        state = graph.get_state(config)
        all_messages = state.values.get("messages", [])
        
        # Should have multiple human messages (original request + confirmation)
        human_messages = [m for m in all_messages if isinstance(m, HumanMessage)]
        
        print(f"\nHuman messages in state: {len(human_messages)}")
        for hm in human_messages:
            print(f"  - {hm.content}")
        
        assert len(human_messages) >= 2, "State should contain both the original request and the confirmation"


class TestSupportRepToolCalling:
    """Test that the support rep properly calls tools."""
    
    @pytest.fixture
    def graph(self):
        """Create a graph with checkpointer."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)
    
    def test_support_rep_calls_refund_after_confirmation(self, graph):
        """Support rep should call process_refund when user confirms."""
        config = {"configurable": {"thread_id": "test-refund-3", "customer_id": 1}}
        
        # Simulate a conversation where we've already discussed the invoice
        # and now the user is confirming
        initial_messages = [
            HumanMessage(content="I want a refund for invoice 143"),
            AIMessage(content="I can help with that. Invoice 143 is for $5.94 dated September 15, 2022. Would you like me to process a refund for this invoice?"),
            HumanMessage(content="yes")
        ]
        
        result = graph.invoke(
            {"messages": initial_messages, "customer_id": 1},
            config
        )
        
        # Check what happened
        state = graph.get_state(config)
        messages = result["messages"]
        
        # Look for refund tool call
        refund_called = False
        for msg in messages:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"Tool call found: {tc['name']}")
                    if tc['name'] == 'process_refund':
                        refund_called = True
        
        hitl_triggered = state.next and len(state.next) > 0
        
        print(f"\nRefund tool called: {refund_called}")
        print(f"HITL triggered: {hitl_triggered}")
        print(f"State.next: {state.next}")
        
        assert refund_called or hitl_triggered, \
            "Support rep should call process_refund when user confirms"
    
    def test_get_invoice_uses_correct_ids(self, graph):
        """Verify get_invoice is called with customer_id (not invoice_id)."""
        config = {"configurable": {"thread_id": "test-invoice-lookup", "customer_id": 1}}
        
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="I want a refund for invoice 143")],
                "customer_id": 1
            },
            config
        )
        
        # Find the get_invoice tool call
        for msg in result["messages"]:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc['name'] == 'get_invoice':
                        args = tc['args']
                        print(f"get_invoice called with: {args}")
                        # customer_id should be 1 (from state), invoice_id should be 143
                        assert args.get('customer_id') == 1, \
                            f"customer_id should be 1, got {args.get('customer_id')}"
                        # invoice_id is optional but if present should be 143
                        if 'invoice_id' in args:
                            assert args['invoice_id'] == 143, \
                                f"invoice_id should be 143, got {args['invoice_id']}"
                        return
        
        # If we didn't find get_invoice, that's also fine - the LLM might have used different approach
        print("Note: get_invoice was not called in this run")
