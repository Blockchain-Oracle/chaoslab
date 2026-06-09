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
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector.target_adapters import (
    AdapterInvocation,
    AdapterResult,
    TargetAdapter,
)

_log = structlog.get_logger(__name__)


class BaselineResult(BaseModel):
    """Outcome of one ``BaselineCheck.validate()`` call.

    ``aborted`` is ``True`` iff ``pass_rate < threshold``; the corresponding
    ``BaselineAbortError`` is raised at the same time so callers don't need
    to read this field to decide whether to abort — it's surfaced for
    observability + logs only.
    """

    n: int = Field(ge=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    aborted: bool
    sample_errors: list[str] = Field(default_factory=list)


class BaselineCheck(BaseModel):
    """Steady-state-hypothesis pre-flight: run target N times without faults,
    compute pass rate, abort if ``pass_rate < threshold``.

    Boundary semantics: ``aborted = pass_rate < threshold`` — exactly 80% (or
    whatever the threshold is) does NOT abort. The orchestrator-side
    threshold knob is for the rare "known-flaky target" case where a lower
    floor is acceptable; the default 80% comes from architecture/04 §8.3.
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
        ``asyncio.gather(return_exceptions=True)`` treats raised exceptions as
        failures rather than aborting the whole baseline on one bad call.

        Shadows Pydantic v2's deprecated ``BaseModel.validate(value)`` classmethod
        intentionally — the BDD criterion calls ``BaselineCheck(...).validate()``
        as an instance method; future callers should use ``BaselineCheck.model_validate``
        for Pydantic-style schema validation (it's the v2 successor anyway).
        """
        await self.target.connect()
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
            raise BaselineAbortError(msg)
        return result

    @staticmethod
    def _tally(gathered: list[Any]) -> tuple[int, list[str]]:
        """Classify each gather outcome as pass or fail; collect error messages."""
        passed = 0
        errors: list[str] = []
        for r in gathered:
            if isinstance(r, BaseException):
                errors.append(str(r))
                continue
            if isinstance(r, AdapterResult) and r.error:
                errors.append(r.error)
                continue
            if isinstance(r, AdapterResult):
                passed += 1
        return passed, errors


__all__ = ["BaselineAbortError", "BaselineCheck", "BaselineResult"]
