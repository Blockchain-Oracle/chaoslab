"""Cross-rubric Judge sub-agent value types.

`FailedSpan` is the input record the clusterer (story-6.2) receives: one
failed `EvalScore` from the rubric pipeline (story-6.1) plus the span
context the LLM-as-clusterer needs to reason about root cause.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from chaoslab_agent.judge.rubrics._base import EvalScore, FaultClass


class FailedSpan(BaseModel):
    """One failed span feeding the clusterer."""

    model_config = ConfigDict(frozen=True)

    # 16- or 32-char hex matches RubricInput's span_id pattern so the
    # clusterer can dispatch back through the rubrics if needed.
    span_id: str = Field(pattern=r"^[0-9a-f]{16}(?:[0-9a-f]{16})?$")
    fault_class: FaultClass
    eval_score: EvalScore
    # Capped to 500 chars to fit the clusterer's prompt budget at the
    # 72-failure upper bound (see story-6.2 Known pitfalls).
    trace_excerpt: str = Field(min_length=1, max_length=500)


__all__ = ["FailedSpan"]
