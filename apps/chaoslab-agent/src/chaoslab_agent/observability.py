"""Structured logging + Phoenix OTel registration for chaoslab-agent.

`setup_logging` configures structlog with a custom processor that injects the
active Phoenix `trace_id` + `span_id` into every log line — that's the recursive
observability story (any log message links to its originating span).

`setup_phoenix_otel` calls `phoenix.otel.register(...)` then installs the
`GoogleADKInstrumentor` so every ADK event surfaces as a span. MUST be called
BEFORE any `google.adk.*` import path executes (per coding-standards.md
ADK-specific patterns + ADR-005).
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog
from opentelemetry import trace as _otel_trace

from chaoslab_agent.config import Settings

# Tracks whether setup_logging has already configured structlog this process;
# letting `setup_logging` no-op on second call is the documented idempotency
# requirement. Stored in a dict so we don't need a `global` declaration (PLW0603).
_STATE: dict[str, bool] = {"logging_configured": False}


def _add_phoenix_trace_id(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Inject Phoenix trace_id + span_id into the log event when a span is active.

    Skips silently when no span is recording (the OTel default `INVALID_SPAN`
    has trace_id=0). This keeps log lines emitted outside an instrumented path
    free of meaningless zeroed-out ids.
    """
    span = _otel_trace.get_current_span()
    ctx = span.get_span_context() if span is not None else None
    if ctx is not None and ctx.is_valid and span.is_recording():
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def setup_logging(env: str = "production") -> None:
    """Configure structlog. Idempotent — safe to call multiple times.

    `env="production"` emits JSON (Cloud Logging native); other values emit a
    colored console renderer for local dev. Log level is INFO+ in both modes.
    """
    if _STATE["logging_configured"]:
        return
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if env == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_phoenix_trace_id,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    _STATE["logging_configured"] = True


def setup_phoenix_otel(settings: Settings) -> None:
    """Register Phoenix as the OTel tracer provider + install GoogleADKInstrumentor.

    Per ADR-005 + coding-standards.md ADK-specific patterns: this MUST run BEFORE
    any `google.adk.*` import executes. The instrumentor patches ADK methods at
    import time; calling it after ADK imports leaves un-instrumented call paths.

    Failures bubble up — silent observability loss on a compliance product is
    unacceptable (matches the `_lifespan` policy from S4.1).
    """
    # Local import: phoenix.otel pulls in heavy dependencies; importing at module
    # top would slow every test that doesn't need observability.
    from phoenix.otel import register

    api_key = settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    register(
        project_name="chaoslab",
        endpoint=settings.phoenix_collector_endpoint,
        api_key=api_key,
    )
    # The instrumentor monkey-patches ADK internals; importing here (vs. module
    # top) lets observability.py be safely imported BEFORE the ADK quarantine.
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    GoogleADKInstrumentor().instrument()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Thin wrapper around `structlog.get_logger` — keeps the import path stable."""
    return structlog.get_logger(name) if name else structlog.get_logger()
