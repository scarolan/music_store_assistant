# 🎸 Demo Materials for Lightning Talk

This directory contains everything you need for the "Demystifying AI Observability" lightning talk.

## 🚀 Quick Start

From the repository root:

```bash
# Start demo (server + continuous traffic for 30 mins)
demo/start_demo.sh

# Validate everything is ready
demo/preflight_check.sh

# Stop demo cleanly
demo/stop_demo.sh
```

## 📁 Contents

### Scripts
- **`start_demo.sh`** - Launches server and continuous traffic generation
- **`stop_demo.sh`** - Stops server and traffic cleanly
- **`preflight_check.sh`** - Validates setup without starting anything
- **`continuous_traffic.py`** - 30-minute continuous traffic generator
- **`generate_traffic.py`** - Burst traffic (15 short conversations)
- **`generate_long_conversations.py`** - Long multi-turn conversations (high token usage)

### Presentation Materials
- **`slides.md`** - Full slide deck (Marp-compatible, convert to PDF/PPTX)
- **`LIGHTNING_TALK.md`** - Complete talk track with timing and slides
- **`SPEAKER_NOTES.md`** - One-page cheat sheet (print/save to phone)
- **`TALK_CHEATSHEET.md`** - Extended reference with all details
- **`DEMO_PREP.md`** - Pre-talk preparation checklist

## 📖 Usage

### For the Lightning Talk

1. **Before the Talk** (1 hour prior):
   ```bash
   demo/start_demo.sh           # Start everything
   demo/preflight_check.sh      # Validate setup
   tail -f /tmp/continuous-traffic.log  # Monitor traffic
   ```

2. **Identify Your Demo Traces** in Grafana:
   - Happy path: Clean music query
   - Long conversation: Token growth over 6 turns
   - Failed trace: 0-char response showing wasted tokens

3. **Take Backup Screenshots** (save to `/tmp/screenshots/`):
   - Happy path trace
   - Long conversation with token growth
   - Failed trace
   - Dashboard overview

4. **Review Materials**:
   ```bash
   cat demo/SPEAKER_NOTES.md    # Your pocket reference
   marp demo/slides.md --pdf    # Convert slides
   ```

5. **After the Talk**:
   ```bash
   demo/stop_demo.sh            # Clean shutdown
   ```

### For Testing/Practice

```bash
# Generate burst traffic manually
uv run python demo/generate_traffic.py

# Generate long conversations (drives up prompt tokens)
uv run python demo/generate_long_conversations.py

# Monitor server logs
tail -f /tmp/music-store.log

# Monitor traffic generation
tail -f /tmp/continuous-traffic.log
```

## 🎯 Key Features

- **Continuous Traffic**: Runs for 30 minutes, generates 1 request every 3-7 seconds
- **Realistic Mix**: 70% music queries, 30% support queries
- **Dashboard-Friendly**: Keeps Grafana graphs populated with fresh data
- **Failure Examples**: Some queries intentionally fail (perfect for demo!)
- **Token Growth Demo**: Long conversations show 5.6x token growth

## 💡 Tips

- Run `demo/start_demo.sh` at least 10 minutes before your talk
- Continuous traffic keeps dashboards lively during presentation
- Practice the demo flow 3+ times
- Have backup screenshots ready (WiFi may fail during demo)
- The "errors" in logs are actually great demo material!

## 🔗 Related Docs

- **Main README**: `../README.md` - Full application documentation
- **Architecture**: `../ARCHITECTURE.md` - System design details
- **Talk Track**: `TALK_TRACK.md` - Example demo conversations

---

**Presentation Duration**: 10 minutes (7 min talk + 3 min Q&A)
**Audience**: Semi-technical
**Theme**: Making AI observability accessible and essential
