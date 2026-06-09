"""F3 hallucination rubric tests."""

from __future__ import annotations

from typing import Any

import pytest

import chaoslab_agent.judge.rubrics.hallucination as f3
from chaoslab_agent.judge.rubrics import (
    PhoenixEvalEmptyError,
    RubricInput,
    RubricInputMissingError,
)
from chaoslab_agent.judge.rubrics.hallucination import hallucination_rubric

from .conftest import (
    SPAN_ID,
    FakePhoenixClient,
    FakeSpan,
    StubVerdict,
    stub_evaluator,
)


def _inp(span: FakeSpan) -> RubricInput:
    return RubricInput(
        span_id=SPAN_ID,
        fault_class="context_poisoning",
        phoenix_client=FakePhoenixClient(span),
    )


def _full_attrs() -> dict[str, Any]:
    return {
        "input.value": "what is the refund policy",
        "output.value": "30-day refund window",
        "retrieval.documents": "30-day refund window",
    }


async def test_factual_verdict_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f3, "_EVALUATOR", stub_evaluator(StubVerdict("factual", "matches truth")))
    result = await hallucination_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert result.passed is True
    assert result.score == 1.0
    assert "factual" in result.reason


async def test_hallucinated_verdict_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        f3, "_EVALUATOR", stub_evaluator(StubVerdict("hallucinated", "quoted poison"))
    )
    result = await hallucination_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert result.passed is False
    assert result.score == 0.0


async def test_payload_carries_all_three_attrs(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(f3, "_EVALUATOR", stub_evaluator(StubVerdict("factual"), captured=captured))
    await hallucination_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert captured[0]["input"] == "what is the refund policy"
    assert captured[0]["output"] == "30-day refund window"
    assert captured[0]["reference"] == "30-day refund window"


@pytest.mark.parametrize("missing", ["input.value", "output.value", "retrieval.documents"])
async def test_missing_attr_raises_instead_of_silent_pass(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setattr(f3, "_EVALUATOR", stub_evaluator(StubVerdict("factual")))
    attrs = _full_attrs()
    del attrs[missing]
    with pytest.raises(RubricInputMissingError) as exc:
        await hallucination_rubric(_inp(FakeSpan(attributes=attrs)))
    assert exc.value.attribute == missing


async def test_empty_attr_raises_instead_of_silent_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f3, "_EVALUATOR", stub_evaluator(StubVerdict("factual")))
    attrs = _full_attrs()
    attrs["retrieval.documents"] = ""
    with pytest.raises(RubricInputMissingError):
        await hallucination_rubric(_inp(FakeSpan(attributes=attrs)))


async def test_empty_phoenix_verdict_list_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class _EmptyEvaluator:
        async def async_evaluate(self, payload: dict[str, Any]) -> list[StubVerdict]:
            return []

    monkeypatch.setattr(f3, "_EVALUATOR", _EmptyEvaluator())
    with pytest.raises(PhoenixEvalEmptyError):
        await hallucination_rubric(_inp(FakeSpan(attributes=_full_attrs())))


async def test_unknown_phoenix_label_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f3, "_EVALUATOR", stub_evaluator(StubVerdict("ambiguous")))
    with pytest.raises(RuntimeError, match="unknown label"):
        await hallucination_rubric(_inp(FakeSpan(attributes=_full_attrs())))
