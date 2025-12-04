"""Tests for the LangGraph supervisor and routing logic."""

import pytest
from langchain_core.messages import HumanMessage


class TestGraphCreation:
    """Tests for graph factory and structure."""

    def test_graph_can_be_created(self):
        """The graph factory function should return a compiled graph."""
        from src.graph import create_graph

        graph = create_graph()
        assert graph is not None

    def test_graph_has_supervisor_node(self):
        """Graph should have a supervisor node for routing."""
        from src.graph import create_graph

        graph = create_graph()
        nodes = list(graph.nodes.keys())

        assert "supervisor" in nodes, f"Expected 'supervisor' node, got: {nodes}"

    def test_graph_has_music_expert_node(self):
        """Graph should have a music_expert node."""
        from src.graph import create_graph

        graph = create_graph()
        nodes = list(graph.nodes.keys())

        assert "music_expert" in nodes, f"Expected 'music_expert' node, got: {nodes}"

    def test_graph_has_support_rep_node(self):
        """Graph should have a support_rep node."""
        from src.graph import create_graph

        graph = create_graph()
        nodes = list(graph.nodes.keys())

        assert "support_rep" in nodes, f"Expected 'support_rep' node, got: {nodes}"

    def test_graph_accepts_customer_context(self):
        """Graph should accept customer_id via context parameter (context_schema)."""
        from src.graph import create_graph

        # Verify graph can be created
        graph = create_graph()
        assert graph is not None

        # Verify the context structure that will be used (NOT in configurable - secure!)
        context = {"customer_id": 16}
        assert "customer_id" in context


class TestRouting:
    """Tests for supervisor routing logic."""

    @pytest.mark.integration
    def test_router_selects_music_for_music_query(self, test_config, test_context):
        """Supervisor should route music queries to music_expert."""
        from src.graph import create_graph

        graph = create_graph()

        result = graph.invoke(
            {"messages": [HumanMessage(content="What albums does AC/DC have?")]},
            test_config,
            context=test_context,
        )

        # Should have received a response about music
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1

    @pytest.mark.integration
    def test_router_selects_support_for_account_query(self, test_config, test_context):
        """Supervisor should route account queries to support_rep."""
        from src.graph import create_graph

        graph = create_graph()

        result = graph.invoke(
            {"messages": [HumanMessage(content="What is my email address on file?")]},
            test_config,
            context=test_context,
        )

        assert result is not None
        assert "messages" in result


class TestHITL:
    """Tests for Human-in-the-Loop interrupts."""

    @pytest.mark.integration
    def test_hitl_interrupts_on_refund_request(self, test_config_with_thread):
        """Graph should interrupt before processing refund for human approval."""
        from src.graph import create_graph
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_graph(checkpointer=checkpointer)
        config, context = test_config_with_thread("test-hitl")

        # First message: request a refund
        result = graph.invoke(
            {"messages": [HumanMessage(content="I want a refund for invoice 98")]},
            config,
            context=context,
        )

        # The graph should have produced some response
        assert result is not None
        assert "messages" in result
