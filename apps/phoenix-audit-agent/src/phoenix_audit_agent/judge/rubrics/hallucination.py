"""F3 context_poisoning rubric — wraps Phoenix HallucinationEvaluator."""

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
    from phoenix.evals.metrics.hallucination import HallucinationEvaluator

_EVALUATOR: Any = None
_PASS_LABEL = "factual"  # noqa: S105 — Phoenix verdict label, not a credential
_KNOWN_LABELS = frozenset({"factual", "hallucinated"})


def _evaluator() -> HallucinationEvaluator:
    global _EVALUATOR  # noqa: PLW0603
    if _EVALUATOR is None:
        from phoenix.evals.metrics.hallucination import HallucinationEvaluator

        _EVALUATOR = HallucinationEvaluator(llm=get_judge_llm())
    return _EVALUATOR


async def hallucination_rubric(inp: RubricInput) -> EvalScore:
    span = await inp.phoenix_client.spans.get_span(span_id=inp.span_id)
    payload = {
        "input": require_attr(
            span, "input.value", span_id=inp.span_id, fault_class=inp.fault_class
        ),
        "output": require_attr(
            span, "output.value", span_id=inp.span_id, fault_class=inp.fault_class
        ),
        "reference": require_attr(
            span,
            "retrieval.documents",
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
            f"hallucination verdict={verdict.label}: {verdict.explanation or 'no explanation'}"
        ),
    )


__all__ = ["hallucination_rubric"]
