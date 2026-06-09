"""Cross-rubric Judge sub-agent value types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chaoslab_agent.judge.rubrics._base import (
    SPAN_ID_PATTERN,
    EvalScore,
    FaultClass,
)


class FailedSpan(BaseModel):
    """One failed span feeding the clusterer."""

    model_config = ConfigDict(frozen=True)

    span_id: str = Field(pattern=SPAN_ID_PATTERN)
    fault_class: FaultClass
    eval_score: EvalScore
    trace_excerpt: str = Field(min_length=1, max_length=500)

    @field_validator("trace_excerpt")
    @classmethod
    def _excerpt_not_blank(cls, value: str) -> str:
        # A whitespace-only excerpt slips past min_length=1 but gives the
        # clusterer nothing to reason about — refuse construction.
        if not value.strip():
            msg = "trace_excerpt must contain non-whitespace content"
            raise ValueError(msg)
        return value


__all__ = ["FailedSpan"]
