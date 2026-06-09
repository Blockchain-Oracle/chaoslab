"""Injector — orchestrator over the 4 fault classes + BaselineCheck (story-5.7).

Two surfaces in this module:

1. ``build_injector_agent()`` (story 4.1 / 4.2): factory returning the ADK
   ``LlmAgent`` that the orchestrator's ``SequentialAgent`` consumes. Currently
   ships a STUB instruction; a real LlmAgent body lands when Epic 5 + Epic 6
   wire the closed-loop demo.

2. ``Injector`` Pydantic class (this story): the actual fault-injection
   orchestrator. Runs ``BaselineCheck(n=5)`` first; if it passes, executes
   ``4 x runs_per_fault`` attacks (default 24), cycling through the four
   fault classes and capturing each ``AttackResult`` into the shared
   ``InjectorState`` the Judge sub-agent (Epic 6) reads.

The Injector covers steps 3-5 of architecture.md's data flow (baseline +
attack phase + span capture). Step 6 (Judge phase) reads
``state.attack_results`` to build the failure cluster set in Epic 6.

Per-fault installation surfaces (architecture/04 §8 + story-5.7 lines
319-324):

- F1 ``MalformedToolOutputFault``  → ``agent.before_tool_callback``
- F2 ``PromptInjectionFault``      → ``agent.before_model_callback``
- F3 ``ContextPoisoningFault``     → ``fault.install(agent)`` (monkey-patches
  retrievers in place for ``mode='retriever_insert'``; sets
  ``before_model_callback`` for ``mode='history_insert'``)
- F4 ``LatencySpikeFault``         → ``agent.before_tool_callback``

Attacks run SEQUENTIALLY (not ``asyncio.gather``) because fault installations
mutate target state; parallel installs would race on the callback slots.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from chaoslab_agent.adk_types import LlmAgent
from chaoslab_agent.config import get_settings
from chaoslab_agent.injector.faults import (
    ContextPoisoningFault,
    LatencySpikeFault,
    MalformedToolOutputFault,
    PromptInjectionFault,
)
from chaoslab_agent.injector.preflight import BaselineCheck
from chaoslab_agent.injector.target_adapters import (
    AdapterInvocation,
    TargetAdapter,
)

INJECTOR_NAME = "Injector"
INJECTOR_OUTPUT_KEY = "injector_result"

_DESCRIPTION = (
    "Selects a fault class, configures the target adapter, invokes the target, captures the span"
)
# `STUB:` prefix is the §14-carve-out documented in story-4.2 — the orchestrator
# §14 grep allows this literal prefix inside instruction strings (data, not code).
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
_DEFAULT_PROMPT = "What is the status of order 12345?"


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
    """One scheduled attack: which fault class, which variant, against which target."""

    run_idx: int = Field(ge=0)
    fault_class: FaultClass
    variant_idx: int = Field(ge=0)
    fault_config: dict[str, Any] = Field(default_factory=dict)


class AttackResult(BaseModel):
    """Outcome of one AttackRun, captured from the target's emitted span."""

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
    """Shared state the Judge sub-agent reads after Injector.run() returns."""

    baseline_passed: bool = False
    baseline_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    total_attacks: int = 0
    attack_results: list[AttackResult] = Field(default_factory=list)

    def record_attack(self, result: AttackResult) -> None:
        self.attack_results.append(result)
        self.total_attacks += 1

    def fault_breakdown(self) -> dict[FaultClass, int]:
        breakdown: dict[FaultClass, int] = {}
        for r in self.attack_results:
            breakdown[r.fault_class] = breakdown.get(r.fault_class, 0) + 1
        return breakdown


# ---------------------------------------------------------------------------
# Fault factories — one per class. Each returns a fresh fault instance for
# the given variant index, cycling through the available configurations.
# ---------------------------------------------------------------------------

