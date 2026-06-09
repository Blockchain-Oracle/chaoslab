"""F4 latency_spike rubric — deterministic, no LLM calls.

Reads the span's duration from Phoenix and compares against
``Settings.LATENCY_SLA_MS``. Score scales with how far under SLA the
duration is; passes iff ``duration_ms < sla_ms`` (strict less-than per BDD
line 87 — exactly-at-SLA fails).
"""

from __future__ import annotations

from typing import Any

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.rubrics._base import EvalScore, RubricInput

_NS_PER_MS = 1_000_000.0


def _duration_ms(span: Any) -> float:
    """Extract per-attack duration from the Phoenix span.

    Prefers the explicit ``chaoslab.duration_ms`` attribute the Injector
    writes; falls back to ``end_time_ns - start_time_ns`` when the attribute
    is absent (older spans).
    """
    explicit = span.attributes.get("chaoslab.duration_ms")
    if explicit is not None:
        return float(explicit)
    return (span.end_time_ns - span.start_time_ns) / _NS_PER_MS


async def latency_failure_rubric(inp: RubricInput) -> EvalScore:
    span = await inp.phoenix_client.spans.get_span(span_id=inp.span_id)  # ty: ignore[unresolved-attribute]
    duration_ms = _duration_ms(span)
    sla_ms = get_settings().LATENCY_SLA_MS
    passed = duration_ms < sla_ms
    # Score scales with how comfortably we beat the SLA. Fast tools score
    # near 1.0; tools exactly at SLA score 1.0 but fail the boolean gate;
    # tools 2x over SLA score 0.5; tools 10x over SLA score 0.1.
    score = min(1.0, sla_ms / max(duration_ms, 1.0))
    return EvalScore(
        passed=passed,
        score=score,
        reason=f"duration {duration_ms:.0f}ms vs SLA {sla_ms:.0f}ms",
    )


__all__ = ["latency_failure_rubric"]
