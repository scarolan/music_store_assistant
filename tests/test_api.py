"""Tests for the FastAPI chat API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the API."""
    from src.api import app

    return TestClient(app)


class TestChatEndpoint:
    """Tests for POST /chat endpoint."""

    def test_chat_endpoint_exists(self, client: TestClient):
        """The /chat endpoint should exist and accept POST."""
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code != 404

    def test_chat_requires_message(self, client: TestClient):
        """The /chat endpoint should require a message field."""
        response = client.post("/chat", json={})
        assert response.status_code == 422

    @pytest.mark.integration
    def test_chat_returns_response(self, client: TestClient):
        """The /chat endpoint should return a response with content."""
        response = client.post(
            "/chat",
            json={
                "message": "What albums does AC/DC have?",
                "thread_id": "test-music-123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "thread_id" in data

    @pytest.mark.integration
    def test_refund_triggers_hitl(self, client: TestClient):
        """Refund requests should trigger HITL and return requires_approval."""
        response = client.post(
            "/chat",
            json={
                "message": "I want a refund for invoice 5",
                "thread_id": "test-refund-456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Should indicate approval is needed
        assert "requires_approval" in data


class TestApproveEndpoint:
    """Tests for POST /approve endpoint."""

    def test_approve_endpoint_exists(self, client: TestClient):
        """The /approve endpoint should exist."""
        response = client.post("/approve/test-thread?customer_id=16")
        assert response.status_code != 404

    @pytest.mark.integration
    def test_approve_continues_graph(self, client: TestClient):
        """Approving should continue the interrupted graph."""
        # First trigger HITL - need to ask for refund AND confirm
        client.post(
            "/chat",
            json={
                "message": "I want a refund for invoice 143",
                "thread_id": "test-approve-789",
                "customer_id": 1,
            },
        )

        # Confirm the refund
        r2 = client.post(
            "/chat",
            json={"message": "yes", "thread_id": "test-approve-789", "customer_id": 16},
        )

        # Verify HITL triggered
        assert r2.json().get("requires_approval"), (
            "Should require approval after confirmation"
        )

        # Then approve
        response = client.post("/approve/test-approve-789?customer_id=16")
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_ok(self, client: TestClient):
        """Health check should return OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
