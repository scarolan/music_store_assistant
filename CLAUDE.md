# CLAUDE.md - AI Assistant Context Guide

This document provides comprehensive context about the Music Store Assistant codebase for AI assistants (like Claude) to quickly understand the project structure, architecture, and implementation details.

## Project Overview

**Music Store Assistant** (aka "Algorhythm Customer Support Bot") is a production-grade LangGraph application demonstrating advanced agentic patterns for customer support automation. The system showcases:

- **Supervisor/Router Pattern**: Intelligent request routing based on intent classification
- **Multi-Agent Architecture**: Specialized agents for different domains (music catalog, customer support)
- **Human-in-the-Loop (HITL)**: Approval workflow for sensitive operations (refunds)
- **Multi-Provider LLM Support**: Configurable model selection (OpenAI, Anthropic, Google, DeepSeek)
- **Production Observability**: Full OpenTelemetry instrumentation with Grafana Cloud integration

## Architecture Quick Reference

### High-Level Flow
```
User Request → Supervisor (Router) → [Music Expert | Support Rep] → Tools → Response
                                                ↓ (if refund)
                                        HITL Approval Gate
```

### Agent Roles

| Agent | Model | Temperature | Purpose | Tools |
|-------|-------|-------------|---------|-------|
| **Supervisor** | gpt-4o-mini | 0 | Intent classification & routing | None |
| **Music Expert** | gpt-4o-mini | 0.7 | Catalog queries (read-only) | 5 music tools |
| **Support Rep** | gpt-4o-mini | 0 | Account operations | 3 support tools (1 HITL) |

### Key Design Patterns

1. **Context Schema for Security**: Customer ID passed via `context_schema`, not state (prevents LLM manipulation)
2. **Structured Output Routing**: Supervisor uses `RouteDecision` Pydantic model with strict enum validation
3. **Conditional HITL**: Only refund operations trigger human approval, other support tools auto-execute
4. **Tool Node Separation**: Separate `ToolNode` instances for safe vs HITL tools
5. **Retry Policy**: Exponential backoff (1s → 2s → 4s, max 10s) for tool execution failures

## Technology Stack

### Core Framework
- **LangGraph 1.0+**: StateGraph with interrupt_before for HITL
- **LangChain 1.0+**: Message types, tool binding, model abstractions
- **FastAPI**: REST API backend for web UI
- **SQLite (Chinook)**: Music catalog database (read-only for agents)

### Observability
- **OpenTelemetry SDK**: OTLP/HTTP exporter to Grafana Cloud
- **OpenInference Instrumentation**: Auto-instrumentation with full trace hierarchy
- **Custom Attribute Filtering**: Reduces span bloat while preserving essential debugging data

### LLM Providers (Auto-Detected)
- **OpenAI**: `gpt-*` models (default: gpt-4o-mini)
- **Anthropic**: `claude-*` models (requires langchain-anthropic)
- **Google**: `gemini-*` models (requires langchain-google-genai)
- **DeepSeek**: `deepseek-*` models (budget option, uses OpenAI SDK with custom base_url)

## File Structure & Responsibilities

### Core Application
```
src/
├── graph.py           # LangGraph definition, node functions, model factory
├── state.py           # TypedDict schemas (State, CustomerContext)
├── api.py             # FastAPI endpoints, HITL management, web UI serving
├── cli.py             # Interactive CLI for local testing
├── otel.py            # [OTEL BRANCH] OpenTelemetry configuration & filtering
├── utils.py           # Database connection utilities
└── tools/
    ├── music.py       # 5 read-only catalog tools (no auth required)
    └── support.py     # 3 support tools (2 safe + 1 HITL refund tool)
```

### Frontend
```
static/
├── index.html         # Customer chat interface (WebSocket-like polling)
└── admin.html         # HITL approval dashboard for supervisors
```

### Configuration
```
.env                   # API keys, model selection, tracing config
.env.example           # Template with all available options
pyproject.toml         # uv-managed dependencies
```

## Key Implementation Details

### 1. Security Architecture

**Customer Authentication**: Simulated via `context_schema`
```python
# In api.py
graph.invoke(
    {"messages": [("user", message)]},
    config={"configurable": {"thread_id": thread_id}},
    context={"customer_id": 16}  # ← NOT in state, secure from LLM
)

# In tools/support.py
@tool(runtime=CustomerContext)
def get_invoice(invoice_id: int | None, runtime: ToolRuntime[CustomerContext]) -> str:
    customer_id = runtime.context.customer_id  # ← Hidden from LLM tool schema
    # ... scoped query using customer_id
```

**Why This Matters**: Customer ID is never exposed to the LLM, preventing prompt injection attacks like "look up customer_id=999's invoices"

### 2. HITL Implementation

**Interrupt Configuration** (src/graph.py:456)
```python
compile_kwargs["interrupt_before"] = ["refund_tools"]  # Only refunds, not all support tools
```

