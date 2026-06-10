"""F4 latency_spike rubric — deterministic, no LLM calls."""

from __future__ import annotations

from typing import Any

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.rubrics._base import (
    EvalScore,
    RubricInput,
    RubricInputMissingError,
)

_NS_PER_MS = 1_000_000.0


def _duration_ms(span: Any, *, span_id: str, fault_class: str) -> float:
    # The Injector writes phoenix-audit.duration_ms; fall back to end-start only
    # when both timestamps are valid (non-zero and start <= end). A span with
    # neither path producing a positive duration is malformed — failing loud
    # here prevents the report from silently scoring it as well-under-SLA.
    explicit = span.attributes.get("phoenix-audit.duration_ms")
    if explicit is not None:
        try:
            value = float(explicit)
        except (TypeError, ValueError) as exc:
            raise RubricInputMissingError(
                span_id, fault_class, "phoenix-audit.duration_ms"
            ) from exc
        if value <= 0:
            raise RubricInputMissingError(span_id, fault_class, "phoenix-audit.duration_ms")
        return value
    start = getattr(span, "start_time_ns", 0)
    end = getattr(span, "end_time_ns", 0)
    if not start or not end or end <= start:
        raise RubricInputMissingError(
            span_id, fault_class, "phoenix-audit.duration_ms|start_time_ns,end_time_ns"
        )
    return (end - start) / _NS_PER_MS


async def latency_failure_rubric(inp: RubricInput) -> EvalScore:
    span = await inp.fetch_span()
    duration_ms = _duration_ms(span, span_id=inp.span_id, fault_class=inp.fault_class)
    sla_ms = get_settings().LATENCY_SLA_MS
    passed = duration_ms < sla_ms
    # Clamp the failure score below 1.0 so downstream consumers reading score
    # alone (e.g. S6.2 clustering) cannot mistake an at-SLA fail for a pass.
    raw_score = min(1.0, sla_ms / duration_ms)
    score = raw_score if passed else min(raw_score, 0.99)
    return EvalScore(
        passed=passed,
        score=score,
        reason=f"duration {duration_ms:.0f}ms vs SLA {sla_ms:.0f}ms",
    )


__all__ = ["latency_failure_rubric"]
