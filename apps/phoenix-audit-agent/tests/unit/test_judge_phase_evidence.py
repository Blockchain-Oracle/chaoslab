"""S-EC7: judge phase — one trace fetch per probe, shared evidence, concurrency.

The old shape fetched the same trace twice per probe (honored + rubric) and
ran 24 probes serially — both halves of the 90-second budget problem. The new
contract: judge_phase fetches each probe's trace ONCE, hands the spans to the
honored-check and the rubric, runs probes concurrently, and maps an
unreadable trace to a disclosed error verdict (never a silent pass).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from phoenix_audit_agent import judge_phase as jp
from phoenix_audit_agent.injector.agent import AttackResult, InjectorState
from phoenix_audit_agent.judge.rubrics import EvalScore
from phoenix_audit_agent.phoenix_tools.span_fetch import FetchedSpan
from phoenix_audit_agent.reporter.honored import HonoredStatus

_TRACE = "ab" * 16


def _result(
    n: int, *, fault: str = "prompt_injection", payload: str | None = "INJ"
) -> AttackResult:
    trace_id = f"{n:032x}"
    return AttackResult(
        run_idx=n - 1,
        fault_class=fault,  # ty: ignore[invalid-argument-type]
        span_id=trace_id,
        trace_id=trace_id,
        status="ok",
        duration_ms=123.0,
        attack_payload=payload,
    )


def _spans() -> list[FetchedSpan]:
    return [
        FetchedSpan(
            span_id="a" * 16,
            trace_id=_TRACE,
            parent_id="",
            attributes={"phoenix_audit.honored": True, "output.value": "out"},
        )
    ]


class _Emit:
    def __init__(self) -> None:
        self.frames: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, event: str, data: dict[str, Any]) -> None:
        self.frames.append((event, data))


async def _passing_rubric(inp: Any) -> EvalScore:
    return EvalScore(passed=True, score=1.0, reason="ok")


def _honored(spans: list[FetchedSpan], **_: Any) -> HonoredStatus:
    return "honored" if spans else "unreadable"


async def test_trace_fetched_exactly_once_per_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[str] = []

    async def fake_fetch(phoenix: Any, *, trace_id: str, project_identifier: str) -> list[Any]:
        fetch_calls.append(trace_id)
        return _spans()

    monkeypatch.setattr(jp, "fetch_trace_spans", fake_fetch)
    state = InjectorState(attack_results=[_result(1), _result(2), _result(3)])
    emit = _Emit()
    tally = await jp.judge_attacks(
        state,
        phoenix=object(),
        emit=emit,
        run_id="r",
        project="target-agent",
        apply_rubric=_passing_rubric,
        span_honored=_honored,
        prompt="original question",
    )
    assert sorted(fetch_calls) == sorted([r.trace_id for r in state.attack_results])
    assert len(fetch_calls) == 3, "exactly ONE Phoenix fetch per probe"
    assert tally.passed == 3


async def test_rubric_receives_prefetched_spans_and_auditor_known_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Any] = []

    async def capture_rubric(inp: Any) -> EvalScore:
        captured.append(inp)
        return EvalScore(passed=True, score=1.0, reason="ok")

    async def fake_fetch(*a: Any, **k: Any) -> list[Any]:
        return _spans()

    monkeypatch.setattr(jp, "fetch_trace_spans", fake_fetch)
    state = InjectorState(attack_results=[_result(1)])
    await jp.judge_attacks(
        state,
        phoenix=object(),
        emit=_Emit(),
        run_id="r",
        project="target-agent",
        apply_rubric=capture_rubric,
        span_honored=_honored,
        prompt="original question",
    )
    inp = captured[0]
    assert inp.spans
    assert inp.spans[0].attributes["output.value"] == "out"
    assert inp.attack_payload == "INJ"
    assert inp.original_user_message == "original question"
    assert inp.client_duration_ms == 123.0


async def test_unreadable_trace_yields_disclosed_error_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_fetch(*a: Any, **k: Any) -> list[Any]:
        raise httpx.ConnectError("phoenix down")

    monkeypatch.setattr(jp, "fetch_trace_spans", failing_fetch)
    state = InjectorState(attack_results=[_result(1)])
    emit = _Emit()
    tally = await jp.judge_attacks(
        state,
        phoenix=object(),
        emit=emit,
        run_id="r",
        project="target-agent",
        apply_rubric=_passing_rubric,
        span_honored=_honored,
        prompt="q",
    )
    assert tally.errored == 1
    assert tally.honored_unreadable == 1
    verdicts = [d for e, d in emit.frames if e == "test_verdict"]
    assert verdicts[0]["verdict"] == "error"
    assert verdicts[0]["rubric_error"] is True


async def test_probes_run_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    in_flight = 0
    peak = 0

    async def slow_fetch(*a: Any, **k: Any) -> list[Any]:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return _spans()

    monkeypatch.setattr(jp, "fetch_trace_spans", slow_fetch)
    state = InjectorState(attack_results=[_result(n) for n in range(1, 7)])
    await jp.judge_attacks(
        state,
        phoenix=object(),
        emit=_Emit(),
        run_id="r",
        project="target-agent",
        apply_rubric=_passing_rubric,
        span_honored=_honored,
        prompt="q",
    )
    assert peak > 1, "probes must overlap — serial judging blows the 90s budget"


async def test_report_probes_are_ordered_by_n_despite_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def jittered_fetch(phoenix: Any, *, trace_id: str, **k: Any) -> list[Any]:
        await asyncio.sleep(0.01 * (int(trace_id, 16) % 3))
        return _spans()

    monkeypatch.setattr(jp, "fetch_trace_spans", jittered_fetch)
    state = InjectorState(attack_results=[_result(n) for n in range(1, 9)])
    tally = await jp.judge_attacks(
        state,
        phoenix=object(),
        emit=_Emit(),
        run_id="r",
        project="target-agent",
        apply_rubric=_passing_rubric,
        span_honored=_honored,
        prompt="q",
    )
    assert [p.n for p in tally.report_probes] == list(range(1, 9))
