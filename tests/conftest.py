"""Pytest configuration and fixtures."""

import pytest
import os
from pathlib import Path


def pytest_configure(config):
    """Register custom markers and set test mode for LangSmith tagging."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may call LLM/DB)"
    )
    
    # Enable test mode for LangSmith tagging
    # This causes the API's build_config to add 'test' tag to all traces
    os.environ["LANGSMITH_TEST_MODE"] = "1"


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    
    # Load from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    # Ensure test mode stays set after loading .env
    os.environ["LANGSMITH_TEST_MODE"] = "1"


@pytest.fixture
def test_config():
    """Provide a config dict with 'test' tag for LangSmith filtering.
    
    Usage in tests:
        result = graph.invoke({"messages": [...]}, test_config)
    """
    return {
        "configurable": {"customer_id": 1},
        "tags": ["test"]
    }


@pytest.fixture
def test_config_with_thread():
    """Factory fixture to create test config with a specific thread_id.
    
    Usage in tests:
        config = test_config_with_thread("my-thread-id")
        result = graph.invoke({"messages": [...]}, config)
    """
    def _make_config(thread_id: str, customer_id: int = 1):
        return {
            "configurable": {"thread_id": thread_id, "customer_id": customer_id},
            "tags": ["test"]
        }
    return _make_config


@pytest.fixture(scope="session")
def db_path():
    """Return the path to the Chinook database."""
    path = Path(__file__).parent.parent / "Chinook.db"
    if not path.exists():
        pytest.skip("Chinook.db not found - run setup first")
    return str(path)