**Approval Flow** (src/api.py):
1. Graph hits `refund_tools` node → interrupts → returns to API
2. API detects `state.next` is populated → stores in `pending_approvals` dict
3. Admin polls `GET /admin/pending` → sees pending request
4. Admin calls `POST /approve/{thread_id}` → `graph.invoke(None, config)` resumes
5. Graph executes refund tool → returns final response

**Rejection Handling**: Rejection does NOT resume graph (prevents confusing LLM with fake user messages). Instead, returns canned rejection message and clears thread from pending tracking.

### 3. OTEL Instrumentation (feat/enable-otel-tracing Branch)

**Initialization Order** (CRITICAL):
```python
# api.py
load_dotenv()                        # 1. Load env vars first
from src.otel import configure_otel_tracing
configure_otel_tracing()             # 2. Set up TracerProvider BEFORE LangChain imports
from langgraph.checkpoint.memory import MemorySaver  # 3. Now safe to import
```

**Why This Order Matters**: OpenInference's LangChain instrumentation must patch modules before they're imported. Setting the global TracerProvider early ensures all LangChain/LangGraph operations are traced.

**Attribute Filtering Strategy**:
- **DROP**: Huge JSON blobs (`input.value`, `output.value`), tool schemas (`llm.tools.*`)
- **TRUNCATE**: User messages (500 chars), system prompts (200 chars)
- **KEEP**: Token counts, model names, trace IDs (critical for cost tracking)
- **LIMIT**: Keeps system prompt + last 10 messages (prevents unbounded span growth)

**Configuration** (.env):
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<base64-encoded-credentials>
OTEL_SERVICE_NAME=music-store-assistant
```

**Trace Hierarchy** (from OpenInference):
```
LangGraph Run (session.id: thread_id)
├─ Supervisor Chain
│  └─ LLM Call (structured output)
├─ Music Expert Chain
│  ├─ LLM Call (with tools)
│  └─ Tool Call: get_albums_by_artist
│     └─ SQL Query (captured in span)
└─ Support Rep Chain
   ├─ LLM Call
   └─ Tool Call: process_refund (interrupted)
```

### 4. Model Factory Pattern

**Dynamic Provider Selection** (src/graph.py:152):
```python
def get_model_for_role(role, env_var, temperature=0, **kwargs) -> BaseChatModel:
    model_name = os.getenv(env_var, "gpt-4o-mini")

    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(...)
    elif model_name.startswith("claude"):
        return ChatAnthropic(...)
    elif model_name.startswith("deepseek"):
        return ChatOpenAI(base_url="https://api.deepseek.com", ...)
    else:  # Default OpenAI
        return ChatOpenAI(...)
```

**Environment Variables**:
- `SUPERVISOR_MODEL` - Routing decisions (default: gpt-4o-mini)
- `MUSIC_EXPERT_MODEL` - Catalog queries (default: gpt-4o-mini, temp=0.7)
- `SUPPORT_REP_MODEL` - Account operations (default: gpt-4o-mini, streaming enabled)

### 5. Tool Categorization

**Music Tools** (public, read-only):
```python
MUSIC_TOOLS = [
    get_albums_by_artist,    # SQL: SELECT * FROM albums WHERE ArtistId=...
    get_tracks_by_artist,    # SQL: SELECT * FROM tracks JOIN albums...
    check_for_songs,         # SQL: SELECT * FROM tracks WHERE Name LIKE %...%
    get_artists_by_genre,    # SQL: SELECT * FROM artists JOIN genres...
    list_genres,             # SQL: SELECT DISTINCT Genre FROM genres
]
```

**Support Tools** (customer-scoped):
```python
SAFE_SUPPORT_TOOLS = [
    get_customer_info,       # SQL: WHERE CustomerId={runtime.context.customer_id}
    get_invoice,             # SQL: WHERE CustomerId={runtime.context.customer_id}
]

HITL_SUPPORT_TOOLS = [
    process_refund,          # SQL: UPDATE invoices SET Status='refunded' WHERE InvoiceId=...
]

HITL_TOOLS = {"process_refund"}  # Used for routing logic
```

## Development Workflow

### Local Development
```bash
# 1. Setup
cp .env.example .env
# Edit .env with your API keys

uv sync
curl -o Chinook.db https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite

# 2. Run Web UI
uv run uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
# Customer UI: http://localhost:8000
# Admin UI: http://localhost:8000/admin

# 3. Run CLI (for quick testing)
uv run python -m src.cli

