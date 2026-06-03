# Story — Pre-flight baseline check (Chaos Toolkit steady-state-hypothesis pattern)

**ID:** story-5.6-preflight-baseline
**Epic:** Epic 5 — Fault injection (the 4 fault classes)
**Depends on:** story-3.1-adapter-interface (BaselineCheck calls TargetAdapter.invoke under the hood)
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, injector, fault]

---

## User story

**As a** ChaosLab orchestrator about to inject 25 faults
**I want to** run a pre-flight `BaselineCheck` that calls the target N times WITHOUT faults, computes the pass rate, and aborts if the pass rate is below 80%
**So that** ChaosLab follows the Chaos Toolkit `steady-state-hypothesis` pattern (per `architecture/01 §7 Move 5`) — if the target is already broken pre-injection the demo collapses into nonsense; the baseline guard is non-negotiable

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py` — NEW — defines `BaselineCheck` class + `BaselineResult` pydantic schema + `BaselineAbortError` custom exception. ≤180 LOC total.
- `apps/chaoslab-agent/src/chaoslab_agent/injector/__init__.py` — UPDATE — add `from .preflight import BaselineCheck, BaselineResult, BaselineAbortError` to the package re-exports
- `apps/chaoslab-agent/src/chaoslab_agent/errors.py` — UPDATE (or NEW if absent) — add `BaselineAbortError(Exception)` to the central error module so it's importable as `from chaoslab_agent.errors import BaselineAbortError`
- `apps/chaoslab-agent/tests/unit/injector/test_preflight.py` — NEW — ≥10 unit tests covering: 100% pass baseline returns BaselineResult(pass_rate=1.0, aborted=False), 50% pass baseline raises BaselineAbortError, exactly-80% pass baseline does NOT abort (boundary), 79% pass aborts, AdapterResult.error contributes to fail count, all-error baseline produces pass_rate=0 and aborts with specific message substring, n=1 supported, n=20 supported, custom threshold accepted (e.g., threshold=0.5), threshold validation rejects values outside [0.0, 1.0].
- `apps/chaoslab-agent/tests/integration/injector/test_preflight_integration.py` — NEW — ≥3 integration tests using a real (in-process) Tier 1 ADK target via the adapter — one happy-path (passes), one degraded-target (aborts), one with mixed AdapterResult outcomes.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py exists
When `grep -E "^class BaselineCheck" apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py` runs
Then exit code is 0

Given the file declares the abort error
When `grep -E "^class BaselineAbortError" apps/chaoslab-agent/src/chaoslab_agent/errors.py` runs
Then exit code is 0

Given the modules are importable
When `uv run python -c "from chaoslab_agent.injector import BaselineCheck, BaselineResult, BaselineAbortError; print('ok')"` runs
Then stdout contains "ok" and exit code is 0

Given a target whose baseline pass rate is 50% (5/10 AdapterResult with error=None, 5/10 with error set)
When `BaselineCheck(target, n=10).validate()` is awaited
Then `BaselineAbortError` is raised
And  the exception message contains the substring "below 80%"

Given a target whose baseline pass rate is 100%
When `BaselineCheck(target, n=10).validate()` is awaited
Then no exception is raised
And  the returned BaselineResult.pass_rate == 1.0
And  BaselineResult.aborted == False
And  BaselineResult.n == 10
And  BaselineResult.passed == 10

Given a target whose baseline pass rate is exactly 80% (boundary)
When `BaselineCheck(target, n=10, threshold=0.8).validate()` is awaited
Then no exception is raised (threshold is inclusive — `pass_rate >= threshold` passes)
And  BaselineResult.pass_rate == 0.8

Given a target whose baseline pass rate is 79%
When `BaselineCheck(target, n=100).validate()` is awaited
Then `BaselineAbortError` is raised

Given BaselineCheck(target, n=10, threshold=1.5) is constructed
When pydantic validates the threshold
Then pydantic.ValidationError is raised (threshold must be in [0.0, 1.0])

Given `uv run pytest apps/chaoslab-agent/tests/unit/injector/test_preflight.py -v` runs
When the test suite completes
Then ≥10 unit tests pass

Given `uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/test_preflight_integration.py -v` runs
When the integration suite completes
Then ≥3 integration tests pass

Given the source file
When `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py` runs
Then exit code is 0

Given §14 check
When `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py` runs
Then zero results appear
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# 1) Source files exist + structure
test -f apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py
grep -qE "^class BaselineCheck" apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py
grep -qE "^class BaselineAbortError" apps/chaoslab-agent/src/chaoslab_agent/errors.py
grep -qE "below 80%" apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py

# 2) Importable
uv run python -c "from chaoslab_agent.injector import BaselineCheck, BaselineResult, BaselineAbortError; print('ok')" | grep -q ok

# 3) Unit tests pass with ≥10 cases
uv run pytest apps/chaoslab-agent/tests/unit/injector/test_preflight.py -v
UNIT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/unit/injector/test_preflight.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$UNIT_COUNT" -ge 10 ] || { echo "expected ≥10 unit tests, got $UNIT_COUNT"; exit 1; }

# 4) Integration tests pass with ≥3 cases
uv run pytest -m integration apps/chaoslab-agent/tests/integration/injector/test_preflight_integration.py -v
INT_COUNT=$(uv run pytest apps/chaoslab-agent/tests/integration/injector/test_preflight_integration.py --collect-only -q 2>&1 | grep -cE "test_")
[ "$INT_COUNT" -ge 3 ] || { echo "expected ≥3 integration tests, got $INT_COUNT"; exit 1; }

# 5) 400-line guard
python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py

# 6) Lint + type-check
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py apps/chaoslab-agent/src/chaoslab_agent/errors.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py apps/chaoslab-agent/src/chaoslab_agent/errors.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py

# 7) §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py

echo "story-5.6 verification: PASS"
```

