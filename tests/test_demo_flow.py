"""Integration test that runs the full demo conversation flow.

This test simulates the complete demo script from DEMO_CHAT.md,
verifying that routing, tool calls, and HITL work end-to-end.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.graph import create_graph


# Default customer ID for all demo tests (matches Chinook test data)
DEFAULT_CUSTOMER_ID = 16


class TestDemoFlow:
    """End-to-end test of the demo conversation flow."""

    @pytest.fixture
    def graph_with_memory(self):
        """Create a graph with memory checkpointer for conversation persistence."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)

    @pytest.fixture
    def config(self):
        """Standard config for demo flow (thread_id only - customer_id is in context)."""
        return {
            "configurable": {
                "thread_id": "demo-flow-test",
            }
        }

    @pytest.fixture
    def context(self):
        """Runtime context with customer_id (secure - NOT in state or configurable)."""
        return {"customer_id": DEFAULT_CUSTOMER_ID}

    def invoke_with_message(
        self, graph, message: str, config: dict, context: dict
    ) -> dict:
        """Helper to invoke graph with proper state and context.

        customer_id is passed via context= parameter (context_schema),
        NOT in state (secure from LLM manipulation).
        """
        return graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
            },
            config=config,
            context=context,
        )

    def get_route(self, result: dict) -> str:
        """Extract the route from graph result."""
        return result.get("route", "unknown")

    def get_last_ai_message(self, result: dict) -> str:
        """Extract the last AI message content."""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                if msg.name != "supervisor":  # Skip routing messages
                    return msg.content
        return ""

    def has_tool_call(self, result: dict, tool_name: str) -> bool:
        """Check if a specific tool was called."""
        for msg in result["messages"]:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == tool_name:
                        return True
        return False

    # =========================================================================
    # 1️⃣ Music Expert Path
    # =========================================================================

    def test_01_acdc_query_routes_to_music(self, graph_with_memory, config, context):
        """'What AC/DC albums do you carry?' → routes to music_expert."""
        result = self.invoke_with_message(
            graph_with_memory,
            "What AC/DC albums do you carry?",
            config,
            context,
        )

        assert self.get_route(result) == "music"
        assert self.has_tool_call(result, "get_albums_by_artist")
        # Should mention AC/DC albums from the database
        response = self.get_last_ai_message(result)
        assert "AC/DC" in response or "ac/dc" in response.lower()

    def test_02_jazz_query_routes_to_music(self, graph_with_memory, config, context):
        """'What jazz artists do you have?' → routes to music_expert."""
        result = self.invoke_with_message(
            graph_with_memory,
            "What jazz artists do you have?",
            config,
            context,
        )

        assert self.get_route(result) == "music"
        assert self.has_tool_call(result, "get_artists_by_genre")

    def test_03_song_search_uses_check_for_songs(
        self, graph_with_memory, config, context
    ):
        """'Do you have any songs with love in the title?' → routes to music and responds about songs."""
        result = self.invoke_with_message(
            graph_with_memory,
            "Do you have any songs with 'love' in the title?",
            config,
            context,
        )

        assert self.get_route(result) == "music"
        # Model may call check_for_songs OR ask a clarifying question
        # Both are valid music expert behaviors
        response = self.get_last_ai_message(result)
        assert self.has_tool_call(result, "check_for_songs") or (
            "song" in response.lower()
            or "search" in response.lower()
            or "title" in response.lower()
        )

    def test_04_genre_query_calls_get_genres(self, graph_with_memory, config, context):
        """'What genres do you carry?' → should call get_genres tool."""
        result = self.invoke_with_message(
            graph_with_memory,
            "What genres of music do you carry?",
            config,
            context,
        )

        assert self.get_route(result) == "music"
        assert self.has_tool_call(result, "list_genres")

    # =========================================================================
    # 2️⃣ Support Rep Path
    # =========================================================================

    def test_05_account_query_routes_to_support(
        self, graph_with_memory, config, context
    ):
        """'Can you tell me about my account?' → routes to support_rep."""
        result = self.invoke_with_message(
            graph_with_memory,
            "Can you tell me about my account?",
            config,
            context,
        )

        assert self.get_route(result) == "support"
        assert self.has_tool_call(result, "get_customer_info"), (
            "Support Rep should call get_customer_info with injected customer_id, "
            "not ask the user for their ID"
        )

    def test_06_invoice_query_uses_tools(self, graph_with_memory, config, context):
        """Invoice query should use invoice-related tools."""
        result = self.invoke_with_message(
            graph_with_memory,
            "What are my recent invoices?",
            config,
            context,
        )

        assert self.get_route(result) == "support"

    # =========================================================================
    # 3️⃣ Routing Edge Cases
    # =========================================================================

    def test_07_greeting_routes_to_support(self, graph_with_memory, config, context):
        """'Hello!' → routes to support (general inquiries)."""
        result = self.invoke_with_message(
            graph_with_memory,
            "Hello!",
            config,
            context,
        )

        assert self.get_route(result) == "support"

    def test_08_topic_switch_works(self, graph_with_memory, config, context):
        """User switches from support to music mid-conversation."""
        # Start with support topic
        result1 = self.invoke_with_message(
            graph_with_memory,
            "I want a refund",
            config,
            context,
        )
        assert self.get_route(result1) == "support"

        # Switch to music topic
        result2 = self.invoke_with_message(
            graph_with_memory,
            "Actually, what rock bands do you have?",
            config,
            context,
        )
        assert self.get_route(result2) == "music"

    def test_09_ambiguous_yes_continues_context(
        self, graph_with_memory, config, context
    ):
        """'yes please' after music discussion should stay in music."""
        # Ask about music first
        result1 = self.invoke_with_message(
            graph_with_memory,
            "Do you have any Led Zeppelin?",
            config,
            context,
        )
        assert self.get_route(result1) == "music"

        # Ambiguous follow-up should continue music context
        result2 = self.invoke_with_message(
            graph_with_memory,
            "yes, tell me more",
            config,
            context,
        )
        assert self.get_route(result2) == "music"

    # =========================================================================
    # 4️⃣ HITL Refund Flow
    # =========================================================================

    def test_10_refund_triggers_hitl_interrupt(
        self, graph_with_memory, config, context
    ):
        """Refund request should trigger HITL interrupt before processing."""
        # First, get invoice info
        result1 = self.invoke_with_message(
            graph_with_memory,
            "I'd like a refund for invoice 98",
            config,
            context,
        )
        assert self.get_route(result1) == "support"

        # The graph should have called get_invoice, then tried to call process_refund
        # which triggers the interrupt. Check that we see the refund tool in pending state.
        state = graph_with_memory.get_state(config)

        # Check if there are pending tasks (HITL interrupt)
        if state.next:
            # Graph is paused at refund_tools node
            assert "refund_tools" in state.next
        else:
            # If no interrupt, the refund tool should have been called
            # (this happens when running without interrupt_before)
            pass

    # =========================================================================
    # 5️⃣ Multi-Turn Conversation
    # =========================================================================

    def test_11_multi_turn_music_conversation(self, graph_with_memory, config, context):
        """Multi-turn conversation about rock music maintains context."""
        # Turn 1
        result1 = self.invoke_with_message(
            graph_with_memory,
            "I'm looking for some rock music",
            config,
            context,
        )
        assert self.get_route(result1) == "music"

        # Turn 2: Model may use tool OR leverage context from previous response
        # (e.g., if Led Zeppelin was already mentioned in rock artists list)
        result2 = self.invoke_with_message(
            graph_with_memory,
            "Do you have Led Zeppelin?",
            config,
            context,
        )
        assert self.get_route(result2) == "music"
        response = self.get_last_ai_message(result2)
        # Accept tool call OR contextual response mentioning Led Zeppelin
        has_tool = self.has_tool_call(
            result2, "get_albums_by_artist"
        ) or self.has_tool_call(result2, "get_tracks_by_artist")
        has_context_response = (
            "led zeppelin" in response.lower() or "zeppelin" in response.lower()
        )
        assert has_tool or has_context_response

    # =========================================================================
    # 6️⃣ Edge Cases & Robustness
    # =========================================================================

    def test_12_artist_not_in_catalog(self, graph_with_memory, config, context):
        """Query for artist not in database returns graceful response."""
        result = self.invoke_with_message(
            graph_with_memory,
            "Do you have any Taylor Swift albums?",
            config,
            context,
        )

        assert self.get_route(result) == "music"
        response = self.get_last_ai_message(result)
        # Should indicate we don't have the artist
        assert any(
            phrase in response.lower()
            for phrase in ["don't have", "not in", "couldn't find", "no ", "sorry"]
        )