# 4. Run Tests
uv run pytest
uv run pytest -v -k test_refund  # Specific test pattern
```

### Testing Strategy
```
tests/
├── test_graph.py               # LangGraph flow tests
├── test_api.py                 # FastAPI endpoint tests
├── test_api_hitl_flow.py       # HITL approval/rejection flows
├── test_demo_flow.py           # End-to-end demo scenarios
├── test_refund_confirmation_flow.py  # Multi-turn refund conversations
├── test_music_tools.py         # Music tool unit tests
├── test_support_tools.py       # Support tool unit tests
└── test_state.py               # State schema validation
```

**Key Test Patterns**:
- Use `MemorySaver` checkpointer for HITL tests
- Mock database in unit tests, use real DB in integration tests
- All tests automatically traced via OpenInference instrumentation

### CI/CD Pipeline (.github/workflows/ci.yml)
```
1. Install uv + Python 3.12
2. Download Chinook.db
3. Run pytest with full test suite
4. Traces exported to Grafana Cloud (tagged with service name)
```

## Common Tasks

### Adding a New Tool
1. Define tool in `src/tools/music.py` or `src/tools/support.py`
2. Add to appropriate tool list (`MUSIC_TOOLS`, `SAFE_SUPPORT_TOOLS`, or `HITL_SUPPORT_TOOLS`)
3. If HITL required, add tool name to `HITL_TOOLS` set
4. Update prompts in `src/graph.py` to document the new tool for the agent

### Changing Models
```bash
# Switch Music Expert to Claude Haiku
export MUSIC_EXPERT_MODEL=claude-3-5-haiku-20241022
export ANTHROPIC_API_KEY=sk-ant-...

# Switch to DeepSeek for cost savings
export SUPERVISOR_MODEL=deepseek-chat
export DEEPSEEK_API_KEY=sk-...
```

### Debugging HITL Issues
1. Check `pending_approvals` dict in API (in-memory, lost on restart)
2. Inspect `graph.get_state(config)` → `state.next` shows pending node
3. Verify `interrupt_before=["refund_tools"]` is set during graph compilation
4. Ensure checkpointer is passed to `create_graph(checkpointer=MemorySaver())`

### Viewing Traces

**Grafana Cloud** (OTEL branch, primary observability):
- URL: Your Grafana instance → Explore → Tempo
- Query: `{service.name="music-store-assistant"}`
- Shows: Token counts, latency, LLM provider metrics, tool execution, full trace hierarchy
- Provides: Dashboards, alerting, long-term retention, unified observability

## Troubleshooting

### Common Issues

1. **"No module named 'langchain_anthropic'"**
   - Solution: `uv add langchain-anthropic`, ensure `ANTHROPIC_API_KEY` is set

2. **HITL approval doesn't resume**
   - Check: Did you pass `checkpointer` to `create_graph()`?
   - Check: Is `thread_id` consistent between invoke and resume?
   - Check: Did you pass `context={"customer_id": ...}` on resume?

3. **OTEL traces not appearing in Grafana**
   - Verify endpoint: `echo $OTEL_EXPORTER_OTLP_ENDPOINT`
   - Test auth: `curl -H "$(echo $OTEL_EXPORTER_OTLP_HEADERS)" $OTEL_EXPORTER_OTLP_ENDPOINT/v1/traces`
   - Check logs: Should see "✅ OTEL tracing configured with OpenInference"

4. **Music Expert gives wrong results**
   - The model is told to ONLY use tool results, never general knowledge
   - Check if the right tool was called with correct arguments
   - Temperature is 0.7 for creativity, but tool calling should be deterministic

5. **Support Rep accesses wrong customer's data**
   - Verify `context={"customer_id": X}` is passed in invoke/resume
   - Check tool implementation uses `runtime.context.customer_id`, not state
   - Never trust customer_id from user messages or state

## Architecture Decisions

### Why Supervisor Pattern?
- Simplifies agent specialization (music vs support have different prompts, tools, temperatures)
- Enables easy routing rule changes without retraining
- Allows per-agent model selection (e.g., use cheap model for routing, powerful model for music)

### Why Separate Tool Nodes?
- `support_tools` (safe) vs `refund_tools` (HITL) allows conditional interrupts
- Only refunds require approval, not invoice lookups
- Simplifies conditional edge logic in `should_continue_support()`

### Why Context Schema?
- State is logged in traces → customer ID would be exposed
- LLMs can be prompt-injected to modify state → security risk
- Runtime context is hidden from LLM tool schema → secure by design

### Why OpenInference + OTEL?
- OpenInference provides rich LLM-specific spans (prompts, completions, token counts)
- Native OTEL instrumentation doesn't understand LangChain's abstractions
- Grafana Cloud provides long-term metric retention, alerting, and unified observability
- Attribute filtering keeps costs reasonable (raw OpenInference spans are huge)

## Related Documentation

- **README.md**: User-facing setup and usage guide
- **ARCHITECTURE.md**: Detailed system diagrams and component descriptions
- **TALK_TRACK.md**: Demo script with example conversations
- **DEMO_CHAT.md**: Sample chat transcripts for testing
- **.env.example**: Complete list of configuration options

## Observability Implementation

**Current State**: OpenTelemetry with OpenInference is the primary observability solution

**Key Components**:
- ✅ `src/otel.py` - OTLP exporter with attribute filtering
- ✅ `src/api.py` - Early OTEL initialization and shutdown hooks
- ✅ OpenInference auto-instrumentation for full LangGraph tracing
- ✅ Grafana Cloud integration via OTLP/HTTP

**Configuration**:
- Requires OTEL env vars for trace export (see `.env.example`)
- Gracefully skips tracing if OTEL credentials not configured
- No breaking changes to application logic

---

**Last Updated**: 2026-01-06
**Primary Contacts**: See repository contributors
**License**: MIT License - See LICENSE file
