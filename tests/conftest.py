"""Pytest configuration and fixtures."""

import pytest
import os
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may call LLM/DB)"
    )


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    
    # Load from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)


@pytest.fixture(scope="session")
def db_path():
    """Return the path to the Chinook database."""
    path = Path(__file__).parent.parent / "Chinook.db"
    if not path.exists():
        pytest.skip("Chinook.db not found - run setup first")
    return str(path)
