"""Unit tests for ForceFlushMiddleware (IF-19 fix).

The middleware MUST call tracer_provider.force_flush() after the inner app
finishes — for the audit-time invariant that target spans never sit
unflushed across Cloud Run's CPU-throttled response gap.
"""

from __future__ import annotations

from typing import Any

import pytest

from target_agent.force_flush_middleware import ForceFlushMiddleware


class _FakeProvider:
    def __init__(self, raise_on_flush: bool = False) -> None:
        self.flush_calls: list[int] = []
        self._raise = raise_on_flush

    def force_flush(self, timeout_millis: int = 0) -> bool:
        self.flush_calls.append(timeout_millis)
        if self._raise:
            msg = "simulated transient phoenix 5xx"
            raise RuntimeError(msg)
        return True


async def _http_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok":true}'})


async def _lifespan_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """Non-http scope — middleware MUST forward untouched, not flush."""
    return


@pytest.mark.asyncio
async def test_force_flush_called_after_http_response() -> None:
    provider = _FakeProvider()
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    sent: list[dict[str, Any]] = []

    async def _send(message: dict[str, Any]) -> None:
        sent.append(message)

    await mw({"type": "http"}, lambda: None, _send)

    assert len(sent) == 2, "inner app's response messages must pass through"
    assert sent[0]["status"] == 200
    assert provider.flush_calls == [2000], (
        f"force_flush(2000ms) must run exactly once per request; got {provider.flush_calls}"
    )


@pytest.mark.asyncio
async def test_flush_runs_even_if_inner_app_raises() -> None:
    """Must flush on the failure path too — otherwise an error response
    silently drops the spans that captured the failure."""
    provider = _FakeProvider()

    async def _failing_app(*_args: Any, **_kwargs: Any) -> None:
        msg = "inner app boom"
        raise ValueError(msg)

    mw = ForceFlushMiddleware(_failing_app, tracer_provider=provider)
    with pytest.raises(ValueError, match="inner app boom"):
        await mw({"type": "http"}, lambda: None, lambda m: None)
    assert provider.flush_calls == [2000], "even on a raising inner app the flush must still fire"


@pytest.mark.asyncio
async def test_flush_failure_does_not_corrupt_response() -> None:
    """A flush that itself raises must NOT escape — the response is already
    sent; raising here would only generate noisy ASGI 500 logs."""
    provider = _FakeProvider(raise_on_flush=True)
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    sent: list[dict[str, Any]] = []

    async def _send(message: dict[str, Any]) -> None:
        sent.append(message)

    # MUST NOT raise — successful response, swallowed flush error
    await mw({"type": "http"}, lambda: None, _send)
    assert sent[0]["status"] == 200
    assert provider.flush_calls == [2000]


@pytest.mark.asyncio
async def test_non_http_scope_skips_flush() -> None:
    """Lifespan / websocket scopes don't generate spans — flushing on
    them would burn budget on a no-op."""
    provider = _FakeProvider()
    mw = ForceFlushMiddleware(_lifespan_app, tracer_provider=provider)
    await mw({"type": "lifespan"}, lambda: None, lambda m: None)
    assert provider.flush_calls == [], "must not flush on non-http scope"