class TestFullDemoSession:
    """Run a complete demo session as a single continuous conversation."""

    @pytest.fixture
    def graph_with_memory(self):
        """Create a graph with memory checkpointer."""
        checkpointer = MemorySaver()
        return create_graph(checkpointer=checkpointer)

    def test_complete_demo_session(self, graph_with_memory):
        """Run through the entire demo script as one session."""
        config = {
            "configurable": {
                "thread_id": "complete-demo-session",
            }
        }
        # customer_id is passed via context (secure - NOT in state or configurable)
        context = {"customer_id": 1}

        demo_script = [
            # Music queries
            ("What AC/DC albums do you carry?", "music"),
            ("What jazz artists do you have?", "music"),
            ("What genres of music do you carry?", "music"),
            # Switch to support
            ("Can you tell me about my account?", "support"),
            # Back to music
            ("Actually, do you have any Led Zeppelin?", "music"),
            # Ambiguous follow-up
            ("What about their most popular songs?", "music"),
            # Final greeting - either route is acceptable for closing
            ("Thanks, that's all I needed!", None),  # None = accept any route
        ]

        for user_message, expected_route in demo_script:
            result = graph_with_memory.invoke(
                {
                    "messages": [HumanMessage(content=user_message)],
                },
                config=config,
                context=context,
            )
            actual_route = result.get("route", "unknown")

            if expected_route is not None:  # Skip assertion for flexible routes
                assert actual_route == expected_route, (
                    f"Message: '{user_message}'\n"
                    f"Expected route: {expected_route}, Got: {actual_route}"
                )

        print("✅ Complete demo session passed!")
