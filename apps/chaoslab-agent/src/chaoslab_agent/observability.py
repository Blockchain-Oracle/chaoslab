"""Structured logging + Phoenix OTel registration for chaoslab-agent.

`setup_logging` configures structlog with a custom processor that injects the
active Phoenix `trace_id` + `span_id` into every log line, so every log message
can be cross-referenced with its originating Phoenix span.

`setup_phoenix_otel` calls `phoenix.otel.register(...)` then installs the
`GoogleADKInstrumentor`. MUST be called BEFORE any `google.adk.*` import path
executes (per coding-standards.md ADK-specific patterns + ADR-005).

Secret hygiene: structlog's processor chain includes `_mask_secrets`, which
replaces any `SecretStr` or kwarg whose key matches `(api_key|token|secret|
password)` with `"***"` before rendering. This defends against the developer
foot-gun of `log.info("phoenix_call", api_key=settings.phoenix_api_key.get_secret_value())`.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog
from opentelemetry import trace as _otel_trace
from pydantic import SecretStr

from chaoslab_agent.config import Settings

# Tracks whether setup_logging has already configured structlog this process;
# letting `setup_logging` no-op on second call is the documented idempotency
# requirement. A second call with a different `env` value is a programmer error
# and raises. Stored in a dict to avoid a `global` declaration.
_STATE: dict[str, Any] = {"logging_configured": False, "env": None}

# Substrings (case-insensitive) that mark a kwarg key as carrying secret material.
# Values bound to such keys are scrubbed before rendering.
_SECRET_KEY_MARKERS = ("api_key", "apikey", "token", "secret", "password", "authorization")


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


def _mask_secrets(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Mask any SecretStr value + any value bound to a secret-named key.

    Defends against the developer foot-gun of binding `get_secret_value()`
    output (a plain str) into a kwarg structlog will then render to JSON.
    """
    for key, value in list(event_dict.items()):
        if isinstance(value, SecretStr) or (
            isinstance(value, str) and any(m in key.lower() for m in _SECRET_KEY_MARKERS)
        ):
            event_dict[key] = "***"
    return event_dict


def setup_logging(env: str = "production") -> None:
    """Configure structlog. Idempotent — safe to call multiple times.

    `env="production"` emits JSON (Cloud Logging native); other values emit a
    colored console renderer for local dev. Log level is INFO+ in both modes.

    Calling a SECOND time with a different `env` value raises — that's a
    programmer error (structlog config is process-global; the second caller's
    expectations would be silently broken without a clear signal).
    """
    if _STATE["logging_configured"]:
        cached_env = _STATE.get("env")
        if cached_env != env:
            msg = (
                f"setup_logging already configured with env={cached_env!r}; "
                f"refusing to reconfigure with env={env!r}. "
                f"Call `structlog.reset_defaults()` first if reconfiguration is genuinely needed."
            )
            raise RuntimeError(msg)
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
            _mask_secrets,
            _add_phoenix_trace_id,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    _STATE["logging_configured"] = True
    _STATE["env"] = env


def setup_phoenix_otel(settings: Settings) -> None:
    """Register Phoenix as the OTel tracer provider + install GoogleADKInstrumentor.

    Per ADR-005 + coding-standards.md ADK-specific patterns: this MUST run BEFORE
    any `google.adk.*` import path executes. The instrumentor patches ADK methods
    at import time; calling it after ADK imports leaves un-instrumented call paths.

    Both imports are resolved BEFORE `register()` is called so an ImportError
    fails fast WITHOUT mutating the global OTel tracer state — otherwise a
    half-installed "Phoenix tracer registered, ADK NOT instrumented" state
    leaves trace-as-assertion gates failing open silently.
    """
    try:
        from phoenix.otel import register
    except ImportError as e:
        msg = (
            "phoenix.otel not installed — observability is mandatory per ADR-005. "
            "Install via `uv add arize-phoenix-otel` in apps/chaoslab-agent/."
        )
        raise ImportError(msg) from e
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    except ImportError as e:
        msg = (
            "openinference-instrumentation-google-adk not installed — ADK span "
            "instrumentation is mandatory per ADR-005. Install via "
            "`uv add openinference-instrumentation-google-adk`."
        )
        raise ImportError(msg) from e

    api_key = settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    register(
        project_name="chaoslab",
        endpoint=settings.phoenix_collector_endpoint,
        api_key=api_key,
    )
    GoogleADKInstrumentor().instrument()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Thin wrapper around `structlog.get_logger` — keeps the import path stable."""
    return structlog.get_logger(name) if name else structlog.get_logger()
