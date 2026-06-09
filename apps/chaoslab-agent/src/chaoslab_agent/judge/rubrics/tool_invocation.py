"""F1 malformed_tool_output rubric — wraps Phoenix's ToolInvocationEvaluator.

Per architecture/04 §4.1 + §5: reuse Phoenix's built-in
``ToolInvocationEvaluator`` rather than re-implement. Pass = the agent
detected the malformed tool output and recovered (retry, fallback, honest
"I don't know"). Fail = the agent confabulated an answer or crashed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.rubrics._base import EvalScore, RubricInput

if TYPE_CHECKING:
    from phoenix.evals import LLM
    from phoenix.evals.metrics.tool_invocation import ToolInvocationEvaluator

# Lazy singletons: instantiating ``LLM(provider="google_genai", ...)`` at
# module load triggers a credential check that breaks unit-test imports
# without GOOGLE_API_KEY set (story-6.1 spec line 281).
_JUDGE: Any = None
_EVALUATOR: Any = None


def _judge() -> LLM:
    global _JUDGE  # noqa: PLW0603
    if _JUDGE is None:
        from phoenix.evals import LLM

        _JUDGE = LLM(provider="google_genai", model=get_settings().JUDGE_LLM)
    return _JUDGE


def _evaluator() -> ToolInvocationEvaluator:
    global _EVALUATOR  # noqa: PLW0603
    if _EVALUATOR is None:
        from phoenix.evals.metrics.tool_invocation import ToolInvocationEvaluator

        _EVALUATOR = ToolInvocationEvaluator(llm=_judge())
    return _EVALUATOR


async def tool_invocation_rubric(inp: RubricInput) -> EvalScore:
    span = await inp.phoenix_client.spans.get_span(span_id=inp.span_id)  # ty: ignore[unresolved-attribute]
    # OpenInference attribute keys per architecture/02 §5.1 — fall back to
    # empty string so the evaluator handles missing fields rather than
    # crashing (story-6.1 spec line 280).
    payload = {
        "input": span.attributes.get("input.value", ""),
        "available_tools": span.attributes.get("llm.tools", "[]"),
        "tool_selection": span.attributes.get("llm.output_messages", ""),
    }
    # Phoenix's async_evaluate returns List[Score]; single-classifier
    # evaluators always emit exactly one Score per input.
    verdict = (await _evaluator().async_evaluate(payload))[0]
    passed = verdict.label == "correct"
    return EvalScore(
        passed=passed,
        score=1.0 if passed else 0.0,
        reason=(
            f"tool_invocation verdict={verdict.label}: {verdict.explanation or 'no explanation'}"
        ),
    )


__all__ = ["tool_invocation_rubric"]
