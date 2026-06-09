"""Dispatcher + base-schema tests for the Judge rubrics (story-6.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from chaoslab_agent.judge.rubrics import (
    EvalScore,
    FaultClass,
    RubricInput,
    apply_rubric,
)


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


# ---------------------------------------------------------------------------
# EvalScore + RubricInput schema validation
# ---------------------------------------------------------------------------


def test_eval_score_accepts_valid_values() -> None:
    s = EvalScore(passed=False, score=0.3, reason="malformed tool output")
    assert s.passed is False
    assert s.score == 0.3
    assert s.reason == "malformed tool output"


def test_eval_score_rejects_score_above_one() -> None:
    with pytest.raises(ValidationError):
        EvalScore(passed=False, score=1.5, reason="bad")


def test_eval_score_rejects_empty_reason() -> None:
    with pytest.raises(ValidationError):
        EvalScore(passed=True, score=1.0, reason="")


def test_eval_score_is_frozen() -> None:
    s = EvalScore(passed=True, score=1.0, reason="ok")
    with pytest.raises(ValidationError):
        s.passed = False  # type: ignore[misc]


def test_fault_class_literal_enumerates_four_values() -> None:
    assert set(FaultClass.__args__) == {
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    }


def test_rubric_input_requires_non_empty_span_id() -> None:
    with pytest.raises(ValidationError):
        RubricInput(
            span_id="",
            fault_class="malformed_tool_output",
            phoenix_client=object(),
        )


# ---------------------------------------------------------------------------
# Dispatcher routing
# ---------------------------------------------------------------------------


async def test_dispatcher_raises_on_unknown_fault_class() -> None:
    # Construct an input that bypasses the Literal at the boundary so the
    # runtime dispatch can raise — mirrors the contract violation case
    # where someone smuggles a non-FaultClass string through.
    inp = RubricInput.model_construct(
        span_id="span-1",
        fault_class="not_a_real_fault",  # type: ignore[arg-type]
        phoenix_client=object(),
    )
    with pytest.raises(ValueError, match=r"unknown fault_class"):
        await apply_rubric(inp)


async def test_dispatcher_routes_latency_spike_to_deterministic_rubric() -> None:
    span = _FakeSpan(attributes={"chaoslab.duration_ms": 1200.0})
    inp = RubricInput(
        span_id="span-1",
        fault_class="latency_spike",
        phoenix_client=_FakePhoenixClient(span),
    )
    result = await apply_rubric(inp)
    # Deterministic path: passes since 1200ms < 5000ms SLA
    assert result.passed is True
    assert "duration" in result.reason
    assert "1200" in result.reason


async def test_dispatcher_routes_malformed_tool_output_to_tool_invocation_rubric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Replace the F1 evaluator with a stub before dispatch so we don't pay
    # an LLM call. The rubric reads from a lazy global; injecting the stub
    # there is the cleanest seam.
    import chaoslab_agent.judge.rubrics.tool_invocation as f1

    class _StubVerdict:
        label = "correct"
        explanation = "stub explanation"

    class _StubEvaluator:
        # Phoenix's async_evaluate returns List[Score]; mirror that contract.
        async def async_evaluate(self, payload: dict[str, Any]) -> list[_StubVerdict]:
            return [_StubVerdict()]

    monkeypatch.setattr(f1, "_EVALUATOR", _StubEvaluator())

    span = _FakeSpan(
        attributes={
            "input.value": "lookup order 12345",
            "llm.tools": "[]",
            "llm.output_messages": "stub",
        }
    )
    inp = RubricInput(
        span_id="span-1",
        fault_class="malformed_tool_output",
        phoenix_client=_FakePhoenixClient(span),
    )
    result = await apply_rubric(inp)
    assert result.passed is True
    assert result.score == 1.0
    assert "tool_invocation" in result.reason