---

## Notes for coding agent

### The class shape

```python
# apps/chaoslab-agent/src/chaoslab_agent/injector/preflight.py
from __future__ import annotations
import asyncio
import structlog
from pydantic import BaseModel, Field
from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector.target_adapters import TargetAdapter, AdapterInvocation

log = structlog.get_logger(__name__)


class BaselineResult(BaseModel):
    n: int = Field(ge=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    aborted: bool
    sample_errors: list[str] = Field(default_factory=list)  # first 3 error strings


class BaselineCheck(BaseModel):
    """Steady-state-hypothesis pre-flight: run target N times without faults, compute pass rate, abort if < threshold.

    Mirrors Chaos Toolkit's steady-state-hypothesis pattern (architecture/01 §7 Move 5).
    """
    model_config = {"arbitrary_types_allowed": True}
    target: TargetAdapter
    n: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    invocation: AdapterInvocation = Field(
        default_factory=lambda: AdapterInvocation(prompt="What is the status of order 12345?")
    )

    async def validate(self) -> BaselineResult:
        await self.target.connect()
        results = await asyncio.gather(
            *(self.target.invoke(self.invocation) for _ in range(self.n)),
            return_exceptions=True,
        )
        passed = 0
        errors: list[str] = []
        for r in results:
            if isinstance(r, Exception):
                errors.append(str(r))
                continue
            if r.error:
                errors.append(r.error)
                continue
            passed += 1
        failed = self.n - passed
        pass_rate = passed / self.n
        result = BaselineResult(
            n=self.n, passed=passed, failed=failed, pass_rate=pass_rate,
            threshold=self.threshold, aborted=pass_rate < self.threshold,
            sample_errors=errors[:3],
        )
        log.info("baseline_check_complete", **result.model_dump())
        if result.aborted:
            raise BaselineAbortError(
                f"baseline pass rate {pass_rate:.0%} is below {self.threshold:.0%} "
                f"(passed={passed}/{self.n}; sample errors: {errors[:3]})"
            )
        return result
```

### Error module addition

```python
# apps/chaoslab-agent/src/chaoslab_agent/errors.py
class BaselineAbortError(RuntimeError):
    """Raised by BaselineCheck when target's pre-flight pass rate is below threshold."""
```

### Unit test pattern

