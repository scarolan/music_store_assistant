"""OpenTelemetry configuration for exporting traces to Grafana Cloud.

This module configures OTEL tracing using OpenInference instrumentation to capture
LLM interactions (prompts, completions, token counts) and export them to Grafana Cloud.

OpenInference captures rich LLM data, but we filter it down to essential attributes
to stay within reasonable limits while preserving the most useful information:
- User messages and AI responses (truncated)
- Token counts and model info
- Tool calls and results
- Session/trace context

Environment Variables Required:
- OTEL_EXPORTER_OTLP_ENDPOINT: Grafana Cloud OTLP endpoint
- OTEL_EXPORTER_OTLP_HEADERS: Authorization header (URL-encoded)

Optional:
- OTEL_SERVICE_NAME: Service name for traces (default: music-store-assistant)
"""

import os
import logging
from urllib.parse import unquote
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.util.types import AttributeValue

# OpenInference instrumentation for full trace hierarchy
from openinference.instrumentation.langchain import LangChainInstrumentor

logger = logging.getLogger(__name__)

# Maximum length for string attributes (user messages, AI responses)
MAX_ATTR_LENGTH = 500

# Maximum number of conversation messages to keep (excludes system prompt at index 0)
# Keep system prompt (index 0) + last MAX_MESSAGES messages
MAX_MESSAGES = 10

# Attributes to DROP entirely (bloated/redundant)
DROP_ATTRIBUTES = {
    "input.value",  # Huge JSON blob, redundant with llm.input_messages
    "output.value",  # Huge JSON blob, redundant with llm.output_messages  
    "input.mime_type",
    "output.mime_type",
    "llm.invocation_parameters",  # Full tool schemas, very long
    "metadata",  # LangGraph internals, mostly noise
}

# Attribute prefixes to DROP (tool schemas repeated on every call)
DROP_PREFIXES = (
    "llm.tools.",  # Tool JSON schemas - huge and repeated
)

# Attributes to KEEP but TRUNCATE
TRUNCATE_ATTRIBUTES = {
    "llm.input_messages.0.message.content",  # System prompt - truncate heavily
}

# Attributes to KEEP as-is (high value, reasonable size)
KEEP_ATTRIBUTES = {
    # Token counts - critical for cost tracking
    "llm.token_count.prompt",
    "llm.token_count.completion",
    "llm.token_count.total",
    # Model info
    "llm.model_name",
    "llm.provider",
    "llm.system",
    # Trace context
    "session.id",
    "openinference.span.kind",
    # Tool info
    "tool.name",
}

# Prefixes to keep (user/assistant messages, but we'll truncate content)
KEEP_PREFIXES = (
    "llm.input_messages.",
    "llm.output_messages.",
    "tool.",
)


def _truncate(value: str, max_length: int = MAX_ATTR_LENGTH) -> str:
    """Truncate string to max_length with ellipsis."""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


