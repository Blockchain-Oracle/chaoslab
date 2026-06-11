"""ASGI middleware: force-flush Phoenix BatchSpanProcessor at the end of each
HTTP request. Required on Cloud Run where CPU is throttled between requests —
without the explicit flush, spans queued in the batch processor sit in the
buffer and may never export. Diagnosed 2026-06-11 (IF-19, see audit-notes.md).

Sits OUTSIDE both SessionAttributesMiddleware and TraceContextMiddleware so
the flush happens AFTER every span end (otherwise the response-final spans
remain unflushed).

Failure-mode: a flush that itself raises (e.g. Phoenix Cloud transient 5xx)
MUST NOT corrupt the response — the response has already been sent by the
inner app. Swallow and breadcrumb so the next request retries the flush.
"""

from __future__ import annotations

from typing import Any

import structlog

_log = structlog.get_logger(__name__)

# Generous: 2s lets a real OTLP burst clear; on Cloud Run a hung flush is
# already paying CPU-throttled latency, so a shorter timeout dropping
# unsent spans would be worse than the wait.
_FLUSH_TIMEOUT_MS = 2000


class ForceFlushMiddleware:
    def __init__(self, app: Any, tracer_provider: Any) -> None:
        self._app = app
        self._provider = tracer_provider

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        try:
            await self._app(scope, receive, send)
        finally:
            try:
                self._provider.force_flush(timeout_millis=_FLUSH_TIMEOUT_MS)
            except Exception as e:
                # Defensive: a swallowed flush failure becomes a missing-span
                # mystery in the audit later. Breadcrumb the type so
                # operators can correlate with the eventual silent loss.
                _log.warning(
                    "phoenix_force_flush_failed",
                    error_type=type(e).__name__,
                    error=str(e)[:200],
                )


__all__ = ["ForceFlushMiddleware"]
