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
    FakeSpan,
    StubVerdict,
    child,
    make_input,
    stub_evaluator,
)


def _inp(span: FakeSpan) -> RubricInput:
    return make_input("malformed_tool_output", span)


def _full_attrs() -> dict[str, Any]:
    return {
        "input.value": "lookup order",
        "llm.tools": "[]",
        "llm.output_messages": "stub",
    }


async def test_flattened_llm_tools_and_output_messages_are_reassembled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real openinference google-adk spans never carry a whole `llm.tools`
    key — they flatten to `llm.tools.{i}.tool.json_schema` (and likewise
    `llm.output_messages.{i}...`). The rubric must reassemble the family
    instead of erroring every probe (IF-16 live finding)."""
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct"), captured=captured))
    llm_span = child(
        {
            "llm.tools.0.tool.json_schema": '{"description":"Look up an order"}',
            "llm.tools.1.tool.json_schema": '{"description":"Issue a refund"}',
            "llm.output_messages.0.message.role": "model",
            "llm.output_messages.0.message.contents.0.message_content.text": "order not found",
        }
    )
    await tool_invocation_rubric(
        make_input(
            "malformed_tool_output",
            FakeSpan(attributes={"input.value": "lookup order"}),
            llm_span,
        )
    )
    assert "Look up an order" in captured[0]["available_tools"]
    assert "Issue a refund" in captured[0]["available_tools"]
    assert "order not found" in captured[0]["tool_selection"]


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


async def test_llm_attrs_found_on_child_span(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm.tools / llm.output_messages live on the target's LLM span (a child),
    not the root agent span — trace-wide selection must find them there."""
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(f1, "_EVALUATOR", stub_evaluator(StubVerdict("correct"), captured=captured))
    root = FakeSpan(attributes={"input.value": "lookup order"})
    llm = child({"llm.tools": "[lookup_order]", "llm.output_messages": "called lookup_order"})
    await tool_invocation_rubric(make_input("malformed_tool_output", root, llm))
    assert captured[0]["available_tools"] == "[lookup_order]"
    assert captured[0]["tool_selection"] == "called lookup_order"


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
