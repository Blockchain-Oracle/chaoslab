"""S-EC4: server assembly — hook routes + trace middleware wrap the A2A app.

The A2A endpoints must keep their root paths (agent-card discovery breaks
otherwise) while /hooks/adk and trace-context extraction sit in front.
"""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route


@pytest.fixture
def assembled(monkeypatch: pytest.MonkeyPatch) -> Starlette:
    from target_agent import server

    async def fake_card(request: Any) -> PlainTextResponse:
        return PlainTextResponse("card")

    fake_a2a = Starlette(routes=[Route("/.well-known/agent-card.json", fake_card, methods=["GET"])])
    monkeypatch.setattr(server, "_build_a2a_app", lambda: fake_a2a)
    return server._assemble_app()  # ty: ignore[invalid-return-type]


def test_a2a_paths_still_served_at_root(assembled: Starlette) -> None:
    from starlette.testclient import TestClient

    resp = TestClient(assembled).get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    assert resp.text == "card"


def test_hook_routes_present_and_gated(assembled: Starlette) -> None:
    from starlette.testclient import TestClient

    # FAULT_HOOKS_ENABLED unset -> gated 404, but the route itself must exist
    # (a missing route would ALSO 404 — distinguish via the JSON detail body).
    resp = TestClient(assembled).post("/hooks/adk", json={"fault_config": {}})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "fault hooks disabled"


def test_trace_middleware_installed(assembled: Starlette) -> None:
    from target_agent.trace_context import TraceContextMiddleware

    assert any(m.cls is TraceContextMiddleware for m in assembled.user_middleware)


def test_force_flush_middleware_is_outermost(assembled: Starlette) -> None:
    """IF-19 invariant: ForceFlushMiddleware MUST be the outermost ASGI
    layer so its finally-block runs AFTER every inner span has ended.
    Starlette stores user_middleware in OUTERMOST-first order (the last
    `add_middleware()` call becomes index 0). A future refactor that
    reorders the three middlewares would silently re-introduce IF-19
    (target spans queued by BatchSpanProcessor sit unflushed across
    Cloud Run's response-flush CPU throttle); this test fails fast
    instead.
    """
    from target_agent.force_flush_middleware import ForceFlushMiddleware
    from target_agent.session_attrs import SessionAttributesMiddleware
    from target_agent.trace_context import TraceContextMiddleware

    classes = [m.cls for m in assembled.user_middleware]
    # All three must be present
    assert ForceFlushMiddleware in classes, "ForceFlushMiddleware missing — see IF-19"
    assert SessionAttributesMiddleware in classes
    assert TraceContextMiddleware in classes
    # Outermost-first: ForceFlush > SessionAttrs > TraceContext
    assert classes.index(ForceFlushMiddleware) < classes.index(SessionAttributesMiddleware), (
        f"ForceFlushMiddleware must be OUTSIDE SessionAttributesMiddleware; got {classes}"
    )
    assert classes.index(SessionAttributesMiddleware) < classes.index(TraceContextMiddleware), (
        f"SessionAttributesMiddleware must be OUTSIDE TraceContextMiddleware; got {classes}"
    )


def test_mount_keeps_a2a_as_fallthrough(assembled: Starlette) -> None:
    mounts = [r for r in assembled.routes if isinstance(r, Mount)]
    assert mounts, "A2A app must be mounted for non-hook paths"


def test_inner_lifespan_runs_so_lifespan_registered_routes_serve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """google-adk's to_a2a() registers ALL A2A routes (incl. the agent card)
    inside the inner app's LIFESPAN — and Starlette never runs a mounted
    sub-app's lifespan. Without explicit delegation every A2A path 404s in
    the container (staging smoke failure 2026-06-10)."""
    from contextlib import asynccontextmanager
    from typing import Any as AnyT

    from starlette.testclient import TestClient

    from target_agent import server

    async def card(request: AnyT) -> PlainTextResponse:
        return PlainTextResponse("card")

    @asynccontextmanager
    async def inner_lifespan(app: Starlette) -> Any:
        app.router.routes.append(Route("/.well-known/agent-card.json", card, methods=["GET"]))
        yield

    fake_a2a = Starlette(lifespan=inner_lifespan)
    monkeypatch.setattr(server, "_build_a2a_app", lambda: fake_a2a)
    assembled = server._assemble_app()
    # Context-managed client = lifespan actually runs, like uvicorn does.
    with TestClient(assembled) as client:  # ty: ignore[invalid-argument-type]
        resp = client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    assert resp.text == "card"
