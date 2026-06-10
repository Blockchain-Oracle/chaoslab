"""F1 tool_invocation rubric tests."""

from __future__ import annotations

from typing import Any

import pytest

import phoenix_audit_agent.judge.rubrics.tool_invocation as f1
from phoenix_audit_agent.judge.rubrics import (
    PhoenixEvalEmptyError,
    RubricInput,
    RubricInputMissingError,
)
from phoenix_audit_agent.judge.rubrics.tool_invocation import tool_invocation_rubric

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
        fault_class="malformed_tool_output",
        phoenix_client=FakePhoenixClient(span),
    )


def _full_attrs() -> dict[str, Any]:
    return {
        "input.value": "lookup order",
        "llm.tools": "[]",
        "llm.output_messages": "stub",
    }


async def test_correct_verdict_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct", "agent recovered")))
    result = await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert result.passed is True
    assert result.score == 1.0
    assert "correct" in result.reason


async def test_incorrect_verdict_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("incorrect", "confabulated")))
    result = await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert result.passed is False
    assert result.score == 0.0


async def test_explanation_threaded_through(monkeypatch: pytest.MonkeyPatch) -> None:
    explanation = "agent returned 'I cannot verify' instead of confabulating"
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct", explanation)))
    result = await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert explanation in result.reason


async def test_payload_carries_all_three_attrs(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct"), captured=captured))
    await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert captured[0]["input"] == "lookup order"
    assert captured[0]["available_tools"] == "[]"
    assert captured[0]["tool_selection"] == "stub"


@pytest.mark.parametrize("missing", ["input.value", "llm.tools", "llm.output_messages"])
async def test_missing_attr_raises_instead_of_silent_pass(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct")))
    attrs = _full_attrs()
    del attrs[missing]
    with pytest.raises(RubricInputMissingError) as exc:
        await tool_invocation_rubric(_inp(FakeSpan(attributes=attrs)))
    assert exc.value.attribute == missing


async def test_empty_attr_raises_instead_of_silent_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct")))
    attrs = _full_attrs()
    attrs["input.value"] = ""
    with pytest.raises(RubricInputMissingError):
        await tool_invocation_rubric(_inp(FakeSpan(attributes=attrs)))


async def test_empty_phoenix_verdict_list_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class _EmptyEvaluator:
        async def async_evaluate(self, payload: dict[str, Any]) -> list[StubVerdict]:
            return []

    monkeypatch.setattr(f1, "_EVALUATOR", _EmptyEvaluator())
    with pytest.raises(PhoenixEvalEmptyError) as exc:
        await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
    assert exc.value.fault_class == "malformed_tool_output"


async def test_unknown_phoenix_label_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # A Phoenix version bump that introduces "uncertain" must not silently
    # be treated as a fail.
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("uncertain")))
    with pytest.raises(RuntimeError, match="unknown label"):
        await tool_invocation_rubric(_inp(FakeSpan(attributes=_full_attrs())))
