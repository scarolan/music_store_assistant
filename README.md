# Music Store Assistant - Algorhythm Customer Support Bot

[![CI](https://github.com/scarolan/music_store_assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/scarolan/music_store_assistant/actions/workflows/ci.yml)

A LangGraph-based customer support chatbot demonstrating the Supervisor/Router pattern with Human-in-the-Loop (HITL) for sensitive operations.

## Architecture

```mermaid
flowchart TD
    Start((Start)) --> supervisor

    subgraph Routing["🎯 Supervisor Router"]
        supervisor{{"Supervisor<br/>(GPT-4o-mini)"}}
    end

    supervisor -->|"music query"| music_expert
    supervisor -->|"support query"| support_rep

    subgraph Music["🎵 Music Expert"]
        music_expert["Music Expert<br/>(GPT-4o-mini or Gemini)"]
        music_tools[["🔧 Music Tools<br/>• get_albums_by_artist<br/>• get_tracks_by_artist<br/>• check_for_songs<br/>• get_artists_by_genre<br/>• list_genres"]]
        music_expert -->|"needs data"| music_tools
        music_tools --> music_expert
    end

    subgraph Support["💼 Support Rep"]
        support_rep["Support Rep<br/>(GPT-4o)"]
        support_tools[["🔧 Safe Tools<br/>• get_invoice<br/>• get_customer_profile"]]
        refund_tools[["⚠️ HITL Tools<br/>• process_refund"]]
        
        support_rep -->|"safe operation"| support_tools
        support_rep -->|"refund request"| hitl
        support_tools --> support_rep
        
        subgraph HITL["🛑 Human-in-the-Loop"]
            hitl{{"Interrupt<br/>for Approval"}}
            hitl -->|"approved"| refund_tools
        end
        
        refund_tools --> support_rep
    end

    music_expert -->|"done"| End((End))
    support_rep -->|"done"| End

    style supervisor fill:#4a90d9,stroke:#2d5a87,color:#fff
    style music_expert fill:#50c878,stroke:#2d7a4a,color:#fff
    style support_rep fill:#f5a623,stroke:#c77d0a,color:#fff
    style hitl fill:#e74c3c,stroke:#a93226,color:#fff
    style music_tools fill:#e8f5e9,stroke:#81c784,color:#1a3d1a
    style support_tools fill:#fff3e0,stroke:#ffb74d,color:#5d4e37
    style refund_tools fill:#ffebee,stroke:#ef5350,color:#7a1f1f
```

### Flow Summary

| Component | Model | Purpose |
|-----------|-------|---------|
| **Supervisor** | GPT-4o-mini | Routes requests to Music Expert or Support Rep |
| **Music Expert** | GPT-4o-mini (or Gemini 2.0 Flash) | Catalog queries - albums, tracks, artists, genres |
| **Support Rep** | GPT-4o | Account info, invoices, refunds |
| **HITL Gate** | — | Requires human approval for refunds |

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
