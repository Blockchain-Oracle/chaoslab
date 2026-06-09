"""F1 tool_invocation rubric tests — Phoenix built-in wrapper (story-6.1).

LLM calls are stubbed via the lazy ``_EVALUATOR`` singleton; tests inject
fake verdicts to verify the wrapper logic without hitting Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

import chaoslab_agent.judge.rubrics.tool_invocation as f1
from chaoslab_agent.judge.rubrics import RubricInput
from chaoslab_agent.judge.rubrics.tool_invocation import tool_invocation_rubric


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


@dataclass
class _StubVerdict:
    label: str
    explanation: str | None = None


def _stub_evaluator(verdict: _StubVerdict) -> Any:
    # Phoenix's async_evaluate returns List[Score]; mirror that contract.
    class _StubEvaluator:
        async def async_evaluate(self, payload: dict[str, Any]) -> list[_StubVerdict]:
            return [verdict]

    return _StubEvaluator()


def _inp(span: _FakeSpan) -> RubricInput:
    return RubricInput(
        span_id="span-1",
        fault_class="malformed_tool_output",
        phoenix_client=_FakePhoenixClient(span),
    )


async def test_correct_verdict_passes_with_score_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phoenix returns label='correct' → rubric passes with score=1.0."""
    monkeypatch.setattr(
        f1, "_EVALUATOR", _stub_evaluator(_StubVerdict("correct", "agent recovered"))
    )
    span = _FakeSpan(attributes={"input.value": "lookup order"})
    result = await tool_invocation_rubric(_inp(span))
    assert result.passed is True
    assert result.score == 1.0
    assert "correct" in result.reason
    assert "tool" in result.reason.lower()


async def test_incorrect_verdict_fails_with_score_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phoenix returns label='incorrect' → rubric fails with score=0.0."""
    monkeypatch.setattr(
        f1,
        "_EVALUATOR",
        _stub_evaluator(_StubVerdict("incorrect", "agent confabulated")),
    )
    span = _FakeSpan(attributes={"input.value": "lookup order"})
    result = await tool_invocation_rubric(_inp(span))
    assert result.passed is False
    assert result.score == 0.0
    assert "incorrect" in result.reason.lower() or "tool" in result.reason.lower()


async def test_missing_span_attributes_does_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per spec line 280: rubric falls back to empty string on missing attrs."""
    monkeypatch.setattr(f1, "_EVALUATOR", _stub_evaluator(_StubVerdict("incorrect")))
    span = _FakeSpan(attributes={})  # no input.value, no llm.tools, etc.
    result = await tool_invocation_rubric(_inp(span))
    assert result.passed is False
    assert result.score == 0.0
    # 'no explanation' fallback fires because StubVerdict had no explanation
    assert "no explanation" in result.reason


async def test_explanation_threaded_through_to_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explanation = "agent returned 'I cannot verify the result' instead of confabulating"
    monkeypatch.setattr(f1, "_EVALUATOR", _stub_evaluator(_StubVerdict("correct", explanation)))
    span = _FakeSpan(attributes={"input.value": "lookup order"})
    result = await tool_invocation_rubric(_inp(span))
    assert explanation in result.reason
