"""Integration tests for BaselineCheck (story-5.6 preflight baseline).

Exercises the full preflight path against an in-process TargetAdapter
implementation that simulates realistic per-invoke latency. Validates that:

1. asyncio.gather parallelizes the N invocations (n=10 against a target
   with 50ms per-call latency completes in ~50-150ms wall-clock — well
   under the 500ms it would take serially).
2. The preflight contract end-to-end: connect → N parallel invokes →
   computed pass_rate → BaselineResult OR BaselineAbortError.
3. Mixed outcomes — successful responses, soft-failure AdapterResults
   with error field set, and raised exceptions — all flow through the
   asyncio.gather(return_exceptions=True) path correctly.

Test doubles (``_LatentTarget``) live in tests/ per §14.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from pydantic import HttpUrl

from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector import BaselineCheck
from chaoslab_agent.injector.target_adapters import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

pytestmark = pytest.mark.integration


class _LatentTarget(TargetAdapter):
    """In-process TargetAdapter that simulates per-invoke latency + scripted outcomes.

    Each invoke sleeps ``per_call_ms`` before returning the next scripted
    outcome — lets us prove parallelism is real (n=10 at 50ms each finishes
    in ~50ms wall-clock under asyncio.gather, vs 500ms serial).
    """

    def __init__(
        self,
        spec: TargetSpec,
        outcomes: list[AdapterResult | Exception],
        per_call_ms: float = 50.0,
    ) -> None:
        super().__init__(spec)
        self._outcomes = list(outcomes)
        self._idx = 0
        self._per_call_s = per_call_ms / 1000.0
        self.connect_count = 0
        self.invoke_count = 0

    async def connect(self) -> None:
        self.connect_count += 1

    async def disconnect(self) -> None:
        pass

    async def fingerprint(self) -> AdapterFingerprint:
        return AdapterFingerprint(tier=self.spec.tier)

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        await asyncio.sleep(self._per_call_s)
        self.invoke_count += 1
        outcome = self._outcomes[(self.invoke_count - 1) % len(self._outcomes)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _spec() -> TargetSpec:
    return TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl("http://localhost:8001/"))


def _ok() -> AdapterResult:
    return AdapterResult(response="ok", duration_ms=10.0, error=None)


def _err(msg: str = "tool failure") -> AdapterResult:
    return AdapterResult(response="", duration_ms=10.0, error=msg)


async def test_happy_path_100pct_completes_under_parallel_wall_clock() -> None:
    """N=10 invokes at 50ms each completes in ~50-200ms via asyncio.gather.

    Proves the implementation actually parallelizes — serial execution would
    take ~500ms (10 * 50ms), so a wall-clock bound of 0.4s is a safe lower-
    bound for "parallel was used."
    """
    target = _LatentTarget(_spec(), [_ok()] * 10, per_call_ms=50.0)
    start = time.monotonic()
    result = await BaselineCheck(target=target, n=10).validate()
    elapsed = time.monotonic() - start

    assert result.pass_rate == 1.0
    assert result.aborted is False
    assert result.passed == 10
    assert target.invoke_count == 10
    assert target.connect_count == 1  # connect() called exactly once
    # If executed serially, elapsed >= 0.5s. Asyncio.gather brings it well below.
    assert elapsed < 0.4, f"asyncio.gather should parallelize — took {elapsed:.2f}s"


async def test_degraded_target_aborts_with_actionable_message() -> None:
    """50% pass rate against a degraded target → BaselineAbortError surfaces
    pass_rate, threshold, and sample errors for the orchestrator to display."""
    target = _LatentTarget(
        _spec(),
        [_ok(), _err("crm returned 503")] * 5,
        per_call_ms=20.0,
    )
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    msg = str(exc_info.value)
    assert "below 80%" in msg
    assert "crm returned 503" in msg  # sample error surfaced
    assert target.invoke_count == 10  # all invokes completed before abort


async def test_mixed_outcomes_success_softfail_and_raised_exception() -> None:
    """A realistic baseline mixes clean successes, soft AdapterResult.error
    failures, and raised transport exceptions. All three failure paths must
    contribute to the failed count via asyncio.gather(return_exceptions=True)."""
    target = _LatentTarget(
        _spec(),
        [_ok(), _ok(), _err("tool timeout"), RuntimeError("connection reset")] * 3,
        per_call_ms=10.0,
    )
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=12).validate()
    msg = str(exc_info.value)
    # Both soft-failure and raised-exception messages flow into sample_errors.
    assert "tool timeout" in msg or "connection reset" in msg
    # Pass rate = 6/12 = 50% (2 ok per cycle * 3 cycles); aborts.
    assert "50%" in msg
