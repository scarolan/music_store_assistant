# Project: Algorhythm Music Store Assistant

A production-ready **LangGraph** customer support chatbot demonstrating the Supervisor/Router pattern with Human-in-the-Loop (HITL) for sensitive operations.

## 1. Purpose & Demo Value

This is a **demo/interview artifact** showcasing:
- **Supervisor Pattern**: LLM-powered routing between specialized agents
- **Human-in-the-Loop (HITL)**: Approval workflow for refund requests
- **Secure Context Injection**: `customer_id` via `context_schema` (not in state!)
- **Multi-Model Support**: Swap LLM providers via environment variables
- **Full-Stack Implementation**: FastAPI backend + chat UI + admin dashboard
- **LangGraph Studio Ready**: `langgraph.json` configured for visual debugging

**Target Audience**: Technical interviewers, customers evaluating LangGraph capabilities, and internal demos.

---

## 2. Technical Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11+ |
| **Framework** | LangGraph, LangChain |
| **LLM Providers** | OpenAI (default), Anthropic, Google Gemini, DeepSeek |
| **API** | FastAPI with async support |
| **Database** | SQLite (Chinook.db sample data) |
| **Testing** | pytest + pytest-asyncio |
| **Observability** | LangSmith (traces, cost tracking) |
| **Package Manager** | `uv` (always use `uv run` to execute commands) |
| **CI/CD** | GitHub Actions (formatting → linting → type-check → tests → cost report) |

### Environment Setup

```bash
# Install dependencies
uv sync

# Run the web UI
uv run uvicorn src.api:app --reload --port 8000

# Run tests
uv run pytest

# Run in LangGraph Studio
langgraph dev
```

**Required `.env` variables:**
```bash
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...              # Required - default for Music Expert
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=music-store-assistant
```

**Model defaults** (auto-detect provider from name prefix):
```bash
SUPERVISOR_MODEL=gpt-4o-mini         # Default: gpt-4o-mini
MUSIC_EXPERT_MODEL=gpt-4o-mini       # Default: gpt-4o-mini
SUPPORT_REP_MODEL=gpt-4o-mini        # Default: gpt-4o-mini
```

---

## 3. Architecture Overview

### Graph Structure (src/graph.py)

```
Entry → Supervisor → [music_expert | support_rep]
                           ↓              ↓
                      music_tools    support_tools ──→ refund_tools (HITL)
                           ↓              ↓                   ↓
                          END         support_rep ←──────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **State Schema** | `src/state.py` | `TypedDict` with `messages`, `route` (NO customer_id!) |
| **Context Schema** | `src/state.py` | `CustomerContext` dataclass for secure runtime context |
| **Supervisor** | `src/graph.py` | Routes via structured output to `RouteDecision` |
| **Music Expert** | `src/graph.py` | 5 read-only catalog tools |
| **Support Rep** | `src/graph.py` | 3 tools (2 safe, 1 HITL-gated) using `Runtime[CustomerContext]` |
| **Tools** | `src/tools/music.py`, `support.py` | `@tool` decorated functions using `ToolRuntime[CustomerContext]` |
| **API** | `src/api.py` | FastAPI with `/chat`, `/approve`, `/reject` endpoints |

### Security: context_schema Pattern

**CRITICAL**: `customer_id` is **NOT** in graph state. It uses `context_schema`:

```python
# state.py - CustomerContext is a dataclass, NOT part of State
@dataclass
class CustomerContext:
    customer_id: int = 16

# graph.py - Graph uses context_schema
builder = StateGraph(State, context_schema=CustomerContext)

# Nodes access via Runtime
def support_rep(state: State, runtime: Runtime[CustomerContext]):
    customer_id = runtime.context.customer_id  # Secure!

# Tools access via ToolRuntime (hidden from LLM schema!)
@tool
def get_customer_info(runtime: ToolRuntime[CustomerContext]) -> str:
    customer_id = runtime.context.customer_id  # Secure!