_F1_MODES = ("invalid_json", "missing_required_field", "type_mismatch", "exception")
_F2_ATTACKS = ("instruction_override", "role_hijacking", "payload_smuggling", "indirect_injection")
_F3_VARIANTS = (
    ("retriever_insert", 0),
    ("history_insert", 0),
    ("retriever_insert", 1),
    ("history_insert", 1),
    ("retriever_insert", 2),
    ("history_insert", 2),
)
_F4_VARIANTS = (
    (300, 500),
    (300, 100),
    (500, 500),
    (1000, 500),
    (100, 300),
    (200, 100),
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


# ---------------------------------------------------------------------------
# Per-fault install/uninstall dispatch. See story-5.7 lines 319-324.
# ---------------------------------------------------------------------------


def _install_callback_tool(agent: Any, fault: Any) -> None:
    """F1, F4 attach via before_tool_callback."""
    agent.before_tool_callback = fault.as_callback()


def _uninstall_callback_tool(agent: Any) -> None:
    agent.before_tool_callback = None


def _install_callback_model(agent: Any, fault: Any) -> None:
    """F2 attaches via before_model_callback."""
    agent.before_model_callback = fault.as_callback()


def _uninstall_callback_model(agent: Any) -> None:
    agent.before_model_callback = None


def _install_f3(agent: Any, fault: ContextPoisoningFault) -> None:
    """F3 has TWO modes with different installation surfaces.

    ``history_insert``: identical shape to F2 (before_model_callback).
    ``retriever_insert``: monkey-patches each matching BaseRetrievalTool's
    ``run_async``. Uninstall reverses by removing the sentinel + restoring the
    original ``run_async`` from the closure capture.
    """
    fault.install(agent)


def _uninstall_f3(agent: Any) -> None:
    """Reverse F3's installation.

    Mirrors ``ContextPoisoningFault.install()`` — clears the
    ``_chaoslab_f3_installed`` sentinel on the agent, clears the
    ``before_model_callback`` (history_insert mode), and clears the
    ``_chaoslab_f3_patched`` sentinel on each tool (retriever_insert mode).
    The patched ``run_async`` closure is left in place — the next attack
    cycle either re-patches (idempotent via the sentinel) or uses a fresh
    target, both of which are safe."""
    if hasattr(agent, "__dict__") and "_chaoslab_f3_installed" in agent.__dict__:
        del agent.__dict__["_chaoslab_f3_installed"]
    agent.before_model_callback = None
    for tool in getattr(agent, "tools", []):
        if hasattr(tool, "__dict__") and "_chaoslab_f3_patched" in tool.__dict__:
            del tool.__dict__["_chaoslab_f3_patched"]


class Injector(BaseModel):
    """Orchestrator over the 4 fault classes + BaselineCheck (story-5.7).

    Workflow per architecture/04 §8.3 + the data-flow spec in architecture.md:

    1. ``BaselineCheck(target, n=5)`` — bail with ``BaselineAbortError`` if
       pre-injection pass rate is below 80%.
    2. Build a 4 x runs_per_fault plan (default 24 ``AttackRun``s).
    3. For each attack: build the fault → install on target.agent → invoke
       target → capture ``AttackResult`` from the span → uninstall fault.
       Sequential, not gathered — installs mutate shared callback slots.
    4. Return the populated ``InjectorState``.

    Lessons from PR #42-44 review applied:
    - try/finally lifecycle around install/uninstall so a fault that raises
      mid-attack still cleans up.
    - Adapter ``disconnect()`` always called via try/finally around the
      attack loop (silent-failure-hunter BLOCKING-1 from PR #44).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: TargetAdapter
    state: InjectorState
    runs_per_fault: int = Field(default=_DEFAULT_RUNS_PER_FAULT, ge=1, le=20)
    prompt: str = Field(default=_DEFAULT_PROMPT, min_length=1)

    async def run(self) -> InjectorState:
        """Execute baseline + 24 attacks; return populated state."""
        await self._run_baseline()
        try:
            plan = self._build_plan()
            for attack in plan:
                await self._run_one_attack(attack)
            return self.state
        finally:
            try:
                await self.target.disconnect()
            except Exception as disconnect_err:
                # Never let disconnect failure mask the original outcome.
                # Matches the PR #44 BLOCKING-1 fix pattern in BaselineCheck.
                from structlog import get_logger

                get_logger(__name__).warning(
                    "injector_disconnect_failed", error=str(disconnect_err)
                )

    async def _run_baseline(self) -> None:
        """BaselineCheck handles its own connect/disconnect lifecycle (PR #44)."""
        baseline = await BaselineCheck(target=self.target, n=_BASELINE_N).validate()
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
        # ``target.agent`` is Tier-1-in-process-specific (per story-5.7 line
        # 326). Tier 3 HTTP black-box adapters use a different installation
        # mechanism that this story doesn't implement.
        agent = self.target.agent  # ty: ignore[unresolved-attribute]
        await self.target.connect()
        fault = self._build_fault(attack)
        self._install(attack.fault_class, agent, fault)
        try:
            response = await self.target.invoke(AdapterInvocation(prompt=self.prompt))
        finally:
            self._uninstall(attack.fault_class, agent)
        self._record(attack, response)

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
        msg = f"unknown fault_class {attack.fault_class!r}"
        raise RuntimeError(msg)

    @staticmethod
    def _install(fault_class: FaultClass, agent: Any, fault: Any) -> None:
        if fault_class in ("malformed_tool_output", "latency_spike"):
            _install_callback_tool(agent, fault)
        elif fault_class == "prompt_injection":
            _install_callback_model(agent, fault)
        elif fault_class == "context_poisoning":
            _install_f3(agent, fault)

    @staticmethod
    def _uninstall(fault_class: FaultClass, agent: Any) -> None:
        if fault_class in ("malformed_tool_output", "latency_spike"):
            _uninstall_callback_tool(agent)
        elif fault_class == "prompt_injection":
            _uninstall_callback_model(agent)
        elif fault_class == "context_poisoning":
            _uninstall_f3(agent)

    def _record(self, attack: AttackRun, response: Any) -> None:
        span_id = response.span_ids[0] if response.span_ids else "<missing>"
        trace_id = (
            response.metadata.get("trace_id", "<missing>") if response.metadata else "<missing>"
        )
        if span_id == "<missing>" or trace_id == "<missing>":
            return  # the BDD requires non-empty span_id; skip this slot
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
                    "chaoslab.fault.type": attack.fault_class,
                    "chaoslab.fault.variant_idx": attack.variant_idx,
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
