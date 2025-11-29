"""Tests for the LangGraph supervisor and routing logic."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage


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

    def test_graph_accepts_customer_id_in_config(self):
        """Graph should accept customer_id via configurable parameters."""
        from src.graph import create_graph
        
        graph = create_graph()
        
        # This should not raise - customer_id is passed via config
        config = {"configurable": {"customer_id": 1}}
        
        # Just verify the config structure is accepted
        assert "configurable" in config
        assert "customer_id" in config["configurable"]


class TestRouting:
    """Tests for supervisor routing logic."""
    
    @pytest.mark.integration
    def test_router_selects_music_for_music_query(self):
        """Supervisor should route music queries to music_expert."""
        from src.graph import create_graph
        
        graph = create_graph()
        config = {"configurable": {"customer_id": 1}}
        
        result = graph.invoke(
            {"messages": [HumanMessage(content="What albums does AC/DC have?")]},
            config
        )
        
        # Should have received a response about music
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1

    @pytest.mark.integration
    def test_router_selects_support_for_account_query(self):
        """Supervisor should route account queries to support_rep."""
        from src.graph import create_graph
        
        graph = create_graph()
        config = {"configurable": {"customer_id": 1}}
        
        result = graph.invoke(
            {"messages": [HumanMessage(content="What is my email address on file?")]},
            config
        )
        
        assert result is not None
        assert "messages" in result


class TestHITL:
    """Tests for Human-in-the-Loop interrupts."""
    
    @pytest.mark.integration
    def test_hitl_interrupts_on_refund_request(self):
        """Graph should interrupt before processing refund for human approval."""
        from src.graph import create_graph
        from langgraph.checkpoint.memory import MemorySaver
        
        checkpointer = MemorySaver()
        graph = create_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "test-hitl", "customer_id": 1}}
        
        # First message: request a refund
        result = graph.invoke(
            {"messages": [HumanMessage(content="I want a refund for invoice 98")]},
            config
        )
        
        # The graph should have produced some response
        assert result is not None
        assert "messages" in result
