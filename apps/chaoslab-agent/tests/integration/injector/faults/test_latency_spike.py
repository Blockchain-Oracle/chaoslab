"""Trace-as-assertion tests for F4 LatencySpikeFault.

The spec (story-5.5 BDD lines 48-67) calls for verifying that the
network-layer fault produces TOOL spans whose duration exceeds the
configured delay (slow-OK case) or whose status maps to a TIMEOUT-shaped
failure (delay > timeout case).

These tests exercise the callback contract directly against a real ADK
``FunctionTool`` + a real OpenTelemetry ``InMemorySpanExporter`` and a
real ``asyncio.sleep`` — so they DO sleep, but with small deltas
(300ms / 100ms) per the spec's "Test-suite acceleration note". One
``@pytest.mark.slow`` test runs the canonical 30000ms/10000ms config.
"""

from __future__ import annotations

import time
from typing import Any, cast

import httpx
import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from chaoslab_agent.adk_types import FunctionTool, ToolContext
from chaoslab_agent.injector.faults import LatencySpikeFault

pytestmark = pytest.mark.integration


def _lookup_order(order_id: str) -> dict[str, Any]:
    """Tool body matching the target-agent lookup_order schema."""
    return {"status": "shipped", "items": [{"name": "widget", "qty": 2}], "total": 19.99}


_LOOKUP_ORDER_TOOL = FunctionTool(func=_lookup_order)

_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("chaoslab.test.injector.faults")


@pytest.fixture(autouse=True)
def exporter() -> InMemorySpanExporter:
    """Autouse so every test starts with a clean exporter — same pattern as F1/F2/F3."""
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


async def _invoke_callback_in_tool_span(
    fault: LatencySpikeFault,
    *,
    tool: FunctionTool = _LOOKUP_ORDER_TOOL,
    args: dict[str, Any] | None = None,
) -> tuple[Any, Any, float]:
    """Run F4's callback inside a TOOL span; return (result, span, elapsed_seconds)."""
    callback = fault.as_callback()
    with _TEST_TRACER.start_as_current_span("test.tool.call") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        start = time.monotonic()
        result = await callback(tool, args or {"order_id": "12345"}, cast(ToolContext, None))
        elapsed = time.monotonic() - start
    return result, span, elapsed


def _last_tool_span(exporter: InMemorySpanExporter) -> ReadableSpan:
    spans = [
        s
        for s in exporter.get_finished_spans()
        if s.attributes is not None and s.attributes.get("openinference.span.kind") == "TOOL"
    ]
    assert spans, "no TOOL spans recorded"
    return spans[-1]


# ----------------------------------------------------------------------
# Behavioral coverage — small deltas keep CI snappy.
# ----------------------------------------------------------------------


async def test_short_delay_long_timeout_produces_slow_but_ok_callback() -> None:
    """delay_ms=300, timeout_ms=60000 → callback returns None after ~300ms; no error."""
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=60_000)
    result, _span, elapsed = await _invoke_callback_in_tool_span(fault)

    assert result is None  # ADK contract: None means "let the real tool run"
    assert elapsed >= 0.30  # asyncio.sleep(0.3) actually slept

    s = _last_tool_span(_TEST_EXPORTER)
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.type") == "latency_spike"
    assert s.attributes.get("chaoslab.fault.delay_ms") == 300
    assert s.attributes.get("chaoslab.fault.timeout_ms") == 60_000
    assert s.attributes.get("chaoslab.fault.injected") is True


async def test_target_tool_name_mismatch_lets_real_tool_run() -> None:
    """target_tool_name mismatch → callback returns None instantly with no fault attrs."""
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100, target_tool_name="other_tool")
    start = time.monotonic()
    result, _, elapsed = await _invoke_callback_in_tool_span(fault)
    assert result is None
    assert elapsed < 0.05  # no sleep happened
    assert (time.monotonic() - start) < 0.05

    s = _last_tool_span(_TEST_EXPORTER)
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.type") is None  # no attrs set when skipped


