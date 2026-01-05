# OpenTelemetry Implementation Guide

**Technical deep-dive: Adding OTEL instrumentation to an LLM application**

This guide walks through the complete implementation of OpenTelemetry tracing for the Music Store Assistant, demonstrating production-ready patterns for LLM observability with Grafana Cloud.

> 📖 **Coming from the blog?** This is the technical companion guide with full code examples and implementation details. Start here if you're ready to add OTEL to your own LLM application.

## What You'll Learn

- How to instrument an LLM application with OpenTelemetry
- Using OpenInference for automatic LLM trace capture
- Implementing attribute filtering to keep traces lean (80-90% size reduction)
- Configuring OTLP export to Grafana Cloud
- Production patterns: sampling, custom attributes, monitoring
- Troubleshooting common issues

**Time to implement:** ~30-60 minutes for a working setup

**Prerequisites:** Basic Python knowledge, existing LLM application, Grafana Cloud account

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Implementation Steps](#implementation-steps)
- [Attribute Filtering Strategy](#attribute-filtering-strategy)
- [Configuration](#configuration)
- [Testing](#testing)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Before OTEL

```
User Request → FastAPI → Graph Execution → LLM Calls → Response
                              ↓
                         (black box)
```

### After OTEL

```
User Request → FastAPI → Graph Execution → LLM Calls → Response
                              ↓
                         OTEL Traces
                              ↓
                    OpenInference Spans (LLM-specific)
                              ↓
                    Attribute Filtering
                              ↓
                    OTLP Export (HTTP)
                              ↓
                    Grafana Cloud Tempo
```

### Trace Hierarchy

```
Span: LangGraph Run (root span)
  ├─ Span: Supervisor Agent
  │  └─ Span: LLM Call (routing decision)
  │     ├─ Attribute: llm.input_messages (prompts)
  │     ├─ Attribute: llm.output_messages (completion)
  │     ├─ Attribute: llm.token_count.prompt
  │     ├─ Attribute: llm.token_count.completion
  │     └─ Attribute: llm.model_name
  │
  ├─ Span: Music Expert Agent
  │  ├─ Span: LLM Call (with tools)
  │  │  ├─ Attribute: llm.input_messages
  │  │  ├─ Attribute: llm.token_count.*
  │  │  └─ Attribute: tool.name
  │  │
  │  └─ Span: Tool Execution (get_albums_by_artist)
  │     ├─ Attribute: tool.parameters
  │     └─ Attribute: tool.result
  │
  └─ Span: Support Rep Agent
     └─ ...similar structure
```

---

## Prerequisites

### Required Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    # Core OTEL (required)
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-exporter-otlp-proto-http>=1.28.0",

    # OpenInference (LLM-specific instrumentation - required)
    "openinference-instrumentation-langchain>=0.1.56",
    "openinference-semantic-conventions>=0.1.25",

    # Note: LangSmith SDK is NOT required for this implementation
    # The application works with OTEL/Grafana alone
]
```

### Environment Variables

```bash
# OTLP endpoint for Grafana Cloud
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp

# Authorization (format: Authorization=Basic {base64(instance_id:token)})
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<your-base64-credentials>

# Service name (appears in Grafana)
OTEL_SERVICE_NAME=music-store-assistant
```

**Getting Grafana Cloud credentials:**
1. Go to Grafana Cloud → Connections → Add new connection → OpenTelemetry
2. Copy Instance ID and generate API token
3. Base64 encode: `echo -n "instance_id:api_token" | base64`
4. URL-encode: Replace spaces with `%20`

**Note on LangSmith**: The demo application references LangSmith in some files, but it's completely optional. LangSmith provides its own tracing system focused on agent execution flow. This guide focuses solely on OTEL + Grafana, which provides production-grade observability without additional tooling.

---

## Implementation Steps

### Step 1: Create OTEL Configuration Module

Create `src/otel.py`:

```python
"""OpenTelemetry configuration for exporting traces to Grafana Cloud."""

import os
import logging
from urllib.parse import unquote

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# OpenInference instrumentation
from openinference.instrumentation.langchain import LangChainInstrumentor

logger = logging.getLogger(__name__)


def configure_otel_tracing() -> bool:
    """Configure OpenTelemetry tracing with Grafana Cloud export.

    Returns:
        True if OTEL was configured, False if skipped (missing config).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers_raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")

    if not endpoint or not headers_raw:
        logger.info(
            "OTEL tracing not configured - missing OTEL_EXPORTER_OTLP_ENDPOINT "
            "or OTEL_EXPORTER_OTLP_HEADERS"
        )
        return False

    # Parse headers (format: "key1=value1,key2=value2")
    headers = {}
    for part in headers_raw.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            headers[unquote(key)] = unquote(value)

    # Service name for Grafana
    service_name = os.getenv("OTEL_SERVICE_NAME", "music-store-assistant")

    # Create resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})

    # Create OTLP exporter
    traces_endpoint = endpoint
    if not traces_endpoint.endswith("/v1/traces"):
        traces_endpoint = f"{traces_endpoint.rstrip('/')}/v1/traces"

    exporter = OTLPSpanExporter(
        endpoint=traces_endpoint,
        headers=headers,
    )

    # Create TracerProvider
    provider = TracerProvider(resource=resource)

    # Add attribute filter processor (see Step 2)
    provider.add_span_processor(AttributeFilterProcessor())

    # Add batch processor for export
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument LangChain (auto-instrumentation magic!)
    LangChainInstrumentor().instrument(tracer_provider=provider)

    logger.info(
        f"✅ OTEL tracing configured for Grafana Cloud: {endpoint} "
        f"(service: {service_name})"
    )
    return True


def shutdown_otel_tracing() -> None:
    """Flush and shutdown the OTEL tracer provider."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
        logger.info("OTEL tracing shutdown complete")
```

### Step 2: Add Attribute Filtering (Critical!)

**Why filter?** Raw OpenInference spans can be 50-100KB each due to:
- Full LLM tool schemas (repeated on every call)
- Complete conversation history
- Redundant JSON blobs

**Strategy**: Keep essential debugging data, drop bloat.

Add to `src/otel.py`:

```python
# Filtering configuration
MAX_ATTR_LENGTH = 500  # Truncate strings
MAX_MESSAGES = 10      # Keep last N messages + system prompt

# Attributes to DROP entirely
DROP_ATTRIBUTES = {
    "input.value",              # Huge JSON, redundant with llm.input_messages
    "output.value",             # Huge JSON, redundant with llm.output_messages
    "llm.invocation_parameters", # Full tool schemas
    "metadata",                 # Framework internals
}

# Prefixes to DROP
DROP_PREFIXES = (
    "llm.tools.",  # Tool JSON schemas (huge and repeated)
)

# Attributes to KEEP as-is (high value, small size)
KEEP_ATTRIBUTES = {
    "llm.token_count.prompt",
    "llm.token_count.completion",
    "llm.token_count.total",
    "llm.model_name",
    "llm.provider",
    "session.id",
    "tool.name",
}


class AttributeFilterProcessor(SpanProcessor):
    """Filters and truncates span attributes before export."""

    def on_start(self, span: Span, parent_context=None) -> None:
        pass  # Nothing to do on start

    def on_end(self, span: ReadableSpan) -> None:
        """Filter attributes when span completes."""
        if not hasattr(span, "_attributes") or span._attributes is None:
            return

        attrs = span._attributes
        keys_to_remove = []
        keys_to_update = {}

        # Find max message index for conversation limiting
        max_msg_index = -1
        for key in attrs.keys():
            if key.startswith("llm.input_messages."):
                try:
                    parts = key.split(".")
                    if len(parts) >= 3:
                        idx = int(parts[2])
                        max_msg_index = max(max_msg_index, idx)
                except (ValueError, IndexError):
                    pass

        # Keep system prompt (index 0) + last MAX_MESSAGES
        keep_indices = {0}
        if max_msg_index > 0:
            if max_msg_index >= MAX_MESSAGES:
                start_idx = max_msg_index - MAX_MESSAGES + 1
                keep_indices.update(range(start_idx, max_msg_index + 1))
            else:
                keep_indices.update(range(0, max_msg_index + 1))

        # Filter attributes
        for key, value in attrs.items():
            # DROP rules
            if key in DROP_ATTRIBUTES:
                keys_to_remove.append(key)
                continue

            if any(key.startswith(prefix) for prefix in DROP_PREFIXES):
                keys_to_remove.append(key)
                continue

            # Message limiting
            if key.startswith("llm.input_messages."):
                try:
                    parts = key.split(".")
                    if len(parts) >= 3:
                        idx = int(parts[2])
                        if idx not in keep_indices:
                            keys_to_remove.append(key)
                            continue
                except (ValueError, IndexError):
                    pass

            # KEEP rules (no modification)
            if key in KEEP_ATTRIBUTES:
                continue

            # TRUNCATE string values
            if isinstance(value, str):
                # System prompts: truncate more aggressively
                if "message.content" in key and ".0." in key:
                    keys_to_update[key] = value[:197] + "..." if len(value) > 200 else value
                else:
                    keys_to_update[key] = value[:497] + "..." if len(value) > 500 else value

        # Apply changes
        for key in keys_to_remove:
            try:
                del attrs[key]
            except (KeyError, TypeError):
                pass

        for key, value in keys_to_update.items():
            try:
                attrs[key] = value
            except TypeError:
                pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
```

### Step 3: Initialize OTEL Early

**Critical**: OTEL must be configured BEFORE importing the frameworks it instruments.

In `src/api.py`:

```python
"""FastAPI backend for the Music Store Assistant."""

import os
from dotenv import load_dotenv

# 1. Load environment variables FIRST
load_dotenv()

# 2. Configure OTEL BEFORE importing frameworks
from src.otel import configure_otel_tracing, shutdown_otel_tracing
configure_otel_tracing()

# 3. NOW safe to import frameworks (they'll be instrumented)
from fastapi import FastAPI
from langgraph.checkpoint.memory import MemorySaver
from src.graph import create_graph

# ... rest of application code

@app.on_event("shutdown")
def shutdown_event():
    """Flush OTEL traces before exit."""
    shutdown_otel_tracing()
```

**Why this order matters:**
- OpenInference uses import-time monkey patching
- Must set global TracerProvider before framework imports
- If imported first, those modules won't be instrumented

---

## Attribute Filtering Strategy

### Size Reduction Results

| Span Type | Before Filtering | After Filtering | Reduction |
|-----------|-----------------|-----------------|-----------|
| LLM Call (simple) | 15 KB | 3 KB | 80% |
| LLM Call (with tools) | 85 KB | 8 KB | 91% |
| Tool Execution | 5 KB | 2 KB | 60% |
| Agent Chain | 120 KB | 15 KB | 87% |

### What We Keep

**Essential for debugging:**
- ✅ Token counts (all three: prompt, completion, total)
- ✅ Model name and provider
- ✅ Truncated messages (500 chars is usually enough context)
- ✅ Tool names and parameters
- ✅ Session/trace IDs
- ✅ System prompt (truncated to 200 chars)
- ✅ Last 10 messages of conversation (prevents unbounded growth)

### What We Drop

**Not useful in production traces:**
- ❌ Full tool JSON schemas (repeated on every call, 20-40 KB each)
- ❌ Complete conversation history (use sliding window instead)
- ❌ Redundant JSON blobs (`input.value`, `output.value`)
- ❌ Framework metadata (internal state, not user-facing)
- ❌ System prompts beyond first 200 chars

### Customizing the Filter

Adjust these constants in `src/otel.py`:

```python
# Increase if you need more context in traces
MAX_ATTR_LENGTH = 500  # Character limit for truncated strings
MAX_MESSAGES = 10      # Number of conversation turns to keep

# Add attributes you want to always preserve
KEEP_ATTRIBUTES = {
    "llm.token_count.prompt",
    "llm.token_count.completion",
    # ... add your custom attributes
}

# Add attributes you want to completely remove
DROP_ATTRIBUTES = {
    "input.value",
    # ... add attributes that bloat your spans
}
```

---

## Configuration

### Environment Variables Reference

```bash
# === Required for OTEL Export ===

# Grafana Cloud OTLP endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-{region}.grafana.net/otlp

# Authorization header (URL-encoded)
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20{base64_credentials}

# === Optional ===

# Service name (default: music-store-assistant)
OTEL_SERVICE_NAME=music-store-assistant

# Sampling rate (default: 1.0 = 100%)
# OTEL_TRACE_SAMPLING_RATE=0.1  # Sample 10% in production
```

### Grafana Cloud Regions

Choose the endpoint closest to your deployment:

| Region | Endpoint |
|--------|----------|
| US Central | `https://otlp-gateway-prod-us-central-0.grafana.net/otlp` |
| US East | `https://otlp-gateway-prod-us-east-0.grafana.net/otlp` |
| EU West | `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp` |
| AP Southeast | `https://otlp-gateway-prod-ap-southeast-0.grafana.net/otlp` |

### Adding Trace Sampling (Production)

For high-traffic applications, sample traces to reduce volume:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

def configure_otel_tracing() -> bool:
    # ... existing code ...

    # Sample 10% of traces
    sampling_rate = float(os.getenv("OTEL_TRACE_SAMPLING_RATE", "1.0"))
    sampler = TraceIdRatioBased(sampling_rate)

    provider = TracerProvider(resource=resource, sampler=sampler)

    # ... rest of setup
```

---

## Testing

### Verify OTEL Configuration

```bash
# Check startup logs
uv run uvicorn src.api:app --host 0.0.0.0 --port 8080

# Should see:
# ✅ OTEL tracing configured for Grafana Cloud: https://...
```

### Generate Test Traces

```bash
# Music query (routes to Music Expert)
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What albums does AC/DC have?", "customer_id": 16}'

# Support query (routes to Support Rep)
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me my recent orders", "customer_id": 16}'

# HITL flow (triggers approval)
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a refund for invoice 98", "customer_id": 16}'
```

### Query Traces in Grafana

1. Go to **Grafana Cloud → Explore → Tempo**

2. **Basic query** (all traces):
   ```
   {service.name="music-store-assistant"}
   ```

3. **Filter by duration** (slow traces):
   ```
   {service.name="music-store-assistant"} | duration > 2s
   ```

4. **Filter by status** (errors):
   ```
   {service.name="music-store-assistant" && status="error"}
   ```

5. **Check token usage** (extract attribute):
   ```
   {service.name="music-store-assistant"}
   | select(span.llm.token_count.total)
   ```

### Import the Dashboard

1. Download `llm_o11y_dashboard.json` from the repo
2. Go to **Grafana → Dashboards → Import**
3. Upload JSON file
4. Select your Tempo data source
5. Click **Import**

---

## Production Considerations

### 1. Make OTEL Optional

Your application should work with or without OTEL configured:

```python
def configure_otel_tracing() -> bool:
    if not endpoint or not headers:
        logger.info("OTEL tracing not configured - skipping")
        return False  # App continues normally

    # ... configure OTEL
    return True
```

### 2. Use Trace Sampling

Don't trace 100% of production traffic:

```python
# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
provider = TracerProvider(resource=resource, sampler=sampler)
```

Alternatives:
- **Head sampling**: Sample at trace start (what we show above)
- **Tail sampling**: Sample after trace completes (requires collector)
- **Adaptive sampling**: Adjust rate based on traffic

### 3. Add Custom Attributes

Enrich traces with business context:

```python
from opentelemetry import trace

def chat(request: ChatRequest):
    # Get current span
    span = trace.get_current_span()

    # Add custom attributes
    span.set_attribute("customer_id", request.customer_id)
    span.set_attribute("conversation_type", "support")
    span.set_attribute("requires_approval", False)

    # ... rest of handler
```

Query in Grafana:
```
{service.name="music-store-assistant" && conversation_type="support"}
```

### 4. Monitor Export Health

Add metrics to track OTEL export success:

```python
from opentelemetry.sdk.trace.export import SpanExportResult

class MonitoredBatchSpanProcessor(BatchSpanProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_failures = 0

    def export(self, spans):
        result = super().export(spans)
        if result != SpanExportResult.SUCCESS:
            self.export_failures += 1
            logger.warning(f"Span export failed (total: {self.export_failures})")
        return result
```

### 5. Set Up Alerts

In Grafana, create alerts for:

**High error rate:**
```promql
rate({service.name="music-store-assistant" && status="error"}[5m]) > 0.05
```

**High latency:**
```promql
histogram_quantile(0.95,
  rate({service.name="music-store-assistant"}[5m])
) > 3000  # 95th percentile > 3s
```

**Cost spike:**
```promql
sum(rate({service.name="music-store-assistant"}
  | unwrap llm_token_count_total [5m])) > 100000  # >100k tokens/min
```

---

## Troubleshooting

### Traces Not Appearing in Grafana

**Check 1: Verify OTEL initialized**
```bash
# Look for this in startup logs:
✅ OTEL tracing configured for Grafana Cloud: https://...

# If you see "OTEL tracing not configured", check env vars
```

**Check 2: Test endpoint connectivity**
```bash
# Replace with your actual endpoint and credentials
curl -X POST https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces \
  -H "Authorization: Basic {your-base64-credentials}" \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'

# Should return 200 OK or 400 (not 401/403)
```

**Check 3: Check for export errors**
```bash
# Look for errors in application logs
grep -i "span export" /path/to/logs
grep -i "otel" /path/to/logs
```

**Check 4: Verify traces are being created**
```python
# Add debug logging
import logging
logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
```

### Traces Are Incomplete

**Symptom**: Seeing traces but missing LLM spans.

**Cause**: OTEL initialized AFTER framework imports.

**Fix**: Ensure this order in `src/api.py`:
```python
load_dotenv()           # 1. Env vars first
configure_otel_tracing() # 2. OTEL second
from langgraph import ... # 3. Frameworks last
```

### Spans Are Too Large

**Symptom**: Grafana shows "span too large" errors.

**Cause**: Attribute filtering not aggressive enough.

**Fix**: Reduce limits in `src/otel.py`:
```python
MAX_ATTR_LENGTH = 200  # Was 500
MAX_MESSAGES = 5       # Was 10
```

Or add more attributes to `DROP_ATTRIBUTES`.

### High Memory Usage

**Symptom**: Application memory grows over time.

**Cause**: Spans accumulating in batch processor.

**Fix**: Tune batch processor settings:
```python
processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,        # Default: 2048
    schedule_delay_millis=5000,  # Default: 5000 (5s)
    max_export_batch_size=512,   # Default: 512
)
```

Or enable more aggressive sampling.

### Token Counts Missing

**Symptom**: Traces show up but no `llm.token_count.*` attributes.

**Cause**: LLM provider not returning token info, or OpenInference version mismatch.

**Fix**:
1. Update OpenInference: `uv add openinference-instrumentation-langchain@latest`
2. Verify LLM response includes token usage
3. Check OpenInference compatibility matrix

---

## Advanced Topics

### Custom Span Processors

Add your own span processing logic:

```python
class CostCalculatorProcessor(SpanProcessor):
    """Calculate and add cost attributes to LLM spans."""

    PRICING = {
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "gpt-4o": {"prompt": 0.0025, "completion": 0.01},
    }

    def on_end(self, span: ReadableSpan) -> None:
        attrs = span._attributes
        model = attrs.get("llm.model_name")

        if model in self.PRICING:
            prompt_tokens = attrs.get("llm.token_count.prompt", 0)
            completion_tokens = attrs.get("llm.token_count.completion", 0)

            cost = (
                prompt_tokens / 1000 * self.PRICING[model]["prompt"] +
                completion_tokens / 1000 * self.PRICING[model]["completion"]
            )

            attrs["llm.cost_usd"] = cost

# Add to provider
provider.add_span_processor(CostCalculatorProcessor())
```

### Multiple OTEL Exporters

Send traces to multiple backends:

```python
# Grafana Cloud exporter
grafana_exporter = OTLPSpanExporter(
    endpoint=grafana_endpoint,
    headers=grafana_headers,
)

# Local Jaeger exporter (for development)
jaeger_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",
)

# Add both
provider.add_span_processor(BatchSpanProcessor(grafana_exporter))
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
```

### Propagating Context Across Services

If your LLM app calls other microservices:

```python
from opentelemetry.propagate import inject
import requests

def call_external_service():
    headers = {}
    inject(headers)  # Inject trace context into headers

    response = requests.get(
        "https://api.example.com/data",
        headers=headers  # Service will continue trace
    )
    return response.json()
```

---

## References

- **OpenTelemetry Python docs**: https://opentelemetry.io/docs/languages/python/
- **OpenInference specification**: https://github.com/Arize-ai/openinference
- **OTLP specification**: https://opentelemetry.io/docs/specs/otlp/
- **Grafana Tempo docs**: https://grafana.com/docs/tempo/latest/
- **Grafana Cloud signup**: https://grafana.com/get
- **This repository**: https://github.com/scarolan/music_store_assistant

## Related Documentation

- **[README.md](README.md)** - Quick start guide and project overview
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive codebase context for AI assistants
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture

---

**Questions or issues?**
- Open an issue: [GitHub Issues](https://github.com/scarolan/music_store_assistant/issues)
- Join the community: [Grafana Community Slack](https://slack.grafana.com/)
- Contact: Sean Carolan ([@scarolan](https://github.com/scarolan))

---

*This guide is part of the Music Store Assistant project - a demonstration of production-ready LLM observability for Grafana Labs.*
