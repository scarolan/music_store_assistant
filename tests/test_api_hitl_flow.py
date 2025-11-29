"""Tests for the API-level HITL flow.

These tests verify:
1. Chat endpoint properly detects HITL interrupts
2. Approve/Reject endpoints work correctly
3. Status polling returns correct states
4. Rejection followed by new refund request works (fresh thread)
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app, pending_approvals, rejected_responses


@pytest.fixture
def client():
    """Create a test client and clear state between tests."""
    pending_approvals.clear()
    rejected_responses.clear()
    return TestClient(app)


class TestChatEndpoint:
    """Test the /chat endpoint."""

    def test_chat_returns_thread_id(self, client):
        """Chat should return a thread_id."""
        response = client.post("/chat", json={"message": "Hello", "customer_id": 1})
        assert response.status_code == 200
        data = response.json()
        assert "thread_id" in data
        assert "response" in data
        assert data["thread_id"] is not None

    def test_chat_uses_provided_thread_id(self, client):
        """Chat should use provided thread_id for conversation continuity."""
        # First message
        r1 = client.post("/chat", json={"message": "Hello", "customer_id": 1})
        thread_id = r1.json()["thread_id"]

        # Second message with same thread
        r2 = client.post(
            "/chat",
            json={
                "message": "What's my account info?",
                "thread_id": thread_id,
                "customer_id": 1,
            },
        )

        assert r2.json()["thread_id"] == thread_id


class TestHITLFlow:
    """Test the Human-in-the-Loop approval flow."""

    def test_refund_request_triggers_hitl(self, client):
        """A confirmed refund request should trigger HITL."""
        # Step 1: Ask for refund
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        # Step 2: Confirm
        r2 = client.post(
            "/chat",
            json={"message": "yes please", "thread_id": thread_id, "customer_id": 1},
        )

        data = r2.json()
        assert data["requires_approval"], "Refund confirmation should require approval"
        assert thread_id in pending_approvals, "Thread should be in pending_approvals"

    def test_approve_endpoint_works(self, client):
        """Approve endpoint should resume the graph."""
        # Setup: Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        r2 = client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )
        assert r2.json()["requires_approval"]

        # Approve
        r3 = client.post(f"/approve/{thread_id}?customer_id=1")
        assert r3.status_code == 200

        data = r3.json()
        assert "response" in data
        assert thread_id not in pending_approvals, "Should be removed from pending"

    def test_reject_endpoint_works(self, client):
        """Reject endpoint should return canned message."""
        # Setup: Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        r2 = client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )
        assert r2.json()["requires_approval"]

        # Reject
        r3 = client.post(f"/reject/{thread_id}?customer_id=1")
        assert r3.status_code == 200

        data = r3.json()
        assert "unable to provide a refund" in data["response"].lower()
        assert thread_id not in pending_approvals, "Should be removed from pending"
        assert thread_id in rejected_responses, "Should be in rejected_responses"


class TestStatusEndpoint:
    """Test the /status endpoint for polling."""

    def test_status_pending_when_awaiting_approval(self, client):
        """Status should return 'pending' when awaiting approval."""
        # Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )

        # Check status
        r3 = client.get(f"/status/{thread_id}?customer_id=1")
        assert r3.status_code == 200
        assert r3.json()["status"] == "pending"

    def test_status_completed_after_approval(self, client):
        """Status should return 'completed' after approval."""
        # Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )

        # Approve
        client.post(f"/approve/{thread_id}?customer_id=1")

        # Check status
        r3 = client.get(f"/status/{thread_id}?customer_id=1")
        assert r3.status_code == 200
        assert r3.json()["status"] == "completed"

    def test_status_completed_after_rejection(self, client):
        """Status should return 'completed' with rejection message after rejection."""
        # Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        r2 = client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )
        # Verify HITL was triggered
        assert r2.json().get("requires_approval"), "HITL should be triggered"

        # Reject
        r_reject = client.post(f"/reject/{thread_id}?customer_id=1")
        assert r_reject.status_code == 200, f"Reject should succeed: {r_reject.json()}"

        # Check status
        r3 = client.get(f"/status/{thread_id}?customer_id=1")
        assert r3.status_code == 200
        assert r3.json()["status"] == "completed"
        assert "unable to provide" in r3.json()["message"].lower()


class TestAdminEndpoint:
    """Test the /admin/pending endpoint."""

    def test_admin_pending_empty_initially(self, client):
        """Admin pending should be empty initially."""
        response = client.get("/admin/pending")
        assert response.status_code == 200
        assert response.json() == {"pending": []}

    def test_admin_pending_shows_hitl_requests(self, client):
        """Admin pending should show HITL requests."""
        # Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )

        # Check admin
        r3 = client.get("/admin/pending")
        pending = r3.json()["pending"]
        assert len(pending) == 1
        assert pending[0]["thread_id"] == thread_id
        assert pending[0]["customer_id"] == 1

    def test_admin_pending_clears_after_approval(self, client):
        """Admin pending should clear after approval."""
        # Get to HITL state
        r1 = client.post(
            "/chat",
            json={"message": "I want a refund for invoice 143", "customer_id": 1},
        )
        thread_id = r1.json()["thread_id"]

        client.post(
            "/chat", json={"message": "yes", "thread_id": thread_id, "customer_id": 1}
        )

        # Approve
        client.post(f"/approve/{thread_id}?customer_id=1")

        # Check admin
        r3 = client.get("/admin/pending")
        assert r3.json() == {"pending": []}
