"""Judge phase of the audit pipeline — per-probe verdicts + tally.

Extracted from audit_runner (400-line cap). Collaborators (`apply_rubric`,
`span_honored`) are INJECTED by the caller so the monkeypatch seams stay on
the `phoenix_audit_agent.audit_runner` module attributes, as every test and
the module docstring promise.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from phoenix_audit_agent.injector.agent import InjectorState
from phoenix_audit_agent.judge import FailedSpan
from phoenix_audit_agent.judge.rubrics import EvalScore, RubricInput
from phoenix_audit_agent.reporter import ReportProbe
from phoenix_audit_agent.reporter.honored import HonoredStatus

_log = structlog.get_logger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
ApplyRubricFn = Callable[[RubricInput], Awaitable[EvalScore]]
SpanHonoredFn = Callable[..., Awaitable[HonoredStatus]]

# Mirrors judge.rubrics._base.SPAN_ID_PATTERN: rubrics reject anything that is
# not a 16- or 32-char hex id, so transport failures that never produced a
# span are scored at the transport level instead.
HEX_SPAN = re.compile(r"^[0-9a-f]{16}(?:[0-9a-f]{16})?$")


class JudgeTally:
    """Per-run judge outcome — counts plus the clusterable failure set."""

    def __init__(self) -> None:
        self.failures: list[FailedSpan] = []
        self.report_probes: list[ReportProbe] = []
        self.passed = 0
        self.failed = 0
        self.errored = 0
        self.transport_failed = 0
        # honored_missing drives the locked warning's {N}: only response spans
        # actually READ and found lacking count (docs/header-convention.md).
        # Unreadable spans tally separately and are disclosed in the report —
        # a regulator must distinguish "verified compliant" from "unverifiable".
        self.honored_missing = 0
        self.honored_unreadable = 0


async def judge_attacks(
    state: InjectorState,
    phoenix: Any,
    *,
    emit: EmitFn,
    run_id: str,
    project: str,
    apply_rubric: ApplyRubricFn,
    span_honored: SpanHonoredFn,
) -> JudgeTally:
    """Score every attack with the per-fault rubric, emitting test_verdict frames.

    Containment rules (review findings on PR #81):
    - transport failures (status != ok, or no usable span id) are real FAILs
      with `transport_error: true` and are excluded from the clusterable set;
    - a rubric exception yields a MARKED `error` verdict (`rubric_error: true`)
      and never voids the other probes' verdicts (CLAUDE.md pattern #4).
    """
    tally = JudgeTally()
    for result in state.attack_results:
        n = result.run_idx + 1
        transport_ok = result.status == "ok" and bool(HEX_SPAN.fullmatch(result.span_id))
        if transport_ok:
            honored = await span_honored(
                phoenix,
                span_id=result.span_id,
                trace_id=result.trace_id,
                project_identifier=project,
                run_id=run_id,
            )
            if honored == "missing":
                tally.honored_missing += 1
            elif honored == "unreadable":
                tally.honored_unreadable += 1
        if not transport_ok:
            tally.failed += 1
            tally.transport_failed += 1
            tally.report_probes.append(
                ReportProbe(
                    n=n,
                    fault_class=result.fault_class,
                    verdict="fail",
                    span_id=result.span_id,
                    score=0.0,
                    transport_error=True,
                )
            )
            await emit(
                "test_verdict",
                {
                    "n": n,
                    "verdict": "fail",
                    "fault_class": result.fault_class,
                    "span_id": result.span_id,
                    "score": 0.0,
                    "transport_error": True,
                    "run_id": run_id,
                },
            )
            continue

        try:
            score = await apply_rubric(
                RubricInput(
                    span_id=result.span_id,
                    trace_id=result.trace_id,
                    project_identifier=project,
                    fault_class=result.fault_class,
                    phoenix_client=phoenix,
                )
            )
        except Exception as rubric_err:
            tally.errored += 1
            tally.report_probes.append(
                ReportProbe(
                    n=n,
                    fault_class=result.fault_class,
                    verdict="error",
                    span_id=result.span_id,
                    score=0.0,
                    rubric_error=True,
                )
            )
            _log.error(
                "rubric_failed",
                run_id=run_id,
                span_id=result.span_id,
                fault_class=result.fault_class,
                exc_type=type(rubric_err).__name__,
                error=str(rubric_err),
                exc_info=True,
            )
            await emit(
                "test_verdict",
                {
                    "n": n,
                    "verdict": "error",
                    "rubric_error": True,
                    "fault_class": result.fault_class,
                    "span_id": result.span_id,
                    "score": 0.0,
                    "transport_error": False,
                    "run_id": run_id,
                },
            )
            continue

        if score.passed:
            tally.passed += 1
        else:
            tally.failed += 1
            excerpt = score.reason.strip()[:500] or "[rubric returned no reason]"
            tally.failures.append(
                FailedSpan(
                    span_id=result.span_id,
                    fault_class=result.fault_class,
                    eval_score=score,
                    trace_excerpt=excerpt,
                )
            )
        tally.report_probes.append(
            ReportProbe(
                n=n,
                fault_class=result.fault_class,
                verdict="pass" if score.passed else "fail",
                span_id=result.span_id,
                score=score.score,
            )
        )
        await emit(
            "test_verdict",
            {
                "n": n,
                "verdict": "pass" if score.passed else "fail",
                "fault_class": result.fault_class,
                "span_id": result.span_id,
                "score": score.score,
                "transport_error": False,
                "run_id": run_id,
            },
        )
    return tally


__all__ = ["HEX_SPAN", "JudgeTally", "judge_attacks"]
