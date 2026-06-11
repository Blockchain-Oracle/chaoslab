"""ASGI middleware: read A2A `params.message.contextId`, inject `session.id`.

Story 9.7 (phoenix-sessions, target side). The auditor wraps `drive_audit` in
`using_attributes(session_id=run_id, user_id=owner_uid)` so its own spans land
in the Phoenix Sessions tab under that run_id. The auditor sends the same
run_id as the A2A `contextId` on the JSON-RPC `message/send` envelope. This
middleware extracts that contextId from the incoming request body and enters
`using_attributes(session_id=<contextId>)` for the duration of the request —
so every span the target emits while handling that request joins the SAME
session in Phoenix.

Failure modes are CONTAINED: a malformed JSON body, missing field, or
non-string `contextId` MUST NOT error the request. The downstream A2A app must
still serve the call; we just skip the scope. A real request with a bad body
is already going to fail at the JSON-RPC parser — we don't pre-empt that.

Body buffering: ASGI's `receive` callable streams the body in chunks. We
fully buffer it, parse + extract, then replay it via a wrapping `receive` the
downstream sees. A2A JSON-RPC bodies are small (kB scale) so full buffering
is acceptable.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from openinference.instrumentation import using_attributes

_log = structlog.get_logger(__name__)


async def _read_body(receive: Any) -> tuple[bytes, list[dict[str, Any]]]:
    """Drain the request body from `receive`; return (full_bytes, recorded_messages).

    The recorded messages are the exact http.request envelopes the downstream
    app would have received — replayed via `_replay_receive` so the downstream
    sees identical bytes and `more_body` flags.
    """
    chunks: list[bytes] = []
    messages: list[dict[str, Any]] = []
    while True:
        message = await receive()
        messages.append(message)
        if message.get("type") != "http.request":
            # http.disconnect / lifespan etc. — stop draining; let the
            # downstream surface them via replay.
            break
        chunks.append(message.get("body", b"") or b"")
        if not message.get("more_body"):
            break
    return b"".join(chunks), messages


def _replay_receive(messages: list[dict[str, Any]], receive: Any) -> Any:
    """Wrap `receive` so the first replay yields buffered messages, then falls
    through to the real `receive` for anything that arrives after (rare in
    JSON-RPC but the contract is "ASGI receive is monotonic")."""
    iterator = iter(messages)

    async def wrapped() -> dict[str, Any]:
        try:
            return next(iterator)
        except StopIteration:
            return await receive()

    return wrapped


def _extract_context_id(body: bytes) -> str | None:
    """Parse the A2A JSON-RPC body and pull `params.message.contextId`.

    Returns None on ANY shape mismatch — JSON parse error, missing field,
    non-string value, empty string. Never raises.
    """
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    # Walk the chain via .get; any non-dict intermediate aborts to None.
    params = payload.get("params") if isinstance(payload, dict) else None
    message = params.get("message") if isinstance(params, dict) else None
    context_id = message.get("contextId") if isinstance(message, dict) else None
    if not isinstance(context_id, str) or not context_id:
        return None
    return context_id


class SessionAttributesMiddleware:
    """ASGI middleware that injects OpenInference `session.id` from A2A `contextId`.

    Mount this OUTSIDE `TraceContextMiddleware` so the OpenInference attributes
    are attached before any tracer instrumentation reads them — and so a
    body-buffer failure in this middleware never blocks W3C context extraction.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        try:
            body, messages = await _read_body(receive)
        except Exception:
            # Receive-side failure (rare): let the downstream see whatever
            # arrives next; we never swallow the request silently.
            _log.warning("session_attrs.receive_failed", exc_info=True)
            await self._app(scope, receive, send)
            return
        context_id = _extract_context_id(body)
        wrapped_receive = _replay_receive(messages, receive)
        if context_id is None:
            await self._app(scope, wrapped_receive, send)
            return
        with using_attributes(session_id=context_id):
            await self._app(scope, wrapped_receive, send)


__all__ = ["SessionAttributesMiddleware"]
