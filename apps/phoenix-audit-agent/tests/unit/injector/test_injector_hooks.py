"""Injector progress hooks — the SSE bridge into POST /run.

The live audit UI needs a per-attack event stream. These tests pin the
contract: `Injector` accepts optional async `on_attack_start` /
`on_attack_end` callbacks, invoked in plan order, with the started attack
and the recorded result respectively. No hooks supplied == current
behavior (no calls, no crash).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import HttpUrl

from phoenix_audit_agent.injector.agent import (
    AttackResult,
    AttackRun,
    Injector,
    InjectorState,
)
from phoenix_audit_agent.injector.target_adapters import AdapterTier, TargetAdapter, TargetSpec


class _NullAdapter(TargetAdapter):
    """Concrete TargetAdapter whose I/O surface is never exercised —
    `_run_baseline` and `_run_one_attack` are monkeypatched below, but
    `connect()`/`disconnect()` in `Injector.run()`'s lifecycle DO fire.
    """

    async def connect(self) -> None:
        return None

    async def invoke(self, invocation: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def fingerprint(self) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def disconnect(self) -> None:
        return None


def _result_for(attack: AttackRun) -> AttackResult:
    return AttackResult(
        run_idx=attack.run_idx,
        fault_class=attack.fault_class,
        span_id=f"{attack.run_idx:016x}",
        trace_id=f"{attack.run_idx:032x}",
        status="ok",
        duration_ms=12.5,
    )


@pytest.fixture
def patched_injector(monkeypatch: pytest.MonkeyPatch) -> Injector:
    async def fake_baseline(self: Injector) -> None:
        self.state.baseline_passed = True
        self.state.baseline_pass_rate = 1.0

    async def fake_attack(self: Injector, attack: AttackRun) -> None:
        self.state.record_attack(_result_for(attack))

    monkeypatch.setattr(Injector, "_run_baseline", fake_baseline)
    monkeypatch.setattr(Injector, "_run_one_attack", fake_attack)
    spec = TargetSpec(
        tier=AdapterTier.TIER1_ADK,
        url=HttpUrl("http://localhost:8001"),
        framework="adk-a2a",
    )
    return Injector(
        target=_NullAdapter(spec),
        state=InjectorState(),
        prompt="hook-test",
        runs_per_fault=2,
    )


@pytest.mark.asyncio
async def test_hooks_fire_per_attack_in_plan_order(
    patched_injector: Injector,
) -> None:
    events: list[tuple[str, Any]] = []

    async def on_start(attack: AttackRun) -> None:
        events.append(("start", attack.run_idx))

    async def on_end(result: AttackResult) -> None:
        events.append(("end", result.run_idx))

    patched_injector.on_attack_start = on_start
    patched_injector.on_attack_end = on_end

    state = await patched_injector.run()

    # 4 fault classes x runs_per_fault=2 = 8 attacks
    assert state.total_attacks == 8
    assert len(events) == 16
    # start_k strictly precedes end_k; pairs are sequential, never interleaved
    for i in range(8):
        assert events[2 * i][0] == "start"
        assert events[2 * i + 1][0] == "end"
        assert events[2 * i][1] == events[2 * i + 1][1]


@pytest.mark.asyncio
async def test_end_hook_receives_the_recorded_result(
    patched_injector: Injector,
) -> None:
    seen: list[AttackResult] = []

    async def on_end(result: AttackResult) -> None:
        seen.append(result)

    patched_injector.on_attack_end = on_end
    state = await patched_injector.run()

    assert [r.span_id for r in seen] == [r.span_id for r in state.attack_results]


@pytest.mark.asyncio
async def test_no_hooks_is_the_default_and_does_not_crash(
    patched_injector: Injector,
) -> None:
    assert patched_injector.on_attack_start is None
    assert patched_injector.on_attack_end is None
    state = await patched_injector.run()
    assert state.total_attacks == 8


@pytest.mark.asyncio
async def test_hook_exception_does_not_abort_the_audit(
    patched_injector: Injector,
) -> None:
    """Hooks are UI telemetry — an SSE-plumbing failure must never kill a
    real audit run. The exception is logged, the attacks continue."""
    calls = {"n": 0}

    async def exploding_hook(_arg: Any) -> None:
        calls["n"] += 1
        msg = "synthetic-sse-plumbing-failure"
        raise RuntimeError(msg)

    patched_injector.on_attack_start = exploding_hook
    patched_injector.on_attack_end = exploding_hook

    state = await patched_injector.run()

    assert state.total_attacks == 8  # every attack still ran
    assert calls["n"] == 16  # every hook still fired (and failed) per attack
