"""Pure Pydantic-validation tests for F4 LatencySpikeFault.

Schema-level tests that don't exercise asyncio or httpx — those live in
the integration suite (test_latency_spike.py).
"""

from __future__ import annotations

import inspect

import httpx
import pytest
from pydantic import ValidationError

from chaoslab_agent.injector.faults import LatencySpikeFault


def test_accepts_valid_delay_and_timeout() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    assert fault.delay_ms == 300
    assert fault.timeout_ms == 100


def test_rejects_negative_delay_ms() -> None:
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=-1, timeout_ms=100)


def test_rejects_negative_timeout_ms() -> None:
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=300, timeout_ms=-1)


def test_rejects_delay_above_max() -> None:
    """Bounded at 120_000 ms (2 min) to prevent runaway fault configs."""
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=120_001, timeout_ms=100)


def test_rejects_timeout_above_max() -> None:
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=300, timeout_ms=120_001)


def test_target_tool_name_defaults_to_none() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    assert fault.target_tool_name is None


def test_target_tool_name_accepts_string() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100, target_tool_name="lookup_order")
    assert fault.target_tool_name == "lookup_order"


def test_rate_defaults_to_one_and_clamps() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    assert fault.rate == 1.0
    LatencySpikeFault(delay_ms=300, timeout_ms=100, rate=0.0)
    LatencySpikeFault(delay_ms=300, timeout_ms=100, rate=0.5)
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=300, timeout_ms=100, rate=1.5)
    with pytest.raises(ValidationError):
        LatencySpikeFault(delay_ms=300, timeout_ms=100, rate=-0.1)


def test_as_callback_returns_async_callable() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    cb = fault.as_callback()
    assert callable(cb)
    assert inspect.iscoroutinefunction(cb)


def test_httpx_transport_returns_async_base_transport_subclass() -> None:
    fault = LatencySpikeFault(delay_ms=300, timeout_ms=100)
    transport = fault.httpx_transport()
    assert isinstance(transport, httpx.AsyncBaseTransport)
