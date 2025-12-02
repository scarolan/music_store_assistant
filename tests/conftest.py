"""Pytest configuration and fixtures."""

import pytest
import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class TokenUsageTracker:
    """Track token usage across all tests in a session."""
    
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    llm_calls: int = 0
    
    # Track per-test breakdown
    test_costs: dict = field(default_factory=dict)
    current_test: str = ""
    
    def add_usage(self, prompt: int, completion: int, cost: float):
        """Record token usage from a callback."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.total_cost += cost
        self.llm_calls += 1
        
        # Track per-test
        if self.current_test:
            if self.current_test not in self.test_costs:
                self.test_costs[self.current_test] = {"tokens": 0, "cost": 0.0, "calls": 0}
            self.test_costs[self.current_test]["tokens"] += prompt + completion
            self.test_costs[self.current_test]["cost"] += cost
            self.test_costs[self.current_test]["calls"] += 1
    
    def summary(self) -> str:
        """Generate a summary report."""
        lines = [
            "",
            "=" * 60,
            "🔥 LLM TOKEN USAGE SUMMARY",
            "=" * 60,
            f"  Total LLM Calls:      {self.llm_calls:,}",
            f"  Prompt Tokens:        {self.prompt_tokens:,}",
            f"  Completion Tokens:    {self.completion_tokens:,}",
            f"  Total Tokens:         {self.total_tokens:,}",
            f"  Estimated Cost:       ${self.total_cost:.4f}",
            "-" * 60,
        ]
        
        if self.test_costs:
            # Sort by cost descending
            sorted_tests = sorted(
                self.test_costs.items(), 
                key=lambda x: x[1]["cost"], 
                reverse=True
            )[:5]  # Top 5 most expensive
            
            lines.append("  Top 5 Most Expensive Tests:")
            for test_name, data in sorted_tests:
                short_name = test_name.split("::")[-1][:40]
                lines.append(f"    {short_name:<40} ${data['cost']:.4f} ({data['tokens']:,} tokens)")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Global tracker instance
_token_tracker = TokenUsageTracker()


def get_langsmith_tags() -> list[str]:
    """Build list of tags for LangSmith tracing.

    Always includes 'test'. Also includes any tags from LANGCHAIN_TAGS env var
    (comma-separated), such as 'ci-cd' when running in GitHub Actions.
    """
    tags = ["test"]

    # Add additional tags from environment (e.g., 'ci-cd' from GitHub Actions)
    extra_tags = os.getenv("LANGCHAIN_TAGS", "")
    if extra_tags:
        tags.extend(tag.strip() for tag in extra_tags.split(",") if tag.strip())

    return tags


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
    """Provide a config dict with appropriate tags for LangSmith filtering.

    Always includes 'test' tag. Includes 'ci-cd' when running in GitHub Actions.

    Usage in tests:
        result = graph.invoke({"messages": [...]}, test_config)
    """
    return {"configurable": {"customer_id": 1}, "tags": get_langsmith_tags()}


@pytest.fixture
def test_config_with_thread():
    """Factory fixture to create test config with a specific thread_id.

    Always includes 'test' tag. Includes 'ci-cd' when running in GitHub Actions.

    Usage in tests:
        config = test_config_with_thread("my-thread-id")
        result = graph.invoke({"messages": [...]}, config)
    """

    def _make_config(thread_id: str, customer_id: int = 1):
        return {
            "configurable": {"thread_id": thread_id, "customer_id": customer_id},
            "tags": get_langsmith_tags(),
        }

    return _make_config


@pytest.fixture(scope="session")
def db_path():
    """Return the path to the Chinook database."""
    path = Path(__file__).parent.parent / "Chinook.db"
    if not path.exists():
        pytest.skip("Chinook.db not found - run setup first")
    return str(path)


# ============================================================================
# Token Usage Tracking Hooks
# ============================================================================

@pytest.fixture(scope="session")
def token_tracker():
    """Provide access to the global token tracker."""
    return _token_tracker


@pytest.fixture(autouse=True)
def track_current_test(request):
    """Track which test is currently running for per-test cost breakdown."""
    _token_tracker.current_test = request.node.nodeid
    yield
    _token_tracker.current_test = ""


@pytest.fixture
def openai_callback():
    """Provide an OpenAI callback that tracks token usage.
    
    Usage in tests:
        def test_something(openai_callback):
            with openai_callback() as cb:
                result = graph.invoke(...)
            # Tokens automatically tracked
    """
    from langchain_community.callbacks import get_openai_callback
    from contextlib import contextmanager
    
    @contextmanager
    def _tracked_callback():
        with get_openai_callback() as cb:
            yield cb
        # Record usage after the context exits
        _token_tracker.add_usage(
            prompt=cb.prompt_tokens,
            completion=cb.completion_tokens,
            cost=cb.total_cost
        )
    
    return _tracked_callback


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print token usage summary at end of test run."""
    if _token_tracker.llm_calls > 0:
        terminalreporter.write_line(_token_tracker.summary())
