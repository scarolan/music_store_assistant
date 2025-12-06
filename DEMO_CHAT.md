# 🎸 Algorhythm Music Store Assistant - Demo Script

This guide walks through demonstrating the key features of the Music Store Assistant.

**Total Demo Time:** ~20 minutes (10 min frontend + 10 min backend)

---

# Part 1: Customer-Facing UI Demo (~10 minutes)

> **Audience:** Business stakeholders, product managers, non-technical interviewers
> **Goal:** Show the end-user experience and business value

## Prerequisites for Part 1

1. Start the server:
   ```bash
   uv run uvicorn src.api:app --reload --port 8000
   ```

2. Open two browser tabs:
   - **Customer Chat**: http://localhost:8000
   - **Admin Dashboard**: http://localhost:8000/admin

---

## Demo Flow

### 1️⃣ Music Expert Path (~3 minutes)

These queries route to the **Music Expert** agent and demonstrate catalog browsing.

#### Ask about an artist:
```
What AC/DC albums do you carry?
```
> Shows: Supervisor routes to Music Expert → calls `get_albums_by_artist` tool

#### Ask about genres:
```
What jazz artists do you have?
```
> Shows: `get_artists_by_genre` tool with genre matching

#### Search for songs:
```
Do you have any songs with "love" in the title?
```
> Shows: `check_for_songs` tool with partial matching

#### List all genres:
```
What genres of music do you carry?
```
> Shows: `list_genres` tool returning full catalog categories

#### Follow-up (tests context retention):
```
What about metal?
```
> Shows: Supervisor correctly routes continuation to Music Expert

---

### 2️⃣ Support Rep Path (~2 minutes)

These queries route to the **Support Rep** agent and demonstrate account operations.

#### Ask about profile:
```
Can you tell me about my account?
```
> Shows: Supervisor routes to Support Rep → calls `get_customer_info` tool
> Note: Customer ID is injected from authenticated session (simulated)

#### Ask about invoices:
```
Show me my recent purchases
```
> Shows: `get_invoice` tool with customer context

---

### 3️⃣ Human-in-the-Loop Refund Flow (~4 minutes) ⚠️

This is the **key demo moment** - showing the HITL approval gate.

#### Step 1: Request a refund
```
I'd like a refund for invoice 134
```
> Shows: Support Rep looks up invoice, then calls `process_refund`
> Graph **interrupts** before executing the refund tool

