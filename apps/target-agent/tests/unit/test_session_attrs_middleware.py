"""Story 9.7 (phoenix-sessions) — target-side ASGI middleware that extracts the
A2A `params.message.contextId` and enters `using_attributes(session_id=...)`
for the duration of the request.

Trace-as-assertion: the handler inside the test app reads OpenInference's real
`get_attributes_from_context()` — we never mock `using_attributes`. The
middleware is exercised through a real Starlette `TestClient` posting a real
A2A-shaped JSON-RPC body. Failure to parse / extract MUST NOT error the
request; it just leaves the scope unentered.
"""

from __future__ import annotations

from typing import Any

from openinference.instrumentation import get_attributes_from_context
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _build_app() -> Starlette:
    """Echo handler returns whatever OpenInference attributes are on the contextvar."""
    from target_agent.session_attrs import SessionAttributesMiddleware

    async def handler(_request: Any) -> JSONResponse:
        return JSONResponse(dict(get_attributes_from_context()))

    app = Starlette(routes=[Route("/", handler, methods=["POST", "GET"])])
    app.add_middleware(SessionAttributesMiddleware)
    return app


def _a2a_body(context_id: str | None) -> dict[str, Any]:
    """Minimal A2A `message/send` JSON-RPC body — only the shape the middleware reads."""
    msg: dict[str, Any] = {"role": "user", "parts": [{"text": "hello"}]}
    if context_id is not None:
        msg["contextId"] = context_id
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {"message": msg},
    }


def test_middleware_injects_session_id_from_context_id() -> None:
    """A valid A2A POST with `params.message.contextId` enters the scope."""
    client = TestClient(_build_app())
    resp = client.post("/", json=_a2a_body("run_session99ab"))
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("session.id") == "run_session99ab"


def test_middleware_no_scope_when_context_id_missing() -> None:
    """No `contextId` => no scope entered; request still served cleanly."""
    client = TestClient(_build_app())
    resp = client.post("/", json=_a2a_body(None))
    assert resp.status_code == 200
    body = resp.json()
    assert "session.id" not in body


def test_middleware_no_scope_when_context_id_empty_string() -> None:
    """Empty string is treated as "no contextId" — OpenInference's empty-string
    default is a no-op, but we surface this explicitly so the contract is
    clear at the middleware boundary (not buried in OpenInference)."""
    client = TestClient(_build_app())
    resp = client.post("/", json=_a2a_body(""))
    assert resp.status_code == 200
    body = resp.json()
    assert "session.id" not in body


def test_middleware_tolerates_non_json_body() -> None:
    """Garbage body MUST NOT error the request — we just skip the scope."""
    client = TestClient(_build_app())
    resp = client.post(
        "/", content=b"not-json-at-all", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "session.id" not in body


def test_middleware_tolerates_non_string_context_id() -> None:
    """A numeric `contextId` MUST NOT crash — skip the scope, serve the request."""
    bad = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {"message": {"role": "user", "contextId": 12345}},
    }
    client = TestClient(_build_app())
    resp = client.post("/", json=bad)
    assert resp.status_code == 200
    body = resp.json()
    assert "session.id" not in body


def test_middleware_passes_through_non_http_scopes() -> None:
    """ASGI middleware sees lifespan/websocket scopes — must forward unchanged."""
    from starlette.applications import Starlette

    from target_agent.session_attrs import SessionAttributesMiddleware

    app = Starlette()
    app.add_middleware(SessionAttributesMiddleware)
    # Lifespan startup/shutdown — TestClient runs lifespan on enter/exit.
    with TestClient(app):
        pass  # if middleware crashed on the lifespan scope, this would raise


def test_middleware_body_is_replayed_downstream_byte_for_byte() -> None:
    """The middleware buffers + replays the body. Downstream must see the EXACT
    bytes that were sent — not just JSON-equivalent. A `json.loads(raw) == sent`
    check passes even if the middleware silently re-canonicalizes whitespace,
    reorders keys, normalizes Unicode, or drops a `more_body` chunk that
    downstream JSON-decodes equivalently. Byte-level hash is the real test."""
    import hashlib

    from target_agent.session_attrs import SessionAttributesMiddleware

    async def hash_body(request: Any) -> JSONResponse:
        raw = await request.body()
        return JSONResponse({"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})

    app = Starlette(routes=[Route("/", hash_body, methods=["POST"])])
    app.add_middleware(SessionAttributesMiddleware)

    # Raw bytes — control whitespace + key order ourselves so the assertion is
    # exact. A JSON-equivalent canonicalization in the middleware would change
    # the hash.
    raw_sent = (
        b'{"jsonrpc": "2.0",  "id":"1","method":"message/send",'
        b'"params":{"message":{"role":"user","contextId":"run_replay99abc"}}}'
    )
    expected_hash = hashlib.sha256(raw_sent).hexdigest()
    resp = TestClient(app).post("/", content=raw_sent, headers={"content-type": "application/json"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["bytes"] == len(raw_sent)
    assert body["sha256"] == expected_hash
