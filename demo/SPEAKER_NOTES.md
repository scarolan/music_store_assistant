# 🎤 Speaker Notes - Quick Reference Card
**Print this or keep on phone during talk**

---

## ⏱️ TIMING CHECKPOINTS
- 2:00 → Start demo
- 5:00 → End demo, back to slides
- 7:00 → On takeaway slide
- 8:00 → Open Q&A

---

## 🎯 THE STRUCTURE

### 1. HOOK (0:30)
"Your AI is talking to itself... you have no idea what it's saying"
- Poll: Who's building with LLMs?
- Poll: Who knows exact cost?
- Metaphor: Teenagers

### 2. PAIN (1:00)
Three questions:
1. Why $12 conversation?
2. Why 47 DB calls?
3. Is prompt working?

Traditional obs → HTTP
AI obs → THOUGHTS

### 3. DEMO SETUP (0:30)
Architecture: Supervisor → Music Expert / Support Rep

### 4. HAPPY PATH (1:30)
Query: "What albums does Pink Floyd have?"
Show: Routing, tokens, tool call, cost ($0.0003), latency

### 5. CHAOS (1:30)
Long convo: Turn 1 (500 tok) → Turn 6 (2,800 tok) = **5.6x growth**
Math: "10K customers = 5x'd your bill"
Failed trace: 0 chars = burned tokens

### 6. THE MONEY SHOT (1:00)
Four superpowers:
1. Cost attribution (5x difference!)
2. Behavioral patterns (wasted calls)
3. Prompt validation (30% misrouted = broken)
4. Debugging (actual errors, not "500")

### 7. HOW (0:45)
OTEL + OpenInference + Grafana
30 mins, 5 lines of code

### 8. HOT TAKE (0:45)
"Flying blind without observability"
Don't know: what, cost, why fail, if prompts work
"Terrifying in production"

### 9. CTA (0:30)
QR codes: GitHub + Grafana Cloud
"30 minutes, you're welcome"

---

## 💪 POWER PHRASES

✅ "Flying blind"
✅ "That's terrifying"
✅ "Table stakes"
✅ "Million-dollar question"
✅ "You're welcome"
✅ "Hit me" (for Q&A)

❌ "Probably should"
❌ "It's complicated"
❌ "Maybe you could"

---

## 🎬 DEMO TRACES (Pre-identify!)

**Trace 1**: Clean music query (Pink Floyd)
**Trace 2**: long-convo-1 (6 turns, token growth)
**Trace 3**: Conversation #2 Metal queries (0 chars)

---

## 🔢 KEY NUMBERS

- 95 conversations
- 176+ requests
- **5.6x token growth**
- $0.0003-0.002 per query
- 17% error rate
- 30 min setup
- 5 lines code

---

## 🛡️ IF DEMO BREAKS

Say: "And THIS is why we need observability!"
Do: Switch to backup screenshots

---

## 🎤 OPENING (Memorize)

"Hey folks! Quick question - how many of you have built or are building with LLMs?"

[Hands up]

"Awesome. Now keep your hand up if you know EXACTLY how much each conversation costs you."

[Hands drop]

"Yeah, that's what I thought. Today I'm going to show you why your AI agents are basically teenagers..."

---

## 🏁 CLOSING (Memorize)

"Here's my hot take: If you're building AI agents without observability, you're flying blind."

[Pause]

"You don't know what they're doing, how much they're costing, why they fail, or if your prompts even work. In production, that's terrifying."

[Pause]

"The good news? It's not hard. [Point to QR codes] 30 minutes. You're welcome."

[Smile]

"Alright, I've got 2 minutes for questions. Hit me!"

---

## ❓ LIKELY QUESTIONS

**Q: Non-LangChain frameworks?**
A: OpenInference → LangChain, LlamaIndex, DSPy. Custom → raw OTEL (more manual).

**Q: Other providers (Anthropic/Google)?**
A: Yes! Token counts from ANY provider. Math changes, tokens universal.

**Q: Sensitive data / PII?**
A: Attribute filtering → DROP sensitive, KEEP metadata. Blog post available.

**Q: Grafana Cloud cost?**
A: Free tier = 50GB/month. Enough for most. Cost of obs << cost of wasted LLM calls.

**Q: Streaming?**
A: Yes! Captures when stream completes. Full tokens + latency.

---

## 🎯 BODY LANGUAGE

✅ Stand if possible
✅ Point at screen during demo
✅ Make eye contact during polls
✅ Smile when things work
✅ Pause after big numbers
✅ High energy throughout

---

## 🚨 WHAT NOT TO FORGET

- [ ] Server running
- [ ] Grafana loaded
- [ ] 3 traces identified
- [ ] Backup screenshots ready
- [ ] Phone on silent
- [ ] Water nearby
- [ ] BREATHE

---

## 💡 THE ONE THING

**If you forget everything else, remember this:**

The demo is the hero.
Your job: show them why observability matters.
How: real data, real costs, real problems solved.

**You've got this! 🎸🔥**
