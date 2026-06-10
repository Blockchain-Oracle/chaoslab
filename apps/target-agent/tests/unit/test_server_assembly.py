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


def test_mount_keeps_a2a_as_fallthrough(assembled: Starlette) -> None:
    mounts = [r for r in assembled.routes if isinstance(r, Mount)]
    assert mounts, "A2A app must be mounted for non-hook paths"