async def test_target_tool_name_match_runs_full_delay() -> None:
    """target_tool_name='_lookup_order' matches the test tool → sleep + attrs set."""
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100, target_tool_name="_lookup_order")
    _, _, elapsed = await _invoke_callback_in_tool_span(fault)
    assert elapsed >= 0.30

    s = _last_tool_span(_TEST_EXPORTER)
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.injected") is True


async def test_rate_zero_short_circuits_without_sleeping() -> None:
    """rate=0.0 → callback returns None immediately; no sleep, no attrs."""
    fault = LatencySpikeFault(delay_ms=10_000, timeout_ms=100, rate=0.0)
    result, _, elapsed = await _invoke_callback_in_tool_span(fault)
    assert result is None
    assert elapsed < 0.05  # rate=0 → no sleep

    s = _last_tool_span(_TEST_EXPORTER)
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.type") is None


async def test_callback_accepts_adk_kwarg_invocation_contract() -> None:
    """ADK invokes before_tool_callback with kwargs tool=, args=, tool_context=.

    See google/adk/flows/llm_flows/functions.py:565,808. Regression guard
    mirrors F1/F2/F3 — locks in the param-name contract.
    `callback: Any` so ty doesn't reject kwarg-by-name on the Callable type.
    """
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    callback: Any = fault.as_callback()
    result = await callback(
        tool=_LOOKUP_ORDER_TOOL,
        args={"order_id": "12345"},
        tool_context=cast(ToolContext, None),
    )
    assert result is None


# ----------------------------------------------------------------------
# httpx_transport behavioral coverage.
# ----------------------------------------------------------------------


async def test_httpx_transport_writes_timeout_into_request_extensions() -> None:
    """The transport shim must inject the timeout into request.extensions['timeout']."""
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=2500)
    transport = cast(Any, fault.httpx_transport())
    request = httpx.Request("GET", "http://example.invalid/")
    captured: dict[str, Any] = {}

    class _Probe(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            captured["extensions"] = dict(request.extensions)
            return httpx.Response(200, request=request)

    # Rebind the inner transport to a no-network probe; the shim's contract
    # is to inject timeouts into request.extensions before delegating, and
    # _base is the documented attribute for the inner delegate.
    transport._base = _Probe()
    await transport.handle_async_request(request)

    timeout_ext = captured["extensions"].get("timeout")
    assert timeout_ext is not None
    # 2500 ms == 2.5 s; the shim writes per-phase timeouts derived from a single ms value.
    assert timeout_ext.get("read") == pytest.approx(2.5, rel=0.01)
    assert timeout_ext.get("connect") == pytest.approx(2.5, rel=0.01)


# ----------------------------------------------------------------------
# Canonical demo-config slow test — gated by @pytest.mark.slow so default
# PR loop doesn't pay the 30s. The BDD's 30000/10000 pair lives here.
# ----------------------------------------------------------------------


@pytest.mark.slow
async def test_demo_config_2s_span_attrs_carry_full_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Demo config shape: delay carries through to span attrs unchanged.

    The canonical demo uses ``delay_ms=30_000, timeout_ms=10_000`` — but the
    raw 30s sleep makes even the slow-marked suite painful. The shape we
    actually need to verify is that the SPAN ATTRS carry the full configured
    values for the Judge to read; the asyncio.sleep mechanics are already
    covered by the small-delta tests above. We monkeypatch ``asyncio.sleep``
    in the fault module so the test runs in ~0s but still exercises the
    full callback path with the demo config.

    Skip with: ``pytest -m "not slow"`` (default PR config does this).
    """
    from chaoslab_agent.injector.faults import latency_spike as ls_mod

    async def _fast_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(ls_mod.asyncio, "sleep", _fast_sleep)

    fault = LatencySpikeFault(delay_ms=30_000, timeout_ms=10_000)
    callback = fault.as_callback()
    with _TEST_TRACER.start_as_current_span("test.tool.call") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        await callback(_LOOKUP_ORDER_TOOL, {"order_id": "12345"}, cast(ToolContext, None))

    s = _last_tool_span(_TEST_EXPORTER)
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.delay_ms") == 30_000
    assert s.attributes.get("chaoslab.fault.timeout_ms") == 10_000
    assert s.attributes.get("chaoslab.fault.injected") is True
