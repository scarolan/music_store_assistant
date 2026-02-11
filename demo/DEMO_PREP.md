# 🎬 Demo Day Preparation Guide

**For: Lightning Talk on AI Observability**
**Presentation Duration: 10 minutes**
**Demo Duration: ~3 minutes within the presentation**

---

## 📋 Pre-Talk Checklist (Do This 1 Hour Before)

### 1. Server & Application
- [ ] Start the demo: `demo/start_demo.sh` (starts server + continuous traffic)
- [ ] Verify setup: `demo/preflight_check.sh`
- [ ] Verify traffic is generating: `tail -f /tmp/continuous-traffic.log`
- [ ] Customer UI loads: Open `http://localhost:8000` in browser
- [ ] Test a query: "What albums does Pink Floyd have?" - verify response
- [ ] Server logs are clean (no OTEL auth errors)

**Note**: Continuous traffic runs for 30 minutes, keeping your dashboard populated with fresh data throughout your talk.

### 2. Grafana Dashboard Setup
- [ ] Login to Grafana Cloud
- [ ] Navigate to Explore → Tempo
- [ ] Have this query ready: `{service.name="music-store-assistant"}`
- [ ] Test query returns traces
- [ ] Identify your 3 demo traces (see below)
- [ ] Bookmark/note their trace IDs for quick access

### 3. Browser Setup
- [ ] Close all unnecessary browser tabs
- [ ] Disable notifications (presentation mode)
- [ ] Set browser zoom to comfortable reading level
- [ ] Test screen sharing - make sure fonts are readable
- [ ] Open these tabs in order:
  1. Slides (slides.md converted to PDF/PPTX/HTML)
  2. Customer UI (`http://localhost:8000`)
  3. Grafana Dashboard (Tempo with query ready)
  4. Backup screenshots folder (just in case)

### 4. Demo Traces to Pre-Identify

Find and bookmark these 3 traces:

#### Trace #1: The Happy Path ✅
- **What to look for**: Single music query, clean execution, ~1-2 second duration
- **Good examples**: "What albums does Pink Floyd have?", "Do you have any jazz albums?"
- **What to show**:
  - Clean routing (Supervisor → Music Expert)
  - Single LLM call
  - One tool invocation
  - Token counts visible
  - Cost ~$0.0003

#### Trace #2: The Long Conversation 📈
- **What to look for**: `long-convo-1` or similar, 6 turns, token growth visible
- **What to show**:
  - First turn: ~500 tokens
  - Last turn: ~2,800 tokens (5.6x growth)
  - Cumulative token usage
  - How context builds up

#### Trace #3: The Failure 💥
- **What to look for**: Response with 0 characters, error indicator
- **Good examples**: Metal genre queries from conversation #2 (all returned 0 chars)
- **What to show**:
  - Agent made LLM call
  - Tool call attempted/failed
  - Tokens burned
  - Zero output to customer

### 5. Backup Screenshots (CRITICAL!)

Take screenshots of all 3 demo traces and save to `/tmp/screenshots/`:

```bash
mkdir -p /tmp/screenshots
# Then manually capture:
# - happy-path-trace.png (full Grafana trace view)
# - long-conversation-tokens.png (token growth visualization)
# - failed-trace-error.png (error trace with 0 chars)
# - dashboard-overview.png (high-level metrics view)
```

**Why?**: If live demo fails (network, Grafana slow, etc.), you can pivot to screenshots

---

## 🎤 Presentation Flow

### Timing Breakdown
- **0:00-2:00**: Slides only (build up the problem)
- **2:00-5:00**: LIVE DEMO (customer UI + Grafana)
- **5:00-7:30**: Slides (insights + takeaways)
- **7:30-10:00**: Q&A

### Demo Script (2:00-5:00)

#### Part 1: Setup (30 seconds)
**Say**: "Let me show you a real multi-agent system running on localhost right now."

**Do**:
- Show architecture slide (Supervisor → Music Expert / Support Rep)
- Keep it quick - don't dwell

#### Part 2: Happy Path Demo (1 minute 30 seconds)
**Say**: "Let me ask something simple: 'What albums does Pink Floyd have?'"

