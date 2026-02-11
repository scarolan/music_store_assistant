---
marp: true
theme: default
class: invert
paginate: true
backgroundColor: #1a1a1a
color: #ffffff
---

<!--
To convert to PDF/PPTX:
npm install -g @marp-team/marp-cli
marp slides.md --pdf
marp slides.md --pptx

Or use https://marp.app/ web editor
-->

# Your AI is Talking to Itself...
## And You Have No Idea What It's Saying

**A 7-Minute Journey into AI Observability**

🎸 Music Store Assistant Demo
🔍 Powered by Grafana Cloud + OpenTelemetry

---

# Quick Poll 🙋

## Who here is building with LLMs?
<!-- pause for hands -->

## Keep your hand up if you know EXACTLY how much each conversation costs...
<!-- most hands drop -->

---

# The Teenager Problem 🤦

## AI Agents are like teenagers:
- 💸 **Expensive** (your API bill proves it)
- 🎲 **Unpredictable** (why did it call that tool?)
- 👀 **Need constant supervision** (but you're flying blind)

**Unlike teenagers, we can actually observe what they're doing.**

---

# The Three Mysteries 🕵️

## When your AI is in production, you're asking:

1. 💰 **"Why did that conversation cost $12?"**
2. 🗄️ **"Why 47 database calls for ONE question?"**
3. 🤖 **"Is my system prompt even working?"**

---

# Traditional Observability vs AI Observability

| Traditional | AI Observability |
|-------------|-----------------|
| Sees HTTP requests | Sees agent decisions |
| Measures latency | Measures token usage |
| Logs errors | Logs reasoning chains |
| Shows "500 error" | Shows "Tool X failed because Y" |

**You need to see what your AI is THINKING, not just what it's DOING.**

---

# The Demo App: Algorhythm 🎸

```
User Query
    ↓
Supervisor (Router)
    ↓
    ├─→ Music Expert (creative, T=0.7)
    │   └─→ 5 catalog tools
    │
    └─→ Support Rep (precise, T=0)
        └─→ 3 support tools
            └─→ HITL approval gate for refunds
```

**Classic multi-agent architecture. Let's see what's really happening...**

---

<!--
DEMO SLIDE 1: Happy Path
Show: Customer UI + Grafana Dashboard side-by-side
Query: "What albums does Pink Floyd have?"
-->

# 🎬 LIVE DEMO: The Happy Path

## What you'll see in Grafana:
1. ✅ **Routing decision** - Supervisor → Music Expert
2. ✅ **Single LLM call** - Token counts visible
3. ✅ **One tool call** - `get_albums_by_artist('Pink Floyd')`
4. ✅ **Cost**: ~$0.0003
5. ✅ **Latency**: 1-2 seconds end-to-end

**This is what success looks like. But wait...**

---

<!--
DEMO SLIDE 2: The Chaos
Show: Long conversation trace (long-convo-1)
Highlight: Token growth across 6 turns
-->

# 🎬 LIVE DEMO: The Chaos

## Multi-turn conversation about jazz artists:

| Turn | Prompt Tokens | Growth |
|------|--------------|--------|
| 1    | 500          | 1.0x   |
| 2    | 850          | 1.7x   |
| 6    | 2,800        | 5.6x   |

**10,000 customers × 6 turns = you just 5x'd your API bill**

---

<!--
DEMO SLIDE 3: The Failure
Show: Trace with 0 response chars
-->

# 🎬 LIVE DEMO: The Failure

## Zero response characters = burned tokens for NOTHING

```
Agent called tool that doesn't exist
  → LLM hallucination
  → Error thrown
  → Tokens wasted
  → Customer sees error
  → You see... nothing (without observability)
```

**Without tracing, you'd never know this happened.**

---

# The Money Shot 💰

## What AI Observability Actually Gives You:

### 1. **Cost Attribution**
Music queries: $0.0004 | Support w/ refunds: $0.002 (5x!)

### 2. **Behavioral Patterns**
Agent called DB for question answered in system prompt

### 3. **Prompt Engineering Validation**
30% misrouted queries = your prompt is broken

### 4. **Actual Debugging**
Not "HTTP 500" → "Tool X, param Y, failed: timeout"

---

# How This Works 🛠️

```
Your App
    ↓
OpenTelemetry SDK (industry standard)
    ↓
OpenInference (LangChain-aware instrumentation)
    ↓
Grafana Cloud Tempo (trace storage + visualization)
```

## Setup time: **30 minutes**
## Lines of code: **~5**

---

# The Hot Take 🔥

## If you're building AI agents without observability...

# You're Flying Blind

You don't know:
- ❌ What they're actually doing
- ❌ How much they're costing
- ❌ Why they fail
- ❌ If your prompts work

**In production, that's terrifying.**

---

# The Good News ✨

## It's not hard.

1. ✅ OpenTelemetry SDK
2. ✅ OpenInference instrumentation
3. ✅ Grafana Cloud (free tier available)

## You can have this running in 30 minutes.

**Observability isn't optional. It's table stakes.**

---

# Try It Yourself 🚀

## 📦 Full Open Source Demo
**GitHub**: [scan QR code]
- Complete app code
- OTEL configuration
- Traffic generators
- Setup instructions

## ☁️ Grafana Cloud Free Tier
**Start Now**: [scan QR code]
- 50GB traces/month free
- No credit card required

---

# Questions? 🎤

## 2-3 minutes for Q&A

**Topics I can dive into:**
- Cost tracking across providers
- Handling sensitive data / PII
- Streaming responses
- Custom frameworks beyond LangChain
- Production deployment patterns

---

# Thank You! 🙌

## Key Takeaway:
**Your AI is making decisions and spending money.**
**Shouldn't you know what it's doing?**

---
**Contact**: [Your contact info]
**Demo Repo**: github.com/[your-repo]
**Grafana Cloud**: grafana.com/cloud

