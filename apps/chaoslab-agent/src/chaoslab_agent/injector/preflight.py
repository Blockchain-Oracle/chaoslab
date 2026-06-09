"""Pre-flight baseline check (Chaos Toolkit steady-state-hypothesis pattern).

Run the target N times WITHOUT faults, compute the pass rate, and abort the
chaos run if pass_rate < threshold. Mirrors the Chaos Toolkit pattern
(architecture/01 §7 Move 5 + reference-implementations §3.4). Without this
gate, the fault-injection demo collapses into nonsense — "the target looks
broken under attack — but it was already broken."

The 80% default threshold comes from architecture/04 §8.3 + the data-flow
spec in architecture.md. The orchestrator (story 5.7 / 4.2) calls
``BaselineCheck.validate()`` BEFORE attaching any fault callbacks.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, model_validator

from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector.target_adapters import (
    AdapterInvocation,
    AdapterResult,
    TargetAdapter,
)

_log = structlog.get_logger(__name__)

# Credential-shape redaction applied to every error string before it lands in
# `BaselineResult.sample_errors` or the `BaselineAbortError` message.
# ADR-005 forbids secrets in error surfaces; the upstream adapter contract
# does NOT statically guarantee that adapter errors stay sanitized (some httpx
# / framework errors interpolate URLs with embedded auth, e.g.
# `https://user:token@host/...`). Defense-in-depth — best-effort but cheap.
_PASS_RATE_TOLERANCE = 1e-9
_CREDENTIAL_PATTERNS = re.compile(
    r"(?ix)"
    r"(?:bearer\s+[A-Za-z0-9._\-/+=]+)"
    r"|(?:api[_-]?key\s*[=:]\s*[A-Za-z0-9._\-]+)"
    r"|(?:authorization\s*[:=]\s*[A-Za-z0-9._\-/+=\s]+)"
    r"|(?:sk-[A-Za-z0-9]{20,})"
    r"|(?:AIza[0-9A-Za-z\-_]{35})"
    r"|(?://[^/@\s]+:[^/@\s]+@)"
)


def _redact_credentials(s: str) -> str:
    return _CREDENTIAL_PATTERNS.sub("***", s)


class BaselineResult(BaseModel):
    """Outcome of one ``BaselineCheck.validate()`` call — an immutable snapshot.

    Cross-field invariants enforced by ``@model_validator``:

    - ``passed + failed == n``
    - ``pass_rate == passed / n`` (within float tolerance)
    - ``aborted == (pass_rate < threshold)``

    The ``aborted`` field is observability-only; callers don't need to read
    it to decide whether to abort — the corresponding ``BaselineAbortError``
    is raised at the same time. Carried on the result for downstream
    report generation + structured logging.
    """

    model_config = ConfigDict(frozen=True)

    n: int = Field(ge=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    aborted: bool
    sample_errors: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def _enforce_cross_field_invariants(self) -> BaselineResult:
        if self.passed + self.failed != self.n:
            msg = (
                f"BaselineResult invariant violated: passed({self.passed}) + "
                f"failed({self.failed}) != n({self.n})"
            )
            raise ValueError(msg)
        expected_rate = self.passed / self.n
        if abs(self.pass_rate - expected_rate) > _PASS_RATE_TOLERANCE:
            msg = (
                f"BaselineResult invariant violated: pass_rate({self.pass_rate}) "
                f"!= passed/n({expected_rate})"
            )
            raise ValueError(msg)
        if self.aborted != (self.pass_rate < self.threshold):
            msg = (
                f"BaselineResult invariant violated: aborted({self.aborted}) "
                f"inconsistent with pass_rate({self.pass_rate}) < threshold({self.threshold})"
            )
            raise ValueError(msg)
        return self


class BaselineCheck(BaseModel):
    """Steady-state-hypothesis pre-flight: run target N times without faults,
    compute pass rate, abort if ``pass_rate < threshold``.

    Boundary semantics: ``aborted = pass_rate < threshold`` — exactly 80% (or
    whatever the threshold is) does NOT abort. The orchestrator-side
    threshold knob is for the rare "known-flaky target" case where a lower
    floor is acceptable; the default 80% comes from architecture/04 §8.3.

    Resource lifecycle: ``validate()`` calls ``connect()`` at entry and
    ``disconnect()`` in a ``finally`` block — failed disconnects are logged
    but never mask the original outcome (whether that's a BaselineResult
    return or a BaselineAbortError raise).

    NOTE: ``arbitrary_types_allowed=True`` is required because
    ``TargetAdapter`` is an ABC, not a Pydantic model. This model is
    constructor-only — NOT designed for JSON round-trip; persist
    ``TargetSpec`` and resolve the adapter via a factory if you need that.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: TargetAdapter
    n: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    invocation: AdapterInvocation = Field(
        default_factory=lambda: AdapterInvocation(prompt="What is the status of order 12345?")
    )

    async def validate(self) -> BaselineResult:  # ty: ignore[invalid-method-override]
        """Run N parallel invocations and return the baseline outcome.

        Raises ``BaselineAbortError`` if the pass rate is below the threshold.
        Raised exceptions from individual invokes are captured via
        ``asyncio.gather(return_exceptions=True)`` and counted as failures —
        EXCEPT ``CancelledError``, which signals event-loop shutdown and
        must propagate (an auditor that reports "your target had 0% pass
        rate" when actually we were SIGTERMed mid-flight would lie to the
        regulator).

        Shadows Pydantic v2's deprecated ``BaseModel.validate(value)``
        classmethod intentionally — the BDD criterion calls
        ``BaselineCheck(...).validate()`` as an instance method. Future
        callers wanting Pydantic-style schema validation use
        ``BaselineCheck.model_validate``.
        """
        await self.target.connect()
        try:
            gathered: list[Any] = await asyncio.gather(
                *(self.target.invoke(self.invocation) for _ in range(self.n)),
                return_exceptions=True,
            )
            passed, errors = self._tally(gathered)
            failed = self.n - passed
            pass_rate = passed / self.n
            aborted = pass_rate < self.threshold

            result = BaselineResult(
                n=self.n,
                passed=passed,
                failed=failed,
                pass_rate=pass_rate,
                threshold=self.threshold,
                aborted=aborted,
                sample_errors=errors[:3],
            )
            _log.info("baseline_check_complete", **result.model_dump())

            if aborted:
                msg = (
                    f"baseline pass rate {pass_rate:.0%} is below {self.threshold:.0%} "
                    f"(passed={passed}/{self.n}; sample errors: {errors[:3]})"
                )
                raise BaselineAbortError(msg, result=result)
            return result
        finally:
            try:
                await self.target.disconnect()
            except Exception as disconnect_err:
                # Never let a disconnect failure mask the original outcome.
                _log.warning("baseline_disconnect_failed", error=str(disconnect_err))

    @staticmethod
    def _tally(gathered: list[Any]) -> tuple[int, list[str]]:
        """Classify each gather outcome.

        Raises ``CancelledError`` immediately if any task was cancelled —
        cancellation signals event-loop shutdown, NOT target failure.
        Raises ``RuntimeError`` if the adapter returned a non-AdapterResult
        value (contract violation in our own code per
        ``TargetAdapter.invoke``'s frozen return type).
        """
        passed = 0
        errors: list[str] = []
        for i, r in enumerate(gathered):
            if isinstance(r, asyncio.CancelledError):
                raise r
            if isinstance(r, BaseException):
                errors.append(_redact_credentials(str(r)))
                continue
            if isinstance(r, AdapterResult):
                if r.error:
                    errors.append(_redact_credentials(r.error))
                else:
                    passed += 1
                continue
            msg = (
                f"TargetAdapter.invoke contract violation at index {i}: "
                f"expected AdapterResult, got {type(r).__name__}"
            )
            raise RuntimeError(msg)
        return passed, errors


__all__ = ["BaselineAbortError", "BaselineCheck", "BaselineResult"]
