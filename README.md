# Music Store Assistant - Algorhythm Customer Support Bot

[![CI](https://github.com/scarolan/music_store_assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/scarolan/music_store_assistant/actions/workflows/ci.yml)

A LangGraph-based customer support chatbot demonstrating the Supervisor/Router pattern with Human-in-the-Loop (HITL) for sensitive operations.

## Architecture

```
                    ┌─────────────┐
                    │  Supervisor │
                    │  (Router)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌─────────┐
        │  Music   │ │ Support  │ │   END   │
        │  Expert  │ │   Rep    │ │         │
        └──────────┘ └──────────┘ └─────────┘
                           │
                           ▼ (HITL for refunds)
                     ┌──────────┐
                     │  Human   │
                     │ Approval │
                     └──────────┘
```

## Setup

1. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your-key-here
   LANGCHAIN_API_KEY=your-key-here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=music-store-assistant
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Download the Chinook database (if not present):
   ```bash
   curl -o Chinook.db https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite
   ```

## Usage

```python
from src.graph import create_graph

graph = create_graph()
config = {"configurable": {"customer_id": 1}}

result = graph.invoke({"messages": [("user", "What albums does AC/DC have?")]}, config)
```

## Testing

```bash
pytest
```

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── graph.py        # Main LangGraph definition
│   ├── state.py        # TypedDict state schema
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── music.py    # Read-only catalog tools
│   │   └── support.py  # Sensitive write tools (HITL)
│   └── utils.py        # Database utilities
├── tests/              # Pytest test suite
├── Chinook.db          # SQLite database
└── pyproject.toml
```
