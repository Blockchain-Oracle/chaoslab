"""Unit tests for BaselineCheck (story-5.6 preflight baseline).

The Chaos Toolkit "steady-state-hypothesis" gate — if the target's pre-fault
pass rate is below threshold, abort the entire chaos run with a loud error
rather than corrupting the resilience signal with a baseline that's
already-broken (architecture/01 §7 Move 5).

Test doubles (`_ScriptedTarget`, `_ok`, `_err`) live in tests/ per §14.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import HttpUrl, ValidationError

from phoenix_audit_agent.errors import BaselineAbortError
from phoenix_audit_agent.injector import BaselineCheck, BaselineResult
from phoenix_audit_agent.injector.target_adapters import (
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

    def __init__(
        self,
        spec: TargetSpec,
        outcomes: Sequence[AdapterResult | BaseException],
    ) -> None:
        super().__init__(spec)
        self._outcomes = list(outcomes)
        self._idx = 0
        self._connected = False
        self.disconnect_count = 0

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self.disconnect_count += 1

    async def fingerprint(self) -> AdapterFingerprint:
        return AdapterFingerprint(tier=self.spec.tier)

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        outcome = self._outcomes[self._idx % len(self._outcomes)]
        self._idx += 1
        if isinstance(outcome, BaseException):
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
    # Happy path must NOT carry stale errors — test-analyzer nice-to-have.
    assert result.sample_errors == []


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
    outcomes: list[AdapterResult | BaseException] = [_ok()] * 79 + [_err()] * 21
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
    outcomes: list[AdapterResult | BaseException] = [_ok()] * 5 + [
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


# ---------------------------------------------------------------------------
# Round-2 fixes for the 4-reviewer pass on PR #44.
# ---------------------------------------------------------------------------


async def test_disconnect_is_called_on_happy_path() -> None:
    """BLOCKING-1: validate() must release the adapter resources after success."""
    target = _ScriptedTarget(_spec(), [_ok()] * 10)
    await BaselineCheck(target=target, n=10).validate()
    assert target.disconnect_count == 1


async def test_disconnect_is_called_on_abort_path() -> None:
    """BLOCKING-1: validate() must release resources even when raising BaselineAbortError."""
    target = _ScriptedTarget(_spec(), [_err()] * 10)
    with pytest.raises(BaselineAbortError):
        await BaselineCheck(target=target, n=10).validate()
    assert target.disconnect_count == 1


async def test_disconnect_is_called_when_gather_raises_unhandled() -> None:
    """BLOCKING-1: even when the gather body raises (e.g. _tally rejects an
    illegal adapter result), disconnect() must still fire."""

    class _BrokenTarget(TargetAdapter):
        def __init__(self, spec: TargetSpec) -> None:
            super().__init__(spec)
            self.disconnect_count = 0

        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            self.disconnect_count += 1

        async def fingerprint(self) -> AdapterFingerprint:
            return AdapterFingerprint(tier=self.spec.tier)

        async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
            return "this is not an AdapterResult"  # ty: ignore[invalid-return-type]

    target = _BrokenTarget(_spec())
    with pytest.raises(RuntimeError, match=r"contract violation"):
        await BaselineCheck(target=target, n=10).validate()
    assert target.disconnect_count == 1


async def test_cancelled_error_is_reraised_not_classified_as_failure() -> None:
    """BLOCKING-2: a CancelledError during invoke must propagate.

    Auditor producing a regulator-facing "your target has 0% pass rate"
    verdict when the auditor was actually SIGTERMed mid-flight would lie
    to the regulator. Treat cancellation as control flow, not failure.
    """
    import asyncio as _asyncio

    target = _ScriptedTarget(
        _spec(),
        [_ok(), _asyncio.CancelledError()] + [_ok()] * 8,
    )
    with pytest.raises(_asyncio.CancelledError):
        await BaselineCheck(target=target, n=10).validate()
    # Disconnect must still fire even when cancellation propagates.
    assert target.disconnect_count == 1


async def test_contract_violating_adapter_result_raises_runtime_error() -> None:
    """BLOCKING-3: an adapter that returns non-AdapterResult / non-Exception
    is a contract violation in OUR code — raise loudly rather than silently
    counting as neither pass nor fail."""

    class _BadAdapter(TargetAdapter):
        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

        async def fingerprint(self) -> AdapterFingerprint:
            return AdapterFingerprint(tier=self.spec.tier)

        async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
            return None  # ty: ignore[invalid-return-type]

    target = _BadAdapter(_spec())
    with pytest.raises(RuntimeError, match=r"contract violation at index \d+"):
        await BaselineCheck(target=target, n=5).validate()


async def test_credentials_redacted_in_sample_errors() -> None:
    """BLOCKING-4a: known credential shapes in adapter error strings are
    redacted before reaching BaselineResult.sample_errors or the abort
    message (ADR-005)."""
    # These are test fixtures, not real secrets — built to match the
    # redaction regex shapes (Bearer, api_key=, AIza*, sk-*, user:pass@).
    leaky_errors = [
        _err("401 from https://user:pretend-pw-xyz@crm.example.com/orders"),  # gitleaks:allow
        _err("api_key=AIzaSyFAKE-TEST-VALUE-FOR-CI-NOT-REAL-001234 invalid"),  # gitleaks:allow
        _err("Bearer sk-FAKE-TEST-VALUE-FOR-CI-NOT-REAL-001234 expired"),  # gitleaks:allow
        _err("crm error"),
        _err("network down"),
    ]
    target = _ScriptedTarget(_spec(), leaky_errors * 2)
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    msg = str(exc_info.value)
    assert "pretend-pw-xyz" not in msg
    assert "AIzaSyFAKE" not in msg
    assert "sk-FAKE" not in msg
    # Sentinel that redaction actually happened
    assert "***" in msg


async def test_baseline_abort_error_carries_structured_result() -> None:
    """test-analyzer + type-design: the exception carries the BaselineResult
    so the orchestrator can include the full snapshot in the audit report
    without parsing the message string."""
    target = _ScriptedTarget(_spec(), [_err()] * 10)
    with pytest.raises(BaselineAbortError) as exc_info:
        await BaselineCheck(target=target, n=10).validate()
    result = exc_info.value.result
    assert isinstance(result, BaselineResult)
    assert result.pass_rate == 0.0
    assert result.aborted is True
    assert result.n == 10
    assert result.passed == 0


# ---------------------------------------------------------------------------
# BaselineResult cross-field invariant enforcement (type-design).
# ---------------------------------------------------------------------------


def test_baseline_result_rejects_passed_plus_failed_not_equal_n() -> None:
    with pytest.raises(ValidationError, match=r"passed.*failed.*!= n"):
        BaselineResult(
            n=10,
            passed=7,
            failed=2,  # 7 + 2 != 10
            pass_rate=0.7,
            threshold=0.8,
            aborted=True,
            sample_errors=[],
        )


def test_baseline_result_rejects_inconsistent_pass_rate() -> None:
    with pytest.raises(ValidationError, match=r"pass_rate.*!= passed/n"):
        BaselineResult(
            n=10,
            passed=5,
            failed=5,
            pass_rate=0.8,  # inconsistent — should be 0.5
            threshold=0.8,
            aborted=False,
            sample_errors=[],
        )


def test_baseline_result_rejects_inconsistent_aborted_flag() -> None:
    with pytest.raises(ValidationError, match=r"aborted.*inconsistent"):
        BaselineResult(
            n=10,
            passed=5,
            failed=5,
            pass_rate=0.5,
            threshold=0.8,
            aborted=False,  # 0.5 < 0.8 so aborted should be True
            sample_errors=[],
        )


def test_baseline_result_is_frozen_immutable_after_construction() -> None:
    result = BaselineResult(
        n=10,
        passed=10,
        failed=0,
        pass_rate=1.0,
        threshold=0.8,
        aborted=False,
        sample_errors=[],
    )
    with pytest.raises(ValidationError):
        result.aborted = True  # type: ignore[misc]


def test_baseline_result_rejects_more_than_three_sample_errors() -> None:
    with pytest.raises(ValidationError):
        BaselineResult(
            n=10,
            passed=0,
            failed=10,
            pass_rate=0.0,
            threshold=0.8,
            aborted=True,
            sample_errors=["a", "b", "c", "d"],  # 4 > max_length=3
        )
