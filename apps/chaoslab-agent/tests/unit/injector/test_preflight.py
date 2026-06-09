"""Unit tests for BaselineCheck (story-5.6 preflight baseline).

The Chaos Toolkit "steady-state-hypothesis" gate — if the target's pre-fault
pass rate is below threshold, abort the entire chaos run with a loud error
rather than corrupting the resilience signal with a baseline that's
already-broken (architecture/01 §7 Move 5).

Test doubles (`_ScriptedTarget`, `_ok`, `_err`) live in tests/ per §14.
"""

from __future__ import annotations

import pytest
from pydantic import HttpUrl, ValidationError

from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector import BaselineCheck, BaselineResult
from chaoslab_agent.injector.target_adapters import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)


def _spec() -> TargetSpec:
    return TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl("http://localhost:8001/"))


def _ok() -> AdapterResult:
    return AdapterResult(response="ok", duration_ms=10.0, error=None)


def _err(msg: str = "tool failure") -> AdapterResult:
    return AdapterResult(response="", duration_ms=10.0, error=msg)


class _ScriptedTarget(TargetAdapter):
    """In-test adapter cycling through a scripted sequence of AdapterResult values.

    Tests can also raise via the special sentinel `_RAISE` — see
    test_raised_exception_is_treated_as_failure.
    """

    def __init__(self, spec: TargetSpec, outcomes: list[AdapterResult | Exception]) -> None:
        super().__init__(spec)
        self._outcomes = list(outcomes)
        self._idx = 0
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def fingerprint(self) -> AdapterFingerprint:
        return AdapterFingerprint(tier=self.spec.tier)

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        outcome = self._outcomes[self._idx % len(self._outcomes)]
        self._idx += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ---------------------------------------------------------------------------
# Pass-rate behavior — the core invariant.
# ---------------------------------------------------------------------------


async def test_100pct_baseline_passes_and_returns_pass_rate_one() -> None:
    target = _ScriptedTarget(_spec(), [_ok()] * 10)
    result = await BaselineCheck(target=target, n=10).validate()
    assert isinstance(result, BaselineResult)
    assert result.pass_rate == 1.0
    assert result.aborted is False
    assert result.passed == 10
    assert result.failed == 0
    assert result.n == 10


async def test_50pct_baseline_aborts_with_below_80pct_message() -> None:
    target = _ScriptedTarget(_spec(), [_ok(), _err()] * 5)
    check = BaselineCheck(target=target, n=10)
    with pytest.raises(BaselineAbortError) as exc_info:
        await check.validate()
    assert "below 80%" in str(exc_info.value)


async def test_exactly_80pct_boundary_does_not_abort() -> None:
    """The boundary is INCLUSIVE: `pass_rate >= threshold` passes.

    BDD line 62-65 — verifies the implementation didn't flip `<` to `<=`.
    """
    target = _ScriptedTarget(_spec(), [_ok()] * 8 + [_err()] * 2)
    result = await BaselineCheck(target=target, n=10, threshold=0.8).validate()
    assert result.pass_rate == 0.8
    assert result.aborted is False


async def test_79pct_pass_rate_aborts() -> None:
    """79% < 80% threshold → abort."""
    outcomes: list[AdapterResult | Exception] = [_ok()] * 79 + [_err()] * 21
    target = _ScriptedTarget(_spec(), outcomes)
    with pytest.raises(BaselineAbortError):
        await BaselineCheck(target=target, n=100).validate()


async def test_adapter_result_with_error_field_counts_as_failure() -> None:
    """Soft-failure semantics: AdapterResult.error set → failure."""
    target = _ScriptedTarget(_spec(), [_err("tool denied request")] * 10)
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    # The sample errors should reference the underlying error message
    assert "tool denied request" in str(exc_info.value)


async def test_all_error_baseline_aborts_with_zero_pass_rate() -> None:
    target = _ScriptedTarget(_spec(), [_err()] * 10)
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    # pass_rate=0.0 == 0%
    assert "0%" in str(exc_info.value) or "below 80%" in str(exc_info.value)


async def test_raised_exception_is_treated_as_failure() -> None:
    """asyncio.gather(return_exceptions=True) → raised exceptions count as failure
    rather than aborting the whole baseline.
    """
    outcomes: list[AdapterResult | Exception] = [_ok()] * 5 + [
        RuntimeError("network error") for _ in range(5)
    ]
    target = _ScriptedTarget(_spec(), outcomes)
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    # The raised exception's message survives into the sample errors
    assert "network error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# n / threshold knobs.
# ---------------------------------------------------------------------------


async def test_n_equals_one_supported() -> None:
    target = _ScriptedTarget(_spec(), [_ok()])
    result = await BaselineCheck(target=target, n=1).validate()
    assert result.n == 1
    assert result.passed == 1
    assert result.pass_rate == 1.0


async def test_n_equals_twenty_supported() -> None:
    target = _ScriptedTarget(_spec(), [_ok()] * 20)
    result = await BaselineCheck(target=target, n=20).validate()
    assert result.n == 20
    assert result.passed == 20


async def test_custom_threshold_below_default_lets_50pct_pass() -> None:
    """threshold=0.5 → 50% pass rate is acceptable, no abort."""
    target = _ScriptedTarget(_spec(), [_ok(), _err()] * 5)
    result = await BaselineCheck(target=target, n=10, threshold=0.5).validate()
    assert result.pass_rate == 0.5
    assert result.aborted is False
    assert result.threshold == 0.5


def test_threshold_above_one_rejected_by_pydantic() -> None:
    target = _ScriptedTarget(_spec(), [_ok()])
    with pytest.raises(ValidationError):
        BaselineCheck(target=target, n=10, threshold=1.5)


def test_threshold_below_zero_rejected_by_pydantic() -> None:
    target = _ScriptedTarget(_spec(), [_ok()])
    with pytest.raises(ValidationError):
        BaselineCheck(target=target, n=10, threshold=-0.1)


def test_n_below_one_rejected_by_pydantic() -> None:
    target = _ScriptedTarget(_spec(), [_ok()])
    with pytest.raises(ValidationError):
        BaselineCheck(target=target, n=0)


# ---------------------------------------------------------------------------
# Result shape + sample_errors truncation.
# ---------------------------------------------------------------------------


async def test_sample_errors_truncated_to_first_three() -> None:
    """When more than 3 errors occur, only the first 3 land in the abort message
    (per spec: ``sample_errors=errors[:3]``)."""
    target = _ScriptedTarget(
        _spec(),
        [_err(f"distinctive-err-{i}") for i in range(10)],
    )
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    msg = str(exc_info.value)
    assert "distinctive-err-0" in msg
    assert "distinctive-err-2" in msg
    # 4th error must NOT appear — confirms the [:3] truncation.
    assert "distinctive-err-3" not in msg