# Invocation passes context separately
graph.invoke({"messages": [...]}, config, context={"customer_id": 16})
```

This prevents LLM from manipulating customer_id while allowing Studio to inject it via Assistants.

### HITL Interrupt Pattern

Refund requests trigger `interrupt_before=["refund_tools"]`:
1. User requests refund → Support Rep calls `process_refund`
2. Graph pauses before executing the tool
3. Admin approves/rejects via dashboard
4. Graph resumes with `Command(resume=True)` (must pass `context=` again!)

---

## 4. Testing Strategy

### Test Pyramid (Layered by Cost & Speed)

We use a **three-tier test strategy** mirroring the CI pipeline:

```
┌──────────────────────────────────────┐
│   Functional Tests (E2E)             │  ← Slowest, most LLM calls
│   test_demo_flow.py                  │  ← Full conversation flows
│   test_api_hitl_flow.py              │  ← API + HITL integration
│   test_refund_confirmation_flow.py   │
├──────────────────────────────────────┤
│   Integration Tests                  │  ← Graph + API, some LLM calls
│   test_graph.py                      │  ← Routing, node execution
│   test_api.py                        │  ← Endpoint contracts
├──────────────────────────────────────┤
│   Unit Tests                         │  ← Fast, no LLM calls
│   test_state.py                      │  ← Schema validation
│   test_music_tools.py                │  ← Tool existence + DB queries
│   test_support_tools.py              │  ← Tool contracts
└──────────────────────────────────────┘
```

### Running Tests

```bash
# All tests
uv run pytest

# By tier (mirrors CI)
uv run pytest tests/test_state.py tests/test_music_tools.py tests/test_support_tools.py  # Unit
uv run pytest tests/test_graph.py tests/test_api.py                                       # Integration
uv run pytest tests/test_demo_flow.py tests/test_api_hitl_flow.py                         # Functional

# With verbose output
uv run pytest -v --tb=short

# Single test
uv run pytest tests/test_graph.py::TestRouting::test_router_selects_music_for_music_query -v
```

### Test Markers

```python
@pytest.mark.integration  # Tests that call LLMs or require Chinook.db
```

### Key Fixtures (tests/conftest.py)

| Fixture | Purpose |
|---------|---------|
| `test_config` | Config dict with `customer_id=16` and LangSmith tags |
| `test_config_with_thread(thread_id)` | Factory for thread-specific configs (HITL tests) |
| `db_path` | Path to Chinook.db (skips if missing) |
| `openai_callback()` | Context manager for token tracking |

### Writing New Tests

1. **Unit tests** (no LLM): Test tool existence, schema shape, DB queries
   ```python
   def test_get_albums_by_artist_is_tool(self):
       from src.tools.music import get_albums_by_artist
       assert hasattr(get_albums_by_artist, "name")  # LangChain tool check
   ```

2. **Integration tests** (`@pytest.mark.integration`): Test graph behavior
   ```python
   @pytest.mark.integration
   def test_router_selects_music_for_music_query(self, test_config):
       from src.graph import create_graph
       graph = create_graph()
       result = graph.invoke(
           {"messages": [HumanMessage(content="What AC/DC albums?")]},
           test_config
       )
       assert result["route"] == "music"
   ```

3. **HITL tests**: Use `MemorySaver` checkpointer + verify `state.next`
   ```python
   def test_refund_triggers_hitl(self, graph, test_config_with_thread):
       config = test_config_with_thread("test-refund-1")
       result = graph.invoke({"messages": [...], "customer_id": 16}, config)
       state = graph.get_state(config)
       assert "refund_tools" in state.next  # Interrupted before refund
   ```

### LangSmith Test Tagging

All tests automatically receive the `test` tag for LangSmith filtering. CI runs add `ci-cd` and `run-{github_run_id}` tags for cost attribution.

```python
# conftest.py sets LANGSMITH_TEST_MODE=1
# Traces visible in LangSmith with filter: has(tags, "test")
```

### Cost Tracking

After test runs, view token usage:
```bash
uv run python scripts/report_test_costs.py --minutes 30
```

---

## 5. Project Structure

```
.
├── src/
│   ├── graph.py          # LangGraph definition + model factory
│   ├── state.py          # State TypedDict schema
│   ├── api.py            # FastAPI backend
│   ├── cli.py            # Interactive CLI
│   ├── utils.py          # DB connection helper
│   └── tools/
│       ├── music.py      # 5 read-only catalog tools (MUSIC_TOOLS)
│       └── support.py    # 3 support tools (SAFE_SUPPORT_TOOLS, HITL_SUPPORT_TOOLS)
├── tests/
│   ├── conftest.py       # Fixtures, token tracking, markers
│   ├── test_state.py     # Unit: Schema validation
│   ├── test_music_tools.py    # Unit: Music tool contracts
│   ├── test_support_tools.py  # Unit: Support tool contracts
│   ├── test_graph.py     # Integration: Graph structure + routing
│   ├── test_api.py       # Integration: API endpoints
│   ├── test_demo_flow.py # Functional: Full demo conversations
│   ├── test_api_hitl_flow.py  # Functional: API-level HITL
│   └── test_refund_confirmation_flow.py  # Functional: Refund flow
├── static/
│   ├── index.html        # Customer chat UI
│   └── admin.html        # HITL approval dashboard
├── scripts/
│   └── report_test_costs.py  # LangSmith cost reporting
├── .github/
│   └── workflows/ci.yml  # CI pipeline (format → lint → typecheck → tests)
├── langgraph.json        # LangGraph Studio configuration
├── pyproject.toml        # Dependencies + pytest config
├── Chinook.db            # SQLite sample database
├── ARCHITECTURE.md       # Mermaid diagrams + detailed docs
├── DEMO_CHAT.md          # Demo script with talk track
└── README.md             # Quick start guide
```

---

## 6. Development Guidelines

### Code Style
- **Type hints**: Required on all function signatures
- **Docstrings**: Required on all public functions (tools need them for LLM understanding)
- **Formatting**: `uv run ruff format src/ tests/`
- **Linting**: `uv run ruff check src/ tests/`
- **Type checking**: `uv run pyright src/`

### Adding New Tools

1. Add the `@tool` decorated function with a clear docstring
2. Add to the appropriate `*_TOOLS` list export
3. Write unit tests for existence and basic functionality
4. Write integration test for graph behavior

```python
# src/tools/music.py
@tool
def my_new_tool(param: str) -> str:
    """Clear description for the LLM to know when to use this tool.
    
    Args:
        param: What this parameter is for.
    
    Returns:
        What the tool returns.
    """
    # Implementation
    