```python
# apps/chaoslab-agent/tests/unit/injector/test_preflight.py
import pytest
from chaoslab_agent.injector import BaselineCheck, BaselineResult, BaselineAbortError
from chaoslab_agent.injector.target_adapters import (
    TargetAdapter, AdapterInvocation, AdapterResult, AdapterFingerprint, TargetSpec, AdapterTier,
)


class _ScriptedTarget(TargetAdapter):
    """In-test target adapter with a scripted sequence of AdapterResult outcomes.
    Lives ONLY in tests/ per §14 — never in src/."""

    def __init__(self, spec, outcomes):
        super().__init__(spec)
        self._outcomes = list(outcomes)
        self._idx = 0

    async def connect(self): self._connected = True
    async def disconnect(self): self._connected = False
    async def fingerprint(self): return AdapterFingerprint(tier=self.spec.tier)

    async def invoke(self, invocation):
        result = self._outcomes[self._idx % len(self._outcomes)]
        self._idx += 1
        return result


def _ok() -> AdapterResult:
    return AdapterResult(response="ok", duration_ms=10.0, error=None)


def _err(msg: str = "tool failure") -> AdapterResult:
    return AdapterResult(response="", duration_ms=10.0, error=msg)


@pytest.mark.asyncio
async def test_50pct_baseline_aborts_with_below_80pct_message() -> None:
    spec = TargetSpec(tier=AdapterTier.TIER1_ADK, url="http://localhost:8001")
    target = _ScriptedTarget(spec, [_ok(), _err(), _ok(), _err(), _ok(), _err(), _ok(), _err(), _ok(), _err()])
    check = BaselineCheck(target=target, n=10)
    with pytest.raises(BaselineAbortError) as ei:
        await check.validate()
    assert "below 80%" in str(ei.value)


@pytest.mark.asyncio
async def test_100pct_baseline_passes() -> None:
    spec = TargetSpec(tier=AdapterTier.TIER1_ADK, url="http://localhost:8001")
    target = _ScriptedTarget(spec, [_ok()] * 10)
    result = await BaselineCheck(target=target, n=10).validate()
    assert result.pass_rate == 1.0
    assert result.aborted is False
    assert result.passed == 10


@pytest.mark.asyncio
async def test_80pct_boundary_inclusive_does_not_abort() -> None:
    spec = TargetSpec(tier=AdapterTier.TIER1_ADK, url="http://localhost:8001")
    target = _ScriptedTarget(spec, [_ok()] * 8 + [_err()] * 2)
    result = await BaselineCheck(target=target, n=10, threshold=0.8).validate()
    assert result.pass_rate == 0.8
    assert result.aborted is False


def test_threshold_above_1_rejected_by_pydantic() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BaselineCheck(target=..., n=10, threshold=1.5)
```

### Architecture context

- **`architecture/01 §7 Move 5` (Chaos Toolkit steady-state-hypothesis):** the pre-flight is the SINGLE biggest borrowable idea from Chaos Toolkit. Without it the demo collapses ("the agent looks broken under attack — but it was already broken").
- **`architecture.md` §"Data flow" step 4:** the orchestrator MUST call `BaselineCheck` before phase=attack. If the check aborts, the orchestrator surfaces the error to the demo UI with "target is already broken; cannot run chaos test" — never proceeds.
- **80% threshold:** per `architecture/04 §8.3` and `architecture.md` §"Data flow" — fixed default. Configurable for the rare case a flaky target is acceptable (e.g., known-flaky tool the user wants to test resilience against).
- **`asyncio.gather` for parallelism:** the baseline is non-attack — N parallel calls is safe + fast. With `n=10` against a real ADK target, baseline completes in ~3-5 seconds total.
- **`return_exceptions=True`:** AdapterAdapter.invoke can raise (network errors, JSON decode, etc.) — treat raised exceptions as failures rather than letting one bad call abort the whole baseline.

### Known pitfalls

- **`arbitrary_types_allowed=True`** on the pydantic config because `TargetAdapter` is an ABC, not a Pydantic BaseModel.
- **`sample_errors=errors[:3]`** keeps the error context for debugging without exploding the result payload. Truncate per-error string to ~200 chars in a future refinement if logs balloon (out of scope for this story).
- **Boundary semantics:** `aborted = pass_rate < threshold` means EXACTLY 80% does NOT abort. The BDD criterion verifies this — be careful not to flip it to `<=`.
- **DO NOT** call the target through faults during the baseline. The Injector sub-agent (story 5.7) wires baseline BEFORE attaching any callbacks; this story's `BaselineCheck` simply assumes the target it receives has no faults installed.
- **Logging:** use `structlog.get_logger(__name__)` not `print()`. The structlog setup from story 4.5 propagates Phoenix trace IDs into the log line via `_add_phoenix_trace_id`.
- **Cross-reference:** `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/01-reference-implementations.md` §3.4 (Chaos Toolkit steady-state-hypothesis pattern, full template) + §7 Move 5. `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-006 (vendoring context) + "Data flow" step 4 (the baseline gate's place in the run lifecycle).
