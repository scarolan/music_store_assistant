# Project: Music Store Support Bot (LangChain/LangGraph Demo)

## 1. Mission Profile
We are building a **Customer Support Bot** for a fictional music store called Algorhythm.
**Goal:** Demonstrate "Deployed Engineer" competency by migrating a raw Jupyter notebook into a production-ready **LangGraph** architecture.
**Key Features:** Supervisor/Router architecture, Human-in-the-Loop (HITL) for refunds, and strict Data/Privacy scoping.

**The Persona:** Senior Solutions Architect. Code must be clean, typed, modular, and designed for readability by a customer.

## 2. Technical Stack & Environment
* **OS:** Ubuntu 22.04 (Target Deployment)
* **Language:** Python 3.11+
* **Frameworks:** `langgraph`, `langchain`, `langchain-openai`, `langchain-community`
* **Database:** SQLite (`Chinook.db`)
* **Testing:** `pytest` (Strict TDD)
* **Observability:** LangSmith (Must be configured via `.env`)
* **Package Manager:** `uv` (Always use `uv run` to execute commands)
* **Virtual Environment:** Always use `.venv` in the project root. **NEVER use system Python.**
  * Run commands with: `uv run pytest`, `uv run python`, etc.
  * Or activate first: `source .venv/bin/activate`

## 3. Development Methodology: TDD (Non-Negotiable)
We follow a strict Test-Driven Development cycle. **Do not write implementation code until a test exists.**
1.  **Write the Test:** Create a new test file in `tests/` defining the expected behavior (e.g., `test_router_selects_music_tool.py`).
2.  **Verify Failure:** Acknowledge that the test fails (or mock it).
3.  **Implement:** Write the minimal code in `src/` to pass the test.
4.  **Refactor:** Clean up.

## 4. Architecture: The Supervisor Pattern
We are refactoring the flat notebook into a StateGraph. The notebook code can be found here:
 
* **State:** Define a `TypedDict` containing `messages` (list of BaseMessage) and `customer_id` (int).
* **Nodes:**
    * `Supervisor` (LLM Router): Decides next step based on user intent.
    * `Music_Expert`: Read-only tools for querying the catalog.
    * `Support_Rep`: Write/Sensitive tools (Invoice lookup, Refunds).
* **Edges:**
    * Conditional edges from `Supervisor` to workers.
    * Workers return to `Supervisor` (or END).
* **Safety:** The `Support_Rep` node must have an `interrupt_before` check for "Refund" actions (HITL).

## 5. LangChain Best Practices (Strict Adherence)
* **State Management:** Always use `Annotated[list, add_messages]` for message history.
* **Tooling:** Use the `@tool` decorator. Always include a docstring for tools so the LLM knows when to use them.
* **SQL Safety:** Do not write raw SQL execution strings unless necessary. Use `create_sql_query_chain` where possible, but ensure it is scoped.
* **Secrets:** Never hardcode API keys. Use `python-dotenv`.

## 6. MVP Constraints 
* **Focus on Tooling:** The complexity should be in the *Graph orchestration*, not the SQL query.
* **Don't Over-Engineer Data:** The Chinook dataset is imperfect. If a query is hard, mock the behavior or simplify the request.
* **Privacy:** We must be able to explain *why* we chose a specific auth method.
    * *Decision:* We will inject `customer_id` via configuration/state to simulate an authenticated session (JWT style), rather than asking the user for it.

## 7. Folder Structure
```text
.
├── .env                # API Keys (OpenAI, LangSmith)
├── src/
│   ├── graph.py        # Main LangGraph definition
│   ├── state.py        # TypedDict definitions
│   ├── tools/
│   │   ├── music.py    # Read-only tools
│   │   └── support.py  # Write tools
│   └── utils.py
├── tests/              # Pytest files
├── notebooks/          # The original starter notebook (reference only)
├── Chinook.db
└── requirements.txt