#### Step 2: Check Admin Dashboard
Switch to the **Admin Dashboard** tab (http://localhost:8000/admin)
- You should see the pending refund request
- Review the details (invoice ID, customer, amount)

#### Step 3: Approve or Reject
- Click **Approve** to process the refund
- Click **Reject** to deny the request

#### Step 4: See the result
Switch back to the **Customer Chat** tab
- If approved: Customer sees refund confirmation
- If rejected: Customer sees apology message

> **Talk Track:** *"This is the key pattern for production AI. You wouldn't want an AI processing refunds without oversight. LangGraph's interrupt pattern gives humans the final word on sensitive operations."*

---

## Part 1 Wrap-Up

**Talk Track:** *"So that's the customer experience — natural conversation, instant catalog lookup, and human oversight for anything sensitive like refunds. Now let me show you what's happening under the hood in LangGraph Studio."*

---

# Part 2: Engineer-Facing LangGraph Studio Demo (~10 minutes)

> **Audience:** Engineering managers, technical interviewers, AI/ML teams
> **Goal:** Show the architecture, agent reasoning, and safety guardrails

## Prerequisites for Part 2

1. Open LangGraph Studio
2. Load the project: `music_store_assistant`
3. Ensure the graph visualization is visible
4. Have the thread panel ready for conversation

---

## 2.1 Multi-Tool Orchestration (~3 minutes)

**Talk Track:** *"Let me show you how the agent autonomously chains tools together to solve complex queries."*

### Demo: Genre Discovery → Track Lookup

#### Step 1: Ask about genres
```
What genres of music do you have?
```

**What to point out in Studio:**
- 🔀 Supervisor routes to `Music_Expert`
- 🔧 Agent calls `list_genres` tool
- 📋 Show the structured tool response (25 genres)
- ✅ Agent formats response naturally

#### Step 2: Drill into a genre
```
What tracks are in the Easy Listening genre?
```

**What to point out in Studio:**
- 🧠 *"Notice the agent is smart enough to figure out the workflow on its own"*
- 🔧 **First tool call:** `get_artists_by_genre("Easy Listening")` — gets artists
- 🔧 **Second tool call:** `get_tracks_by_artist` — iterates to get actual tracks
- 📊 Show the tool responses in sequence
- 💡 *"I didn't tell it to do two queries. It reasoned through the schema and realized it needed to chain these tools together."*

> **Key Message:** The agent understands the data model and orchestrates multiple tools autonomously.

---

## 2.2 Multi-Turn Conversation Context (~2 minutes)

**Talk Track:** *"Now let's see how the agent maintains context across a conversation."*

### Demo: Conversational Flow

```
I'm looking for some rock music
```
> Agent responds with rock artists

```
Tell me more about Led Zeppelin
```
> Agent calls `get_albums_by_artist("Led Zeppelin")`

```
What are their most popular songs?
```
> Agent calls `get_tracks_by_artist("Led Zeppelin")` — knows "their" = Led Zeppelin

**What to point out in Studio:**
- 📝 Show the `messages` array growing in state
- 🔗 Highlight how the third query is ambiguous without conversation history.
- 🧠 *"The agent resolved the pronoun 'their' by looking at conversation history"*
- 🤯 It's interesting to note that the LLM did a pretty good job picking the most popular songs, without any explicit instructions on how to do that!

---

## 2.3 Hallucination Prevention (~2 minutes)

**Talk Track:** *"One of the biggest risks with AI assistants is hallucination. Let me show you how we enforce strict compliance."*

### Demo: Artist Not in Catalog

```
Do you have any Michael Jackson albums?
```

**What to point out in Studio:**
- 🔧 Agent calls `get_albums_by_artist("Michael Jackson")`
- 📭 Tool returns **empty results**
- ✅ Agent says "We don't carry Michael Jackson" — doesn't make up albums!
- 💡 *"The prompt says 'ONLY use tool results, NEVER use general knowledge.' It could easily hallucinate Thriller, Bad, etc., but it doesn't."*

### Demo: Off-Topic Rejection

```
What's the weather like today?
```

**What to point out in Studio:**
- 🚫 Agent declines without calling any tools
- 📋 Show the system prompt constraint: "catalog recommendations only"
- 💡 *"This is prompt engineering in action — the agent stays in its lane."*

> **Key Message:** Guardrails prevent the model from going off-script or making things up.

---

## 2.4 Human-in-the-Loop Refund Flow (~3 minutes)

**Talk Track:** *"Now the most important pattern for production AI: human oversight for sensitive operations."*

### Demo: HITL Interrupt in LangGraph Studio

#### Step 1: Request a refund
```
I'd like a refund for invoice 134
```

**What to point out in Studio:**
- 🔀 Supervisor routes to `Support_Rep`
- 🔧 Agent attempts to call `process_refund(98)`
- ⚠️ **Graph INTERRUPTS** — show the visual interrupt indicator
- 💡 *"The graph has `interrupt_before` on the refund tool. Execution pauses here."*

#### Step 2: Show the interrupt state
- 📊 Click on the interrupted node
- 👀 Show the pending tool call in the state
- 💡 *"This is what gets sent to our admin queue. In production, this could go to Slack, email, or a ticketing system."*

#### Step 3: Resume or reject
- ✅ Click **Continue** in LangSmith studio
- 🔄 Watch the graph continue execution
- 📋 Show the final state with refund confirmation

> **Key Message:** LangGraph's interrupt pattern gives humans the final say on sensitive operations. This is essential for compliance, fraud prevention, and customer protection.

---

## Part 2 Wrap-Up

**Talk Track:** *"So to summarize the architecture: a Supervisor LLM routes to specialized workers, each with their own tools. Read-only operations flow through automatically. Write operations like refunds hit a HITL gate. And everything is observable in LangSmith for debugging and optimization."*

---

## Bonus: LangSmith Observability (if time allows)

If the interviewer is interested in observability, switch to [LangSmith](https://smith.langchain.com):

1. Filter by project: `music-store-assistant`
2. Show the supervisor routing decisions
3. Drill into tool calls and token usage
4. Filter out test traces: `Tag is not test`
5. Show CI runs: `Tag = ci-cd`

**Talk Track:** *"Everything we just did is fully traced here. I can see exactly what the model was thinking, how long each step took, and what it cost. This is how you debug and optimize in production."*

---

## Anticipated Q&A Topics

Be ready for questions like:

| Topic | Quick Answer |
|-------|--------------|
| *"How do you handle auth?"* | Customer ID injected via config from JWT session — never asked from user |
| *"Why separate agents?"* | Principle of least privilege — Music Expert has no access to billing tools |
| *"What about rate limiting?"* | LangSmith tracks usage; could add token budgets per conversation |
| *"How would this scale?"* | Stateless workers + Redis checkpointer = horizontal scaling |
| *"Cost per conversation?"* | Show LangSmith traces — typically 3-5 LLM calls per turn |
| *"Why LangGraph vs raw LangChain?"* | Graph structure = visual debugging, interrupts, stateful checkpointing |
| *"What about prompt injection?"* | System prompts enforce role boundaries; could add guardrails layer |
| *"Testing strategy?"* | Pytest with mocked LLM responses; CI runs on every PR |

---

## Architecture Highlights to Mention

- **Supervisor Pattern**: Single router LLM decides which specialist handles each request
- **Tool Isolation**: Music Expert has read-only tools, Support Rep has write tools
- **HITL Gate**: Sensitive operations (refunds) require human approval
- **State Persistence**: Checkpointer enables conversation resumption after approval
- **Configurable Models**: Music Expert can use Gemini or OpenAI (`MUSIC_EXPERT_MODEL` env var)

---

## Quick Reference: Demo Timeline

| Section | Time | Key Point |
|---------|------|-----------|
| **Part 1: UI Demo** | 10 min | Customer experience |
| Music Expert | 3 min | Catalog browsing |
| Support Rep | 2 min | Account lookups |
| HITL Refund | 4 min | ⭐ Human approval flow |
| **Part 2: Studio Demo** | 10 min | Architecture deep-dive |
| Multi-Tool | 3 min | Agent chains tools autonomously |
| Multi-Turn | 2 min | Context retention |
| Hallucination | 2 min | ⭐ Strict compliance |
| HITL in Studio | 3 min | ⭐ Interrupt visualization |
