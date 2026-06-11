"""ASGI middleware: force-flush Phoenix BatchSpanProcessor at the end of each
HTTP request. Required on Cloud Run where CPU is throttled between requests —
without the explicit flush, spans queued in the batch processor sit in the
buffer and may never export. Diagnosed 2026-06-11 (IF-19, see audit-notes.md).

Sits OUTSIDE both SessionAttributesMiddleware and TraceContextMiddleware so
the flush happens AFTER every span end (otherwise the response-final spans
remain unflushed). The outermost-position invariant is locked in by
`tests/unit/test_server_assembly.py` so a future refactor that reorders
add_middleware calls fails the test instead of silently re-introducing IF-19.

Failure-mode discipline (PR #121 silent-failure review):

- A flush returning False is the SDK's documented "I did not finish flushing
  in time" signal — i.e. spans were dropped. IF-19's exact silent-loss
  shape if not surfaced. Logged at warning with `kind=queue_not_drained`.
- A flush raising a TRANSPORT error (timeout / OSError / ConnectionError) is
  treated as transient and breadcrumbed at warning level.
- A flush raising anything else (AttributeError from a wrong-shape provider,
  TypeError from arize-phoenix-otel kwarg drift, etc.) is a PROGRAMMER error
  and logged at error level with exc_info — these belong in the developer
  inbox, NOT pattern-matched as "transient Phoenix 5xx".
- A `DegradedTracerProvider` (no real exporter, from the
  `PHOENIX_OBSERVABILITY_OPTIONAL=1` graceful-degradation path) gets ONE
  boot-time warning so an operator running a misconfigured deploy doesn't
  conclude from quiet logs that observability is healthy.
"""

from __future__ import annotations

from typing import Any

import structlog

from target_agent.observability import DegradedTracerProvider

_log = structlog.get_logger(__name__)

# Generous: 2s lets a real OTLP burst clear; on Cloud Run a hung flush is
# already paying CPU-throttled latency, so a shorter timeout dropping
# unsent spans would be worse than the wait.
_FLUSH_TIMEOUT_MS = 2000

# Transport errors we treat as transient. Everything else is a programmer
# error and surfaces with exc_info at error level — per CLAUDE.md silent-
# failure pattern #4 (a fallback path that LOOKS like real success in
# operator dashboards is worse than no fallback at all).
_TRANSIENT_FLUSH_ERRORS = (TimeoutError, ConnectionError, OSError)


class ForceFlushMiddleware:
    def __init__(self, app: Any, tracer_provider: Any) -> None:
        self._app = app
        self._provider = tracer_provider
        # One-shot boot-time disclosure if we're flushing a no-op provider.
        # Without it, an operator who set PHOENIX_OBSERVABILITY_OPTIONAL=1
        # in a misconfigured env sees quiet logs and assumes observability
        # is fine — while the signed audit produces zero target evidence.
        if isinstance(tracer_provider, DegradedTracerProvider):
            _log.warning(
                "phoenix_force_flush_degraded_mode",
                provider_type=type(tracer_provider).__name__,
                note=(
                    "ForceFlushMiddleware will run on every request but flush "
                    "a no-op TracerProvider — no spans will ever land in "
                    "Phoenix. This is the PHOENIX_OBSERVABILITY_OPTIONAL=1 "
                    "graceful-degradation path; on Cloud Run it almost "
                    "certainly means a misconfigured deploy."
                ),
            )

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        try:
            await self._app(scope, receive, send)
        finally:
            self._flush(scope)

    def _flush(self, scope: dict[str, Any]) -> None:
        """Run force_flush with disciplined error surfacing.

        `scope` is used only for correlation-id breadcrumbs (path + method)
        so an operator chasing "11 of 13 traces have 0 target spans" can
        find which endpoints dropped them. Trace id would be richer but
        the current trace context is already detached by the time the
        finally-block runs (TraceContextMiddleware is INSIDE this one).
        """
        path = scope.get("path", "")
        method = scope.get("method", "")
        try:
            ok = self._provider.force_flush(timeout_millis=_FLUSH_TIMEOUT_MS)
        except _TRANSIENT_FLUSH_ERRORS as e:
            _log.warning(
                "phoenix_force_flush_failed",
                error_type=type(e).__name__,
                error=str(e)[:200],
                path=path,
                method=method,
                kind="transient",
            )
            return
        except Exception as e:
            # Programmer error path — exc_info=True so the traceback reaches
            # Cloud Logging instead of getting flattened to a one-liner.
            _log.error(
                "phoenix_force_flush_programmer_error",
                error_type=type(e).__name__,
                error=str(e)[:200],
                path=path,
                method=method,
                exc_info=True,
            )
            return
        if not ok:
            # `False` is the documented OTel signal for "queue not drained
            # within timeout" — i.e. spans were dropped. Earlier drafts
            # discarded the return value and would have silently re-
            # introduced IF-19 via a different door.
            _log.warning(
                "phoenix_force_flush_timeout",
                timeout_ms=_FLUSH_TIMEOUT_MS,
                path=path,
                method=method,
                kind="queue_not_drained",
            )


__all__ = ["ForceFlushMiddleware"]
