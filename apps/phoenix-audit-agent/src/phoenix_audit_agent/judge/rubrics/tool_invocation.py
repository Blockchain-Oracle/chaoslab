"""F1 malformed_tool_output rubric — wraps Phoenix ToolInvocationEvaluator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from phoenix_audit_agent.judge.rubrics._base import (
    EvalScore,
    RubricInput,
    first_verdict,
    require_attr,
)
from phoenix_audit_agent.judge.rubrics._llm import get_judge_llm

if TYPE_CHECKING:
    from phoenix.evals.metrics.tool_invocation import ToolInvocationEvaluator

_EVALUATOR: Any = None
# Phoenix's allowed verdict labels for ToolInvocationEvaluator — drift here
# silently flips every attack to FAIL, so we enumerate and raise on unknowns.
_PASS_LABEL = "correct"  # noqa: S105 — Phoenix verdict label, not a credential
_KNOWN_LABELS = frozenset({"correct", "incorrect"})


def _evaluator() -> ToolInvocationEvaluator:
    global _EVALUATOR  # noqa: PLW0603
    if _EVALUATOR is None:
        from phoenix.evals.metrics.tool_invocation import ToolInvocationEvaluator

        _EVALUATOR = ToolInvocationEvaluator(llm=get_judge_llm())
    return _EVALUATOR


async def tool_invocation_rubric(inp: RubricInput) -> EvalScore:
    span = await inp.phoenix_client.spans.get_span(span_id=inp.span_id)
    payload = {
        "input": require_attr(
            span, "input.value", span_id=inp.span_id, fault_class=inp.fault_class
        ),
        "available_tools": require_attr(
            span, "llm.tools", span_id=inp.span_id, fault_class=inp.fault_class
        ),
        "tool_selection": require_attr(
            span,
            "llm.output_messages",
            span_id=inp.span_id,
            fault_class=inp.fault_class,
        ),
    }
    verdict = first_verdict(
        await _evaluator().async_evaluate(payload),
        span_id=inp.span_id,
        fault_class=inp.fault_class,
    )
    if verdict.label not in _KNOWN_LABELS:
        msg = (
            f"rubric={inp.fault_class} span_id={inp.span_id} Phoenix returned "
            f"unknown label {verdict.label!r}; expected one of {sorted(_KNOWN_LABELS)}"
        )
        raise RuntimeError(msg)
    passed = verdict.label == _PASS_LABEL
    return EvalScore(
        passed=passed,
        score=1.0 if passed else 0.0,
        reason=(
            f"tool_invocation verdict={verdict.label}: {verdict.explanation or 'no explanation'}"
        ),
    )


__all__ = ["tool_invocation_rubric"]
