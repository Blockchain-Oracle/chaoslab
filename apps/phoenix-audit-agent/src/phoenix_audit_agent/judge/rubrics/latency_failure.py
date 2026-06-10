"""F4 latency_spike rubric — deterministic, no LLM calls."""

from __future__ import annotations

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.rubrics._base import (
    EvalScore,
    RubricInput,
    RubricInputMissingError,
)

_NS_PER_MS = 1_000_000.0


def _duration_ms(inp: RubricInput) -> float:
    # The auditor MEASURED the round-trip itself (AdapterResult.duration_ms);
    # that client-side measurement is authoritative. Fall back to the target's
    # root-span server timing only when the client value is absent. Neither
    # producing a positive duration is malformed — failing loud here prevents
    # the report from silently scoring it as well-under-SLA.
    if inp.client_duration_ms is not None and inp.client_duration_ms > 0:
        return inp.client_duration_ms
    root = inp.root_span()
    start = getattr(root, "start_time_ns", 0)
    end = getattr(root, "end_time_ns", 0)
    if not start or not end or end <= start:
        raise RubricInputMissingError(
            inp.span_id, inp.fault_class, "client_duration_ms|start_time_ns,end_time_ns"
        )
    return (end - start) / _NS_PER_MS


async def latency_failure_rubric(inp: RubricInput) -> EvalScore:
    duration_ms = _duration_ms(inp)
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