MUSIC_TOOLS = [..., my_new_tool]  # Add to exports
```

### Modifying the Graph

1. Update node/edge logic in `src/graph.py`
2. Run routing tests: `uv run pytest tests/test_graph.py -v`
3. Run demo flow to verify end-to-end: `uv run pytest tests/test_demo_flow.py -v`

### Model Configuration

Models are configured via environment variables with auto-detection:
- `gpt-*` → OpenAI (ChatOpenAI)
- `claude-*` → Anthropic (ChatAnthropic)
- `gemini-*` → Google (ChatGoogleGenerativeAI)
- `deepseek-*` → DeepSeek (ChatOpenAI with custom base_url)

---

## 7. Key Files Reference

| When you need to... | Look at... |
|---------------------|------------|
| Understand graph flow | `src/graph.py`, `ARCHITECTURE.md` |
| Add/modify tools | `src/tools/music.py`, `src/tools/support.py` |
| Change state schema | `src/state.py` |
| Modify API endpoints | `src/api.py` |
| Add test fixtures | `tests/conftest.py` |
| Update demo script | `DEMO_CHAT.md` |
| Modify CI pipeline | `.github/workflows/ci.yml` |
| Configure LangGraph Studio | `langgraph.json` |

---

## 8. Common Tasks

### Run a demo
```bash
uv run uvicorn src.api:app --reload --port 8000
# Open http://localhost:8000 (chat) and http://localhost:8000/admin (HITL)
```

### Debug in LangGraph Studio
```bash
langgraph dev
# Visual graph execution with state inspection
```

### Check test costs
```bash
uv run python scripts/report_test_costs.py --minutes 30
```

### Full CI check locally
```bash
uv run ruff format src/ tests/ --check
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest -v
```