**Do**:
1. Split screen: Customer UI (left) + Grafana (right)
2. Type query in customer UI: "What albums does Pink Floyd have?"
3. Hit send
4. While waiting for response, say: "Watch the dashboard light up..."
5. When response arrives, switch to Grafana
6. Pull up the trace (use your pre-identified Trace #1)

**Show and Narrate**:
- "The Supervisor routed this to Music Expert" [point to routing span]
- "One LLM call - see the prompt tokens here: [X] and completion tokens: [Y]" [point]
- "It called the get_albums_by_artist tool" [point to tool span]
- "Total latency: 1.2 seconds" [point to duration]
- "Cost for this conversation: about $0.0003" [point to token counts]

**Transition**: "That's the happy path. But things get interesting when agents misbehave..."

#### Part 3: The Chaos (1 minute 30 seconds)
**Say**: "Now let's look at one of those long conversations - 6 questions in a row about jazz."

**Do**:
1. Switch to your pre-identified Trace #2 (long-convo-1)
2. Navigate to show multiple turns

**Show and Narrate**:
- "Turn 1: 500 prompt tokens" [point]
- "Turn 6: 2,800 prompt tokens" [point]
- "That's 5.6x growth - WHY? Full conversation history every time."
- "10,000 customers doing this? You just 5x'd your API bill without realizing."

**Transition**: "But wait, there's more..."

**Do**:
1. Switch to Trace #3 (the failure)
2. Show the error/zero response

**Show and Narrate**:
- "Zero response characters" [point]
- "The LLM hallucinated a tool call that doesn't exist"
- "Burned tokens for NOTHING"
- "Without tracing? You'd never know this happened."

#### Part 4: Wrap Demo (30 seconds)
**Say**: "So this isn't just nice to have - it's how you actually understand what your AI is doing."

**Do**:
- Quick switch back to slides
- Move to "The Money Shot" slide

---

## 🛡️ Backup Plans

### If Server Crashes
**Pivot**: "And THIS is exactly why we need observability - because stuff fails! Let me show you the screenshots from earlier..."

**Do**: Switch to backup screenshots, narrate the same way

### If Grafana is Slow/Unreachable
**Pivot**: "Looks like Grafana is having a moment. Good thing I took screenshots..."

**Do**: Switch to backup screenshots immediately

### If Query Fails
**Stay calm**: "Actually, this is perfect - watch how we can debug this in the trace..."

**Do**: Show the error trace as your "chaos" example instead

### If You're Running Over Time
**Skip**: Slide 7 (How This Works implementation details)

**Focus**: Problem → Demo → Insights → CTA

---

## 🎯 Key Metrics to Call Out

Have these numbers ready from your actual data:

- **Total conversations generated**: 95
- **Total API requests**: 176+
- **Token growth in long convos**: 5.6x
- **Cost range**: $0.0003 (music) to $0.002 (support)
- **Error rate**: ~17% (proves the point!)
- **Setup time**: 30 minutes
- **Lines of code**: ~5

---

## 💡 Pro Tips

### Energy Management
- **Start strong**: The "teenager" metaphor sets the tone
- **Peak energy at demo**: This is the money moment
- **Slow down for key numbers**: "Five point six times growth" not "5.6x"
- **End with confidence**: "You're welcome" with a smile

### Audience Engagement
- **Make eye contact** during the poll questions
- **Pause after big reveals** (e.g., 5x cost growth)
- **Use your hands** to point at screen during demo
- **Smile when things work** - show enthusiasm!

### Technical Execution
- **Practice the demo 3x** before going live
- **Know your keyboard shortcuts** (Alt+Tab, Cmd+Tab, etc.)
- **Have water nearby** - talking fast = dry mouth
- **Stand if possible** - better energy than sitting

### Dealing with Questions During Demo
**If someone interrupts with a question:**
- "Great question! Hold that thought - I'll address it in the Q&A"
- OR (if it's relevant): "Actually, let me show you that right now..." [use it as a demo opportunity]

---

## 🎬 Slide Transitions

When moving between slides and demo:

1. **Slides → Demo**: "Let me show you this live..."
2. **Demo → Slides**: "Alright, so what did we just learn?"
3. **Within Demo**: Use natural pauses while traces load

---

## 🎤 Opening Lines (Memorize These)

**Line 1**: "Hey folks! Quick question - how many of you have built or are building with LLMs?"

**Line 2** (after hands): "Awesome. Now keep your hand up if you know EXACTLY how much each conversation costs you."

**Line 3** (after most hands drop): "Yeah, that's what I thought."

**Line 4** (the hook): "Today I'm going to show you why your AI agents are basically teenagers - they're expensive, unpredictable, and they need constant supervision."

---

## 🏁 Closing Lines (Memorize These)

**Wrap-up**: "Here's my hot take: If you're building AI agents without observability, you're flying blind."

**Pause for effect**

**The list**: "You don't know what they're doing, how much they're costing, why they fail, or if your prompts even work."

**Pause**

**The reassurance**: "The good news? It's not hard. OpenTelemetry, OpenInference, Grafana Cloud. Done."

**Pause**

**The send-off**: "Everything I showed you is in that GitHub repo. You can have this running in 30 minutes. [Point to QR codes] You're welcome."

**Smile**

**Q&A opener**: "Alright, I've got 2 minutes for questions. Hit me!"

---

## 📞 Emergency Contacts

If tech fails completely:
- Have backup laptop ready
- Have slides on USB drive
- Have screenshots on phone (can AirDrop/share to backup device)

---

## ✅ Final 5-Minute Checklist (Right Before Talk)

- [ ] Server running (check browser)
- [ ] Grafana loaded (check traces appear)
- [ ] Slides cued to title slide
- [ ] Screen mirroring tested
- [ ] Phone on silent
- [ ] Notifications disabled
- [ ] Water bottle nearby
- [ ] Backup screenshots open (hidden tab)
- [ ] Deep breath
- [ ] Smile

**You've got this! 🎸🔥**

---

## 🎯 Post-Talk Actions

After the talk:
- [ ] Share QR codes in chat/email
- [ ] Follow up with interested attendees
- [ ] Post demo repo link
- [ ] Share slides (if requested)
- [ ] Capture any great questions for blog post ideas

---

**Remember**: The demo is the hero. The slides support the demo. You are the guide helping them see the light.

**Energy + Confidence + Real Data = Killer Talk**

**Break a leg! 🎭**
