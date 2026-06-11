"""Unit tests for ForceFlushMiddleware (IF-19 fix).

The middleware MUST call tracer_provider.force_flush() after the inner app
finishes — for the audit-time invariant that target spans never sit
unflushed across Cloud Run's CPU-throttled response gap. Per PR #121
review-fleet findings the tests also lock in:

  - the timeout has a sane LOWER bound (assertion not coupled to the
    literal constant — see Test #3 finding);
  - `force_flush` returning False (timeout) breadcrumbs (Test #4 finding);
  - programmer-class exceptions surface at ERROR with exc_info, NOT
    swallowed as "transient" (F2 finding);
  - DegradedTracerProvider gets one boot-time disclosure (F1 finding).
"""

from __future__ import annotations

from typing import Any

import pytest

import target_agent.force_flush_middleware as ffm_module
from target_agent.force_flush_middleware import ForceFlushMiddleware
from target_agent.observability import DegradedTracerProvider


class _FakeProvider:
    """Records every force_flush call with its timeout, configurable
    return value and raise behavior. Used to assert the middleware's
    behavioral contract — not its log strings."""

    def __init__(
        self,
        *,
        returns: bool = True,
        raises: BaseException | None = None,
    ) -> None:
        self.flush_calls: list[int] = []
        self._returns = returns
        self._raises = raises

    def force_flush(self, timeout_millis: int = 0) -> bool:
        self.flush_calls.append(timeout_millis)
        if self._raises is not None:
            raise self._raises
        return self._returns


async def _noop_receive() -> dict[str, Any]:
    return {"type": "http.disconnect"}


async def _noop_send(_message: dict[str, Any]) -> None:
    return None


async def _http_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok":true}'})


async def _lifespan_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """Non-http scope — middleware MUST forward untouched, not flush."""
    return


class _RecordingLogger:
    """Stand-in for the module's structlog logger that records every
    call so tests can assert on event names + kwargs without depending
    on a structlog config."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def warning(self, event: str, **kw: Any) -> None:
        self.records.append({"event": event, "_level": "warning", **kw})

    def error(self, event: str, **kw: Any) -> None:
        self.records.append({"event": event, "_level": "error", **kw})


@pytest.fixture
def recording_log(monkeypatch: pytest.MonkeyPatch) -> _RecordingLogger:
    """Swap the module's logger for the test. Returns the recorder so
    tests can grep `recording_log.records` by event name."""
    rec = _RecordingLogger()
    monkeypatch.setattr(ffm_module, "_log", rec)
    return rec


@pytest.mark.asyncio
async def test_force_flush_called_after_http_response() -> None:
    provider = _FakeProvider()
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    sent: list[dict[str, Any]] = []

    async def _send(message: dict[str, Any]) -> None:
        sent.append(message)

    await mw({"type": "http"}, _noop_receive, _send)

    assert len(sent) == 2, "inner app's response messages must pass through"
    assert sent[0]["status"] == 200
    # Test #3 finding: assert "exactly once with non-trivial timeout",
    # not the literal constant — keeps the test honest if the constant
    # gets tuned without invalidating the contract.
    assert len(provider.flush_calls) == 1
    assert provider.flush_calls[0] >= 1000, (
        f"flush timeout must be ≥1s; got {provider.flush_calls[0]}ms"
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
        await mw({"type": "http"}, _noop_receive, _noop_send)
    assert len(provider.flush_calls) == 1


@pytest.mark.asyncio
async def test_transient_flush_failure_does_not_corrupt_response(
    recording_log: _RecordingLogger,
) -> None:
    """A TimeoutError / ConnectionError / OSError from the exporter is
    transient — swallow, breadcrumb at warning, do not raise."""
    provider = _FakeProvider(raises=TimeoutError("phoenix slow"))
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    await mw(
        {"type": "http", "path": "/", "method": "POST"},
        _noop_receive,
        _noop_send,
    )

    assert len(provider.flush_calls) == 1
    events = [r["event"] for r in recording_log.records]
    assert "phoenix_force_flush_failed" in events, (
        "transient flush failure must breadcrumb at warning; got events: " + str(events)
    )


@pytest.mark.asyncio
async def test_programmer_error_in_flush_surfaces_at_error_level(
    recording_log: _RecordingLogger,
) -> None:
    """PR #121 F2: an AttributeError / TypeError from a wrong-shape
    provider is a PROGRAMMER bug — must NOT look like a transient Phoenix
    5xx in operator dashboards. Logged at error with exc_info, not
    swallowed at warning."""
    provider = _FakeProvider(raises=AttributeError("force_flush misspelled"))
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    # MUST NOT raise — response was already sent
    await mw(
        {"type": "http", "path": "/x", "method": "POST"},
        _noop_receive,
        _noop_send,
    )
    events = [r["event"] for r in recording_log.records]
    assert "phoenix_force_flush_programmer_error" in events, (
        f"AttributeError must surface as PROGRAMMER error event; got: {events}"
    )
    assert "phoenix_force_flush_failed" not in events, (
        "programmer error must NOT be logged as 'transient' — that misleads operators"
    )
    # The error log must include the error_type discriminator so a grep
    # in Cloud Logging tells "Phoenix 5xx" from "we shipped broken code".
    matched = next(
        r for r in recording_log.records if r["event"] == "phoenix_force_flush_programmer_error"
    )
    assert matched.get("error_type") == "AttributeError"
    assert matched.get("_level") == "error"


@pytest.mark.asyncio
async def test_flush_returning_false_breadcrumbs_as_dropped_spans(
    recording_log: _RecordingLogger,
) -> None:
    """PR #121 Test #4: force_flush returning False is the SDK's
    documented "queue not drained" signal — i.e. spans were dropped.
    Earlier drafts discarded this and would have silently re-introduced
    IF-19 via a different door."""
    provider = _FakeProvider(returns=False)
    mw = ForceFlushMiddleware(_http_app, tracer_provider=provider)
    await mw(
        {"type": "http", "path": "/p", "method": "POST"},
        _noop_receive,
        _noop_send,
    )

    events = [r["event"] for r in recording_log.records]
    assert "phoenix_force_flush_timeout" in events, (
        f"force_flush()=False must surface as a timeout breadcrumb; got: {events}"
    )
    matched = next(r for r in recording_log.records if r["event"] == "phoenix_force_flush_timeout")
    assert matched.get("kind") == "queue_not_drained"


@pytest.mark.asyncio
async def test_non_http_scope_skips_flush() -> None:
    """Lifespan / websocket scopes don't generate spans — flushing on
    them would burn budget on a no-op."""
    provider = _FakeProvider()
    mw = ForceFlushMiddleware(_lifespan_app, tracer_provider=provider)
    await mw({"type": "lifespan"}, _noop_receive, _noop_send)
    assert provider.flush_calls == [], "must not flush on non-http scope"


def test_degraded_provider_logs_one_boot_time_breadcrumb(
    recording_log: _RecordingLogger,
) -> None:
    """PR #121 F1: a DegradedTracerProvider (no real exporter) must
    surface at boot — otherwise PHOENIX_OBSERVABILITY_OPTIONAL=1 in a
    misconfigured deploy looks identical to a healthy run in operator
    dashboards (quiet logs, signed report with zero target evidence)."""
    from opentelemetry.sdk.trace import TracerProvider

    degraded = DegradedTracerProvider(TracerProvider())
    ForceFlushMiddleware(_http_app, tracer_provider=degraded)

    events = [r["event"] for r in recording_log.records]
    assert "phoenix_force_flush_degraded_mode" in events, (
        f"DegradedTracerProvider must trigger boot-time disclosure; got: {events}"
    )
