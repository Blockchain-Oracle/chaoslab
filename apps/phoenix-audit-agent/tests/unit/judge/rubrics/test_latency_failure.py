"""F4 deterministic latency rubric tests."""

from __future__ import annotations

import pytest
import respx

from phoenix_audit_agent.judge.rubrics import (
    RubricInput,
    RubricInputMissingError,
)
from phoenix_audit_agent.judge.rubrics.latency_failure import latency_failure_rubric

from .conftest import SPAN_ID, FakePhoenixClient, FakeSpan


def _inp(span: FakeSpan) -> RubricInput:
    return RubricInput(
        span_id=SPAN_ID,
        fault_class="latency_spike",
        phoenix_client=FakePhoenixClient(span),
    )


async def test_fast_tool_passes_with_score_above_half() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 1200.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True
    assert result.score > 0.5
    assert "1200" in result.reason
    assert "5000" in result.reason


async def test_slow_tool_fails_with_duration_in_reason() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 9000.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is False
    assert "9000" in result.reason


async def test_one_ms_under_sla_passes_strict_less_than() -> None:
    # Anchors the strict `<` boundary so a regression to `<=` would flip.
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 4999.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True


async def test_exactly_at_sla_fails_strict_less_than() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 5000.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is False


async def test_failing_score_clamps_below_one() -> None:
    # passed=False with score=1.0 would lie to S6.2 clustering — model
    # validator on EvalScore would have raised; this asserts the clamp.
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 5000.0})
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is False
    assert result.score < 1.0
    assert result.score == pytest.approx(0.99)


async def test_falls_back_to_end_minus_start_when_attribute_missing() -> None:
    span = FakeSpan(
        attributes={},
        start_time_ns=1_000_000_000,
        end_time_ns=4_000_000_000,
    )
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True
    assert "3000" in result.reason


async def test_explicit_attribute_wins_over_end_minus_start() -> None:
    # Both paths produce a value; the explicit attribute must take precedence.
    span = FakeSpan(
        attributes={"phoenix-audit.duration_ms": 1500.0},
        start_time_ns=1_000_000_000,
        end_time_ns=9_000_000_000,  # would compute to 8000ms (would FAIL)
    )
    result = await latency_failure_rubric(_inp(span))
    assert result.passed is True
    assert "1500" in result.reason
    assert "8000" not in result.reason


async def test_missing_duration_raises_instead_of_silent_pass() -> None:
    # No attribute + zero timestamps used to silently score 1.0. Refuse.
    span = FakeSpan(attributes={})
    with pytest.raises(RubricInputMissingError):
        await latency_failure_rubric(_inp(span))


async def test_zero_duration_raises_instead_of_silent_pass() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 0.0})
    with pytest.raises(RubricInputMissingError):
        await latency_failure_rubric(_inp(span))


async def test_inverted_timestamps_raises() -> None:
    span = FakeSpan(
        attributes={},
        start_time_ns=4_000_000_000,
        end_time_ns=1_000_000_000,
    )
    with pytest.raises(RubricInputMissingError):
        await latency_failure_rubric(_inp(span))


async def test_no_outbound_llm_calls_fire() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 1200.0})
    with respx.mock(assert_all_called=False) as router:
        router.route(host__regex=r".*googleapis\.com").mock(
            side_effect=RuntimeError("F4 must not call googleapis.com")
        )
        router.route(host__regex=r".*generativelanguage\.googleapis\.com").mock(
            side_effect=RuntimeError("F4 must not call generativelanguage API")
        )
        result = await latency_failure_rubric(_inp(span))
        assert result.passed is True
        assert all(call.call_count == 0 for call in router.routes)


async def test_score_clamps_to_one_for_sub_millisecond_durations() -> None:
    span = FakeSpan(attributes={"phoenix-audit.duration_ms": 0.5})
    result = await latency_failure_rubric(_inp(span))
    assert result.score == pytest.approx(1.0)
    assert result.passed is True
