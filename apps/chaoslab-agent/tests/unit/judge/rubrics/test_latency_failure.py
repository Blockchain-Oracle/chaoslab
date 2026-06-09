"""F4 deterministic latency rubric tests (story-6.1).

Asserts no outbound LLM HTTP calls fire via respx — the rubric is
deterministic by contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
import respx

from chaoslab_agent.judge.rubrics import RubricInput
from chaoslab_agent.judge.rubrics.latency_failure import latency_failure_rubric


@dataclass
class _FakeSpan:
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0


class _FakeSpansClient:
    def __init__(self, span: _FakeSpan) -> None:
        self._span = span

    async def get_span(self, span_id: str) -> _FakeSpan:
        return self._span


class _FakePhoenixClient:
    def __init__(self, span: _FakeSpan) -> None:
        self.spans = _FakeSpansClient(span)


def _inp(span: _FakeSpan) -> RubricInput:
    return RubricInput(
        span_id="span-1",
        fault_class="latency_spike",
        phoenix_client=_FakePhoenixClient(span),
    )


async def test_fast_tool_passes_with_score_near_one() -> None:
    """Duration 1200ms vs SLA 5000ms → passes; score reflects the ~4x margin."""
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 1200.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True
    assert result.score > 0.5
    assert "1200" in result.reason
    assert "5000" in result.reason


async def test_slow_tool_fails_with_explicit_duration_in_reason() -> None:
    """Duration 9000ms vs SLA 5000ms → fails; reason names the offending duration."""
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 9000.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is False
    assert "duration" in result.reason
    assert "9000" in result.reason


async def test_exactly_at_sla_fails_strict_less_than() -> None:
    """Duration == SLA is NOT a pass (strict <)."""
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 5000.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is False


async def test_falls_back_to_span_end_minus_start_when_attribute_missing() -> None:
    """No chaoslab.duration_ms → derive from end_time_ns - start_time_ns."""
    span = _FakeSpan(
        attributes={},
        start_time_ns=1_000_000_000,
        end_time_ns=4_000_000_000,
    )  # 3000ms gap, passes
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True
    assert "3000" in result.reason


async def test_no_outbound_llm_calls_fire() -> None:
    """The deterministic rubric must NOT touch googleapis.com or any LLM HTTP."""
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 1200.0})
    with respx.mock(assert_all_called=False) as router:
        # Route any googleapis or generativelanguage hit to a sentinel that
        # would loudly fail; if our deterministic rubric calls out, this
        # assertion catches it.
        router.route(host__regex=r".*googleapis\.com").mock(
            side_effect=RuntimeError("F4 must not call googleapis.com")
        )
        router.route(host__regex=r".*generativelanguage\.googleapis\.com").mock(
            side_effect=RuntimeError("F4 must not call generativelanguage API")
        )
        result = await latency_failure_rubric(_inp(span))
        assert result.passed is True
        # Ensure no calls actually hit either mocked route.
        assert all(call.call_count == 0 for call in router.routes)


async def test_score_clamps_to_one_for_extremely_fast_calls() -> None:
    """Sub-millisecond durations must not produce score > 1.0."""
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 0.5})
    result = await latency_failure_rubric(_inp(span))
    assert result.score == pytest.approx(1.0)
    assert result.passed is True
