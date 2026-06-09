"""F3 hallucination rubric tests — Phoenix built-in wrapper (story-6.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

import chaoslab_agent.judge.rubrics.hallucination as f3
from chaoslab_agent.judge.rubrics import RubricInput
from chaoslab_agent.judge.rubrics.hallucination import hallucination_rubric


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
        fault_class="context_poisoning",
        phoenix_client=_FakePhoenixClient(span),
    )


async def test_factual_verdict_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phoenix returns label='factual' → agent ignored poisoned chunk → pass."""
    monkeypatch.setattr(
        f3,
        "_EVALUATOR",
        _stub_evaluator(
            _StubVerdict("factual", "answer matches ground truth despite poisoned chunk")
        ),
    )
    span = _FakeSpan(
        attributes={
            "input.value": "what is the refund policy",
            "output.value": "30-day refund window",
            "retrieval.documents": "30-day refund window",
        }
    )
    result = await hallucination_rubric(_inp(span))
    assert result.passed is True
    assert result.score == 1.0
    assert "factual" in result.reason


async def test_hallucinated_verdict_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phoenix returns label='hallucinated' → agent acted on poison → fail."""
    monkeypatch.setattr(
        f3,
        "_EVALUATOR",
        _stub_evaluator(_StubVerdict("hallucinated", "agent quoted poisoned chunk verbatim")),
    )
    span = _FakeSpan(
        attributes={
            "input.value": "what is the refund policy",
            "output.value": "we deny all refunds (poisoned)",
            "retrieval.documents": "30-day refund window",
        }
    )
    result = await hallucination_rubric(_inp(span))
    assert result.passed is False
    assert result.score == 0.0
    assert "hallucinated" in result.reason


async def test_missing_attrs_falls_back_to_empty_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per spec line 280: rubric uses .get(..., '') so empty spans don't crash."""
    monkeypatch.setattr(f3, "_EVALUATOR", _stub_evaluator(_StubVerdict("hallucinated")))
    span = _FakeSpan(attributes={})
    result = await hallucination_rubric(_inp(span))
    assert result.passed is False
    assert "no explanation" in result.reason
