"""Injector — orchestrator over the 4 fault classes + BaselineCheck.

Two surfaces in this module:

1. ``build_injector_agent()``: factory returning the ADK ``LlmAgent`` that the
   orchestrator's ``SequentialAgent`` consumes. Currently ships a STUB
   instruction; a real LlmAgent body lands when Epic 5 + Epic 6 wire the
   closed-loop demo.

2. ``Injector`` Pydantic class: the actual fault-injection orchestrator.
   Runs ``BaselineCheck(n=5)`` first; if it passes, executes
   ``4 x runs_per_fault`` attacks (default 24), cycling through the four
   fault classes and capturing each ``AttackResult`` into the shared
   ``InjectorState`` the Judge sub-agent reads.

Per-fault installation surfaces (architecture/04 §8):

- F1 ``MalformedToolOutputFault``  → ``agent.before_tool_callback``
- F2 ``PromptInjectionFault``      → ``agent.before_model_callback``
- F3 ``ContextPoisoningFault``     → ``fault.install(agent)`` (covers both
  retriever_insert and history_insert via S5.4's install() entry point)
- F4 ``LatencySpikeFault``         → ``agent.before_tool_callback``

Attacks run SEQUENTIALLY (not ``asyncio.gather``) because fault installations
mutate target state; parallel installs would race on the callback slots.

Resource lifecycle: ``Injector.run()`` does ONE ``target.connect()`` at the
top of the attack phase (BaselineCheck owns its own connect/disconnect
internally) and ONE ``target.disconnect()`` in the outer finally. Per-attack
no longer connects — the ADK adapter is idempotent but Tier-2/3 adapters
may not be, so we don't rely on per-call idempotency.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal, assert_never

import structlog
from pydantic import BaseModel, ConfigDict, Field, computed_field

from phoenix_audit_agent.adk_types import LlmAgent
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.errors import BaselineAbortError
from phoenix_audit_agent.injector.faults import (
    ContextPoisoningFault,
    LatencySpikeFault,
    MalformedToolOutputFault,
    PromptInjectionFault,
)
from phoenix_audit_agent.injector.preflight import BaselineCheck
from phoenix_audit_agent.injector.target_adapters import (
    AdapterInvocation,
    TargetAdapter,
)

_log = structlog.get_logger(__name__)

INJECTOR_NAME = "Injector"
INJECTOR_OUTPUT_KEY = "injector_result"

_DESCRIPTION = (
    "Selects a fault class, configures the target adapter, invokes the target, captures the span"
)
# `STUB:` prefix is the §14 carve-out documented in story-4.2 — the
# orchestrator §14 grep allows this literal prefix inside instruction strings
# (data, not code).
_INSTRUCTION = (
    "STUB: emit a JSON object with keys ['fault_class', 'span_id', 'pass']. "
    "Stub-mode response is acceptable."
)

FaultClass = Literal[
    "malformed_tool_output",
    "prompt_injection",
    "context_poisoning",
    "latency_spike",
]
_FAULT_CLASSES: tuple[FaultClass, ...] = (
    "malformed_tool_output",
    "prompt_injection",
    "context_poisoning",
    "latency_spike",
)
_BASELINE_N = 5
_DEFAULT_RUNS_PER_FAULT = 6


def build_injector_agent() -> LlmAgent:
    """Construct the Injector LlmAgent for the SequentialAgent pipeline."""
    return LlmAgent(
        name=INJECTOR_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=INJECTOR_OUTPUT_KEY,
    )


class AttackRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_idx: int = Field(ge=0)
    fault_class: FaultClass
    variant_idx: int = Field(ge=0)


class AttackResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_idx: int = Field(ge=0)
    fault_class: FaultClass
    span_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    status: Literal["ok", "error", "timeout"]
    duration_ms: float = Field(ge=0.0)
    span_attributes: dict[str, Any] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InjectorState(BaseModel):
    """Shared state the Judge sub-agent reads after Injector.run() returns.

    ``total_attacks`` is a computed property over ``attack_results`` rather
    than a stored field — eliminates the redundant-state desync vector
    where ``record_attack`` could fail to increment a counter.
    """

    baseline_passed: bool = False
    baseline_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    attack_results: list[AttackResult] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_attacks(self) -> int:
        return len(self.attack_results)

    def record_attack(self, result: AttackResult) -> None:
        self.attack_results.append(result)

    def fault_breakdown(self) -> dict[FaultClass, int]:
        breakdown: dict[FaultClass, int] = {}
        for r in self.attack_results:
            breakdown[r.fault_class] = breakdown.get(r.fault_class, 0) + 1
        return breakdown


# Fault factories. Each cycles through documented variants for the class.
_F1_MODES = ("invalid_json", "missing_required_field", "type_mismatch", "exception")
_F2_ATTACKS = (
    "instruction_override",
    "role_hijacking",
    "payload_smuggling",
    "indirect_injection",
)
_F3_VARIANTS = (
    ("retriever_insert", 0),
    ("history_insert", 0),
    ("retriever_insert", 1),
    ("history_insert", 1),
    ("retriever_insert", 2),
    ("history_insert", 2),
)
# F4 variants are delay-only because the timeout half of the fault requires
# wiring ``LatencySpikeFault.httpx_transport()`` into the target's httpx
# client — that requires adapter cooperation (rebuilding the inner
# transport) which the TargetAdapter ABC does not expose. The full
# timeout-firing demo is deferred. Variant configs here only exercise the
# asyncio.sleep before_tool_callback path; timeout values are recorded as
# span attrs for completeness but won't fire as ReadTimeout.
_F4_VARIANTS = (
    (100, 5000),
    (300, 5000),
    (500, 5000),
    (1000, 5000),
    (200, 5000),
    (400, 5000),
)


def _build_f1(variant_idx: int) -> MalformedToolOutputFault:
    mode = _F1_MODES[variant_idx % len(_F1_MODES)]
    return MalformedToolOutputFault(mode=mode)  # type: ignore[arg-type]


def _build_f2(variant_idx: int) -> PromptInjectionFault:
    attack = _F2_ATTACKS[variant_idx % len(_F2_ATTACKS)]
    return PromptInjectionFault(attack=attack)  # type: ignore[arg-type]


def _build_f3(variant_idx: int) -> ContextPoisoningFault:
    mode, poison_idx = _F3_VARIANTS[variant_idx % len(_F3_VARIANTS)]
    return ContextPoisoningFault(mode=mode, poison_idx=poison_idx)  # type: ignore[arg-type]


def _build_f4(variant_idx: int) -> LatencySpikeFault:
    delay_ms, timeout_ms = _F4_VARIANTS[variant_idx % len(_F4_VARIANTS)]
    return LatencySpikeFault(delay_ms=delay_ms, timeout_ms=timeout_ms)


def _install_callback_tool(agent: Any, fault: Any) -> None:
    agent.before_tool_callback = fault.as_callback()


def _uninstall_callback_tool(agent: Any) -> None:
    agent.before_tool_callback = None


def _install_callback_model(agent: Any, fault: Any) -> None:
    agent.before_model_callback = fault.as_callback()


def _uninstall_callback_model(agent: Any) -> None:
    agent.before_model_callback = None


def _install_f3(agent: Any, fault: ContextPoisoningFault) -> None:
    """F3 has two installation surfaces depending on mode."""
    fault.install(agent)


def _uninstall_f3(agent: Any) -> None:
    # Sentinel removal is enough — the patched run_async closure is idempotent
    # on re-install via context_poisoning's own _PATCHED_SENTINEL guard.
    if hasattr(agent, "__dict__") and "_phoenix_audit_f3_installed" in agent.__dict__:
        del agent.__dict__["_phoenix_audit_f3_installed"]
    agent.before_model_callback = None
    for tool in getattr(agent, "tools", []):
        if hasattr(tool, "__dict__") and "_phoenix_audit_f3_patched" in tool.__dict__:
            del tool.__dict__["_phoenix_audit_f3_patched"]


class Injector(BaseModel):
    """Orchestrator over the 4 fault classes + BaselineCheck.

    Workflow:
    1. ``BaselineCheck(target, n=5)`` — bail with ``BaselineAbortError`` if
       pre-injection pass rate is below 80%. The measured rate is preserved
       on the state before re-raising so the audit report carries real data,
       not the default 0.0.
    2. Build a 4 x runs_per_fault plan (default 24 AttackRuns).
    3. For each attack: build fault → install → invoke → uninstall →
       capture AttackResult. Sequential. Per-attack exceptions are caught
       so one bad attack doesn't kill the whole 24-attack audit — the
       failure surfaces as an error-status AttackResult, not a silent drop.
    4. Return the populated InjectorState.

    Adapter lifecycle: one ``connect()`` at entry, one ``disconnect()`` in
    the outer finally. Per-attack code does not re-connect.

    NOTE: ``arbitrary_types_allowed=True`` is required because
    ``TargetAdapter`` is an ABC. This model is constructor-only.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: TargetAdapter
    state: InjectorState
    prompt: str = Field(min_length=1)
    runs_per_fault: int = Field(default=_DEFAULT_RUNS_PER_FAULT, ge=1, le=20)
    # Progress hooks — the live-audit SSE bridge. Awaited inline, so a slow
    # hook slows the audit; emitters must be queue-puts, not network calls.
    on_attack_start: Callable[[AttackRun], Awaitable[None]] | None = None
    on_attack_end: Callable[[AttackResult], Awaitable[None]] | None = None

    async def run(self) -> InjectorState:
        await self._run_baseline()
        try:
            await self.target.connect()
            plan = self._build_plan()
            for attack in plan:
                if self.on_attack_start is not None:
                    await self._fire_hook(self.on_attack_start, attack, hook_name="start")
                recorded_before = self.state.total_attacks
                await self._run_one_attack(attack)
                # Fire the end hook only for the result THIS attack recorded —
                # never re-announce a previous attack's tail.
                if self.on_attack_end is not None and self.state.total_attacks > recorded_before:
                    await self._fire_hook(
                        self.on_attack_end, self.state.attack_results[-1], hook_name="end"
                    )
            return self.state
        finally:
            try:
                await self.target.disconnect()
            except Exception as disconnect_err:
                # Never let disconnect failure mask the original outcome.
                _log.warning(
                    "injector_disconnect_failed",
                    exc_type=type(disconnect_err).__name__,
                    error=str(disconnect_err),
                    exc_info=True,
                )

    @staticmethod
    async def _fire_hook(
        hook: Callable[[Any], Awaitable[None]], arg: Any, *, hook_name: str = ""
    ) -> None:
        """Invoke a progress hook without letting it abort the audit.

        Hooks are UI telemetry — an SSE-plumbing exception must never kill a
        real audit run mid-flight. Failures are logged loudly, never silent.
        """
        try:
            await hook(arg)
        except Exception as hook_err:
            _log.error(
                "attack_hook_failed",
                hook=hook_name,
                exc_type=type(hook_err).__name__,
                error=str(hook_err),
                exc_info=True,
            )

    async def _run_baseline(self) -> None:
        """BaselineCheck owns its own connect/disconnect lifecycle.

        On abort, preserves the measured pass rate on the state so downstream
        report rendering reflects what was actually observed rather than the
        default 0.0.
        """
        try:
            baseline = await BaselineCheck(target=self.target, n=_BASELINE_N).validate()
        except BaselineAbortError as e:
            self.state.baseline_passed = False
            if e.result is not None:
                self.state.baseline_pass_rate = e.result.pass_rate
            raise
        self.state.baseline_passed = not baseline.aborted
        self.state.baseline_pass_rate = baseline.pass_rate

    def _build_plan(self) -> list[AttackRun]:
        plan: list[AttackRun] = []
        run_idx = 0
        for fault_class in _FAULT_CLASSES:
            for variant_idx in range(self.runs_per_fault):
                plan.append(
                    AttackRun(
                        run_idx=run_idx,
                        fault_class=fault_class,
                        variant_idx=variant_idx,
                    )
                )
                run_idx += 1
        return plan

    async def _run_one_attack(self, attack: AttackRun) -> None:
        # target.agent is Tier-1-in-process-specific; Tier 3 HTTP black-box
        # adapters install faults differently and won't satisfy this access.
        agent = self.target.agent  # ty: ignore[unresolved-attribute]
        try:
            fault = self._build_fault(attack)
            self._install(attack.fault_class, agent, fault)
            try:
                response = await self.target.invoke(AdapterInvocation(prompt=self.prompt))
            finally:
                self._uninstall(attack.fault_class, agent)
            self._record(attack, response)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # One bad attack must not kill the 24-attack audit — surface as
            # an error-status AttackResult so the Judge sees the failure.
            _log.warning(
                "injector_attack_failed",
                run_idx=attack.run_idx,
                fault_class=attack.fault_class,
                exc_type=type(exc).__name__,
                exc_info=True,
            )
            self.state.record_attack(
                AttackResult(
                    run_idx=attack.run_idx,
                    fault_class=attack.fault_class,
                    span_id=f"error:{type(exc).__name__}",
                    trace_id="error:no-trace",
                    status="error",
                    duration_ms=0.0,
                    span_attributes={
                        "phoenix_audit.fault.type": attack.fault_class,
                        "phoenix_audit.fault.variant_idx": attack.variant_idx,
                        "phoenix_audit.attack.exception": type(exc).__name__,
                    },
                )
            )

    @staticmethod
    def _build_fault(attack: AttackRun) -> Any:
        if attack.fault_class == "malformed_tool_output":
            return _build_f1(attack.variant_idx)
        if attack.fault_class == "prompt_injection":
            return _build_f2(attack.variant_idx)
        if attack.fault_class == "context_poisoning":
            return _build_f3(attack.variant_idx)
        if attack.fault_class == "latency_spike":
            return _build_f4(attack.variant_idx)
        assert_never(attack.fault_class)

    @staticmethod
    def _install(fault_class: FaultClass, agent: Any, fault: Any) -> None:
        if fault_class in ("malformed_tool_output", "latency_spike"):
            _install_callback_tool(agent, fault)
        elif fault_class == "prompt_injection":
            _install_callback_model(agent, fault)
        elif fault_class == "context_poisoning":
            _install_f3(agent, fault)
        else:
            assert_never(fault_class)

    @staticmethod
    def _uninstall(fault_class: FaultClass, agent: Any) -> None:
        if fault_class in ("malformed_tool_output", "latency_spike"):
            _uninstall_callback_tool(agent)
        elif fault_class == "prompt_injection":
            _uninstall_callback_model(agent)
        elif fault_class == "context_poisoning":
            _uninstall_f3(agent)
        else:
            assert_never(fault_class)

    def _record(self, attack: AttackRun, response: Any) -> None:
        """Record an AttackResult — never silently drop on missing span info.

        Adapter regressions that drop ``span_ids`` or ``trace_id`` were
        silently invisible to the audit verdict. Surface them as
        error-status AttackResults with sentinel IDs + a structured log.
        """
        span_id = response.span_ids[0] if response.span_ids else ""
        trace_id = response.metadata.get("trace_id", "") if response.metadata else ""

        if not span_id or not trace_id:
            _log.warning(
                "injector_attack_span_missing",
                run_idx=attack.run_idx,
                fault_class=attack.fault_class,
                span_id_present=bool(span_id),
                trace_id_present=bool(trace_id),
                response_error=getattr(response, "error", None),
            )
            self.state.record_attack(
                AttackResult(
                    run_idx=attack.run_idx,
                    fault_class=attack.fault_class,
                    span_id=span_id or "missing:no-span-emitted",
                    trace_id=trace_id or "missing:no-trace-emitted",
                    status="error",
                    duration_ms=response.duration_ms,
                    span_attributes={
                        "phoenix_audit.fault.type": attack.fault_class,
                        "phoenix_audit.fault.variant_idx": attack.variant_idx,
                        "phoenix_audit.attack.span_missing": True,
                    },
                )
            )
            return

        status: Literal["ok", "error", "timeout"]
        if response.error:
            status = "timeout" if "timeout" in response.error.lower() else "error"
        else:
            status = "ok"
        self.state.record_attack(
            AttackResult(
                run_idx=attack.run_idx,
                fault_class=attack.fault_class,
                span_id=span_id,
                trace_id=trace_id,
                status=status,
                duration_ms=response.duration_ms,
                span_attributes={
                    "phoenix_audit.fault.type": attack.fault_class,
                    "phoenix_audit.fault.variant_idx": attack.variant_idx,
                },
            )
        )


__all__ = [
    "INJECTOR_NAME",
    "INJECTOR_OUTPUT_KEY",
    "AttackResult",
    "AttackRun",
    "FaultClass",
    "Injector",
    "InjectorState",
    "build_injector_agent",
]
