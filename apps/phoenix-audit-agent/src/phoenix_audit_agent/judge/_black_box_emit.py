"""Emit one black-box probe's verdict — extracted from judge_phase.py to
respect the 400-line per-file cap.

The judge phase routes any AttackResult whose
``span_attributes['phoenix_audit.delivery_mode'] == 'black_box_no_hook'``
through ``emit_black_box_verdict`` instead of the standard span-fetch +
rubric path. We score via ``phoenix.evals`` over the (prompt, response)
pair the auditor already has and quote the judge LLM's explanation on the
SSE frame so the chamber + signed-report cover surface it unchanged.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from phoenix_audit_agent.reporter import ReportProbe

if TYPE_CHECKING:
    from phoenix_audit_agent.injector.agent import AttackResult
    from phoenix_audit_agent.judge_phase import _ProbeOutcome

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def emit_black_box_verdict(
    *,
    result: AttackResult,
    out: _ProbeOutcome,
    n: int,
    emit: EmitFn,
    run_id: str,
    prompt: str,
) -> _ProbeOutcome:
    # Function-level import so tests can monkeypatch
    # phoenix_audit_agent.judge.black_box_evals.evaluate_black_box_probe and
    # have the override take effect at call time, not at import time.
    from phoenix_audit_agent.judge import black_box_evals as _bbe

    eval_prompt = result.attack_payload or prompt
    eval_score = await _bbe.evaluate_black_box_probe(
        fault_class=result.fault_class,
        prompt=eval_prompt,
        response_text=result.response_text,
    )
    skipped = _bbe.black_box_skipped(result.fault_class)
    # Distinct "skip" verdict so the report cover can count
    # deliberate-skips separately from "could not be scored" (errored)
    # and from a real fail. (PR #134 code-review HIGH#1.)
    if skipped:
        verdict, bucket = "skip", "skipped"
        # score=None for skipped probes — any aggregator averaging this
        # MUST filter None or it silently inflates the pass rate.
        probe_score: float | None = None
    elif eval_score.passed:
        verdict, bucket = "pass", "passed"
        probe_score = eval_score.score
    else:
        verdict, bucket = "fail", "failed"
        probe_score = eval_score.score
    out.bucket = bucket
    out.probe = ReportProbe(
        n=n,
        fault_class=result.fault_class,
        verdict=verdict,
        span_id=result.span_id,
        score=probe_score,
        fault_triggered=False,
        # rubric_error is reserved for "the rubric blew up" — do NOT
        # overload it for intentional skips. (PR #134 code-review HIGH#3.)
        rubric_error=False,
        skipped=skipped,
    )
    payload: dict[str, Any] = {
        "n": n,
        "verdict": verdict,
        "fault_class": result.fault_class,
        "span_id": result.span_id,
        "score": probe_score,
        "transport_error": False,
        "fault_triggered": False,
        "delivery_mode": "black_box_no_hook",
        "rubric_reason": eval_score.reason,
        "run_id": run_id,
    }
    if skipped:
        payload["skipped"] = True
    await emit("test_verdict", payload)
    return out


__all__ = ["emit_black_box_verdict"]
