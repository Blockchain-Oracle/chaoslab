"""FailedSpan schema invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chaoslab_agent.judge._models import FailedSpan
from chaoslab_agent.judge.rubrics._base import EvalScore


def _eval_score(passed: bool = False) -> EvalScore:
    return EvalScore(
        passed=passed,
        score=0.0 if not passed else 1.0,
        reason="rubric reason",
    )


def test_failed_span_accepts_valid_shape() -> None:
    f = FailedSpan(
        span_id="0123456789abcdef",
        fault_class="malformed_tool_output",
        eval_score=_eval_score(),
        trace_excerpt="real content",
    )
    assert f.span_id == "0123456789abcdef"


def test_failed_span_rejects_non_hex_span_id() -> None:
    with pytest.raises(ValidationError):
        FailedSpan(
            span_id="not-hex",
            fault_class="malformed_tool_output",
            eval_score=_eval_score(),
            trace_excerpt="content",
        )


def test_failed_span_rejects_whitespace_only_trace_excerpt() -> None:
    with pytest.raises(ValidationError, match="non-whitespace"):
        FailedSpan(
            span_id="0123456789abcdef",
            fault_class="malformed_tool_output",
            eval_score=_eval_score(),
            trace_excerpt="   \n  \t  ",
        )


def test_failed_span_rejects_excerpt_over_500_chars() -> None:
    with pytest.raises(ValidationError):
        FailedSpan(
            span_id="0123456789abcdef",
            fault_class="malformed_tool_output",
            eval_score=_eval_score(),
            trace_excerpt="x" * 501,
        )


def test_failed_span_is_frozen() -> None:
    f = FailedSpan(
        span_id="0123456789abcdef",
        fault_class="malformed_tool_output",
        eval_score=_eval_score(),
        trace_excerpt="content",
    )
    with pytest.raises(ValidationError):
        f.trace_excerpt = "tampered"  # type: ignore[misc]