class AttributeFilterProcessor(SpanProcessor):
    """SpanProcessor that filters and truncates attributes on span end.
    
    This runs BEFORE export to remove bloated attributes and truncate
    long strings, keeping traces lean while preserving essential data.
    """
    
    def on_start(self, span: Span, parent_context: object = None) -> None:
        """Called when span starts - nothing to do here."""
        pass
    
    def on_end(self, span: ReadableSpan) -> None:
        """Called when span ends - filter attributes before export."""
        # ReadableSpan._attributes is a BoundedAttributes dict we can modify
        if not hasattr(span, "_attributes") or span._attributes is None:
            return
        
        attrs: Any = span._attributes
        keys_to_remove = []
        keys_to_update: dict[str, AttributeValue] = {}
        
        # First pass: find the highest message index to determine if we need to limit
        max_msg_index = -1
        for key in attrs.keys():
            if key.startswith("llm.input_messages."):
                # Extract index from "llm.input_messages.N.message.xxx"
                try:
                    parts = key.split(".")
                    if len(parts) >= 3:
                        idx = int(parts[2])
                        max_msg_index = max(max_msg_index, idx)
                except (ValueError, IndexError):
                    pass
        
        # Calculate which message indices to keep:
        # Always keep index 0 (system prompt) + last MAX_MESSAGES
        keep_indices: set[int] = {0}  # Always keep system prompt
        if max_msg_index > 0:
            # If we have more than MAX_MESSAGES, keep only the last ones + system prompt
            if max_msg_index >= MAX_MESSAGES:
                # Keep system prompt (0) + last MAX_MESSAGES messages
                start_idx = max_msg_index - MAX_MESSAGES + 1
                keep_indices.update(range(start_idx, max_msg_index + 1))
            else:
                # Keep all messages if under limit
                keep_indices.update(range(0, max_msg_index + 1))
        
        for key, value in attrs.items():
            # Check if we should DROP this attribute entirely
            if key in DROP_ATTRIBUTES:
                keys_to_remove.append(key)
                continue
            
            # Check if prefix matches DROP list
            if any(key.startswith(prefix) for prefix in DROP_PREFIXES):
                keys_to_remove.append(key)
                continue
            
            # Check if this is a message we should drop due to limit
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
            
            # Check if this is a KEEP attribute (no modification)
            if key in KEEP_ATTRIBUTES:
                continue
            
            # Check if prefix matches KEEP list - truncate string values
            if any(key.startswith(prefix) for prefix in KEEP_PREFIXES):
                if isinstance(value, str):
                    # System prompts get extra truncation (less useful in traces)
                    if "message.content" in key and ".0." in key:
                        # First message is usually system prompt - truncate more
                        keys_to_update[key] = _truncate(value, 200)
                    else:
                        keys_to_update[key] = _truncate(value, MAX_ATTR_LENGTH)
                continue
            
            # For any other string attribute, truncate it
            if isinstance(value, str) and len(value) > MAX_ATTR_LENGTH:
                keys_to_update[key] = _truncate(value, MAX_ATTR_LENGTH)
        
        # Apply removals
        for key in keys_to_remove:
            try:
                del attrs[key]
            except (KeyError, TypeError):
                pass
        
        # Apply updates
        for key, value in keys_to_update.items():
            try:
                attrs[key] = value
            except TypeError:
                pass
    
    def shutdown(self) -> None:
        """Shutdown the processor."""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush - nothing to flush in this processor."""
        return True


def configure_otel_tracing() -> bool:
    """Configure OpenTelemetry tracing with OpenInference for Grafana Cloud export.
    
    Uses OpenInference instrumentation which properly captures LLM prompts,
    completions, and token usage. Applies attribute filtering to keep traces
    lean while preserving essential debugging information.
    
    Returns:
        True if OTEL tracing was configured, False if skipped (missing config).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers_raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    
    if not endpoint or not headers_raw:
        logger.info(
            "OTEL tracing not configured - missing OTEL_EXPORTER_OTLP_ENDPOINT "
            "or OTEL_EXPORTER_OTLP_HEADERS"
        )
        return False
    
    # Parse headers (format: "key1=value1,key2=value2" or URL-encoded)
    headers: dict[str, str] = {}
    for part in headers_raw.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            # URL-decode the value in case it's encoded (common for auth tokens)
            headers[unquote(key)] = unquote(value)
    
    # Service name for Grafana
    service_name = os.getenv("OTEL_SERVICE_NAME", "music-store-assistant")
    
    # Create resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})
    
    # Create the OTLP exporter pointing to Grafana Cloud
    # Append /v1/traces if not already present
    traces_endpoint = endpoint
    if not traces_endpoint.endswith("/v1/traces"):
        traces_endpoint = f"{traces_endpoint.rstrip('/')}/v1/traces"
    
    exporter = OTLPSpanExporter(
        endpoint=traces_endpoint,
        headers=headers,
    )
    
    # Create TracerProvider
    provider = TracerProvider(resource=resource)
    
    # Add our attribute filter processor FIRST (runs on_end before export)
    provider.add_span_processor(AttributeFilterProcessor())
    
    # Add the batch processor for actual export
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    # Set as global tracer provider - this must happen BEFORE LangChain imports
    trace.set_tracer_provider(provider)
    
    # Instrument LangChain - this creates spans for chains, agents, tools, and LLM calls
    # with full message content, token usage, and trace hierarchy
    LangChainInstrumentor().instrument(tracer_provider=provider)
    
    logger.info(
        f"✅ OTEL tracing configured with OpenInference for Grafana Cloud: {endpoint} "
        f"(service: {service_name}, attribute filtering enabled)"
    )
    return True


def shutdown_otel_tracing() -> None:
    """Flush and shutdown the OTEL tracer provider.
    
    Call this on application shutdown to ensure all spans are exported.
    """
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
        logger.info("OTEL tracing shutdown complete")
