"""S-EC3: W3C trace-context propagation into the target's spans.

The auditor's adapter span must be the ancestor of every span this target
emits for that request — that shared 32-hex trace_id is how the Judge fetches
the target's evidence from Phoenix. Without extraction, target spans start a
fresh trace and the audit's evidence chain breaks.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from target_agent.trace_context import TraceContextMiddleware

_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
_PARENT_SPAN = "00f067aa0ba902b7"
_TRACEPARENT = f"00-{_TRACE_ID}-{_PARENT_SPAN}-01"


def _build_app() -> Starlette:
    async def handler(request: Any) -> JSONResponse:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("inside-target") as span:
            ctx = span.get_span_context()
            return JSONResponse({"trace_id": format(ctx.trace_id, "032x")})

    app = Starlette(routes=[Route("/", handler, methods=["GET"])])
    app.add_middleware(TraceContextMiddleware)
    return app


def test_traceparent_header_joins_the_callers_trace(in_memory_spans: Any) -> None:
    client = TestClient(_build_app())
    resp = client.get("/", headers={"traceparent": _TRACEPARENT})
    assert resp.json()["trace_id"] == _TRACE_ID
    finished = in_memory_spans.get_finished_spans()
    assert finished, "expected the downstream span to be exported"
    assert format(finished[0].get_span_context().trace_id, "032x") == _TRACE_ID


def test_without_traceparent_a_fresh_trace_starts(in_memory_spans: Any) -> None:
    client = TestClient(_build_app())
    resp = client.get("/")
    assert resp.json()["trace_id"] != _TRACE_ID


def test_malformed_traceparent_does_not_crash_the_request() -> None:
    client = TestClient(_build_app())
    resp = client.get("/", headers={"traceparent": "garbage"})
    assert resp.status_code == 200
