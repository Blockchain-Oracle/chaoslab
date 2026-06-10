"""W3C trace-context extraction middleware (pure ASGI, no extra dependency).

`to_a2a()`'s Starlette app is not server-instrumented, so an incoming
`traceparent` header is normally ignored and the target's ADK spans start a
FRESH trace. Phoenix Audit's evidence chain requires the opposite: the
auditor's adapter span and this process's spans must share one trace_id so
the Judge can fetch the target's spans from Phoenix by that id.

This middleware extracts the W3C context and attaches it for the duration of
the request; every span started downstream (GoogleADKInstrumentor's included)
becomes a child of the caller's span. Malformed headers extract to an empty
context — the request proceeds on a fresh trace, never errors.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import context as otel_context
from opentelemetry.propagate import extract


def _headers_dict(scope: dict[str, Any]) -> dict[str, str]:
    return {
        name.decode("latin-1").lower(): value.decode("latin-1")
        for name, value in scope.get("headers") or []
    }


class TraceContextMiddleware:
    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        token = otel_context.attach(extract(_headers_dict(scope)))
        try:
            await self._app(scope, receive, send)
        finally:
            otel_context.detach(token)


__all__ = ["TraceContextMiddleware"]
