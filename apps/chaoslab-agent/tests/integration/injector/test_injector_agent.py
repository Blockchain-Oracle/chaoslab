"""Trace-as-assertion integration tests for the Injector orchestrator (story-5.7).

Drives ``Injector.run()`` against an in-process scripted target that
mimics the Tier 1 ADK shape (exposes ``agent`` with callback hooks +
tools list) but does NOT call Gemini — each invoke synthesizes a TOOL
or LLM or RETRIEVER span via OTel directly, applies whatever fault
callback has been installed, and returns an ``AdapterResult`` whose
``span_ids[0]`` points to the just-finished span.

This pattern matches PR #42-44's trace-as-assertion approach: we
verify the Injector emits the right SHAPE of spans (4 fault classes,
~24 attacks, correct ``chaoslab.fault.type`` tagging) without paying
for real Gemini calls.

Test doubles (``_ScriptedAgent``, ``_ScriptedTarget``) live in tests/
per §14.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from google.genai.types import Content, Part
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import HttpUrl

from chaoslab_agent.adk_types import BaseRetrievalTool, CallbackContext, LlmRequest, ToolContext
from chaoslab_agent.errors import BaselineAbortError
from chaoslab_agent.injector import Injector, InjectorState
from chaoslab_agent.injector.target_adapters import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

pytestmark = pytest.mark.integration

_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("chaoslab.test.injector.agent")


@pytest.fixture(autouse=True)
def exporter() -> InMemorySpanExporter:
    """Clean exporter per test — matches the autouse pattern from PR #42-44."""
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


def _spec() -> TargetSpec:
    return TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl("http://localhost:8001/"))


class _ScriptedRetriever(BaseRetrievalTool):
    """Minimal retriever for F3 retriever_insert to monkey-patch."""

    def __init__(self) -> None:
        super().__init__(name="scripted_retriever", description="A scripted retriever")

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        return ["doc-1", "doc-2"]


class _ScriptedAgent:
    """Stand-in for ADK LlmAgent that exposes the callback hooks F1-F4 mutate.

    The faults attach callbacks via:
    - ``before_tool_callback`` (F1, F4)
    - ``before_model_callback`` (F2, F3 history_insert)
    - ``ContextPoisoningFault.install(agent)`` reaches into ``agent.tools``
      to patch retrievers (F3 retriever_insert).
    """

    def __init__(self) -> None:
        self.before_tool_callback: Any = None
        self.before_model_callback: Any = None
        self.tools: list[Any] = [_ScriptedRetriever()]


class _ScriptedTarget(TargetAdapter):
    """In-process adapter that drives the agent's callbacks against a synthetic
    span on every invoke. ``agent`` is exposed so per-fault dispatch can attach
    callbacks.

    ``baseline_fail_simulation=True`` makes the FIRST 3 of every 5 invokes
    fail — produces a 40% baseline pass rate (below the 80% threshold) that
    is genuinely deterministic. Previously this used % 2 which produced 60%,
    misleadingly named.
    """

    def __init__(
        self,
        spec: TargetSpec,
        *,
        baseline_fail_simulation: bool = False,
        drop_span_ids: bool = False,
        error_on_invoke: str | None = None,
        raise_on_invoke: type[BaseException] | None = None,
    ) -> None:
        super().__init__(spec)
        self.agent = _ScriptedAgent()
        self._baseline_fail_simulation = baseline_fail_simulation
        self._drop_span_ids = drop_span_ids
        self._error_on_invoke = error_on_invoke
        self._raise_on_invoke = raise_on_invoke
        self._invoke_count = 0
        self.disconnect_count = 0

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        self.disconnect_count += 1

    async def fingerprint(self) -> AdapterFingerprint:
        return AdapterFingerprint(tier=self.spec.tier)

    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        self._invoke_count += 1
        if self._baseline_fail_simulation and self._invoke_count % 5 in (1, 2, 3):
            return AdapterResult(
                response="",
                span_ids=[],
                duration_ms=1.0,
                error="baseline-fail-simulation",
            )
        # Error/raise/drop modes apply only AFTER baseline (n=5). Otherwise
        # the test target would fail baseline and never reach the attack
        # phase the tests are trying to exercise.
        in_attack_phase = self._invoke_count > 5
        if in_attack_phase and self._raise_on_invoke is not None:
            raise self._raise_on_invoke("scripted invoke failure")
        if in_attack_phase and self._error_on_invoke is not None:
            return AdapterResult(
                response="",
                span_ids=["span-with-error"],
                duration_ms=1.0,
                error=self._error_on_invoke,
                metadata={"trace_id": "trace-test"},
            )
        if in_attack_phase and self._drop_span_ids:
            return AdapterResult(
                response="ok",
                span_ids=[],
                duration_ms=1.0,
                error=None,
                metadata={"trace_id": "trace-test"},
            )

        span_kind, span_id = await self._drive_callbacks(invocation)
        return AdapterResult(
            response="ok",
            span_ids=[span_id],
            duration_ms=1.0,
            error=None,
            metadata={"trace_id": "trace-test", "span_kind": span_kind},
        )

    async def _drive_callbacks(self, invocation: AdapterInvocation) -> tuple[str, str]:
        """Fire the installed callbacks once each inside test-traced spans.

        Returns (span_kind, span_id) for the LAST fault-tagged span that fired.
        """
        last_kind = "TOOL"
        last_span_id = "no-fault-fired"

        if self.agent.before_tool_callback is not None:
            with _TEST_TRACER.start_as_current_span("test.tool") as span:
                span.set_attribute("openinference.span.kind", "TOOL")
                from google.adk.tools.function_tool import FunctionTool

                def _t() -> dict[str, Any]:
                    return {"status": "ok"}

                tool = FunctionTool(func=_t)
                try:
                    await self.agent.before_tool_callback(
                        tool=tool, args={}, tool_context=cast(ToolContext, None)
                    )
                except RuntimeError as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.record_exception(e)
                last_kind = "TOOL"
                last_span_id = f"{span.get_span_context().span_id:016x}"

        if self.agent.before_model_callback is not None:
            with _TEST_TRACER.start_as_current_span("test.llm") as span:
                span.set_attribute("openinference.span.kind", "LLM")
                req = LlmRequest(
                    model="gemini-3.5-flash",
                    contents=[Content(role="user", parts=[Part(text=invocation.prompt)])],
                )
                await self.agent.before_model_callback(
                    callback_context=cast(CallbackContext, None), llm_request=req
                )
                last_kind = "LLM"
                last_span_id = f"{span.get_span_context().span_id:016x}"

        # Only emit a RETRIEVER span if the retriever was patched (F3
        # retriever_insert). The sentinel attribute is set by
        # ContextPoisoningFault.install().
        if (
            self.agent.tools
            and isinstance((tool := self.agent.tools[0]), BaseRetrievalTool)
            and getattr(tool, "_chaoslab_f3_patched", False)
        ):
            with _TEST_TRACER.start_as_current_span("test.retriever") as span:
                span.set_attribute("openinference.span.kind", "RETRIEVER")
                await tool.run_async(args={}, tool_context=cast(ToolContext, None))
                last_kind = "RETRIEVER"
                last_span_id = f"{span.get_span_context().span_id:016x}"

        return last_kind, last_span_id


def _fault_tagged_spans(exporter: InMemorySpanExporter) -> list[Any]:
    return [
        s
        for s in exporter.get_finished_spans()
        if s.attributes is not None and s.attributes.get("chaoslab.fault.type")
    ]


# ---------------------------------------------------------------------------
# Happy path: 24 attacks, 4 fault classes, baseline_passed.
# ---------------------------------------------------------------------------


async def test_full_run_emits_24_annotated_spans_across_4_fault_classes() -> None:
    """BDD lines 52-58: the canonical 5x5-cell-style demo grid materializes."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=6)
    await injector.run()

    fault_spans = _fault_tagged_spans(_TEST_EXPORTER)
    assert len(fault_spans) >= 24, f"expected ≥24 fault-tagged spans, got {len(fault_spans)}"

    fault_types = {s.attributes["chaoslab.fault.type"] for s in fault_spans}
    assert fault_types == {
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    }

    breakdown = state.fault_breakdown()
    for fc in fault_types:
        assert (
            breakdown.get(fc, 0) >= 4
        ), f"expected ≥4 attacks for {fc}, got {breakdown.get(fc, 0)}"

    assert state.baseline_passed is True
    assert state.total_attacks >= 24


async def test_broken_baseline_aborts_before_any_attack() -> None:
    """BDD lines 60-63: degraded target → BaselineAbortError, zero attack spans."""
    target = _ScriptedTarget(_spec(), baseline_fail_simulation=True)
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=6)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    assert _fault_tagged_spans(_TEST_EXPORTER) == []
    assert state.total_attacks == 0
    assert state.baseline_passed is False


async def test_attack_results_carry_non_empty_span_id_and_fault_class() -> None:
    """BDD lines 65-67: every AttackResult is fully populated."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    await Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=6).run()

    assert state.attack_results, "expected at least one AttackResult"
    for result in state.attack_results:
        assert result.span_id
        assert result.span_id != "<missing>"
        assert result.fault_class in {
            "malformed_tool_output",
            "prompt_injection",
            "context_poisoning",
            "latency_spike",
        }


async def test_runs_per_fault_configures_attack_count_per_class() -> None:
    """runs_per_fault=3 → exactly 3 attacks per fault class = 12 total."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    await Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=3).run()

    breakdown = state.fault_breakdown()
    for fc in (
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    ):
        assert breakdown.get(fc, 0) >= 3
    assert state.total_attacks >= 12


async def test_per_attack_uninstall_isolates_consecutive_attacks() -> None:
    """Each attack must clean up before the next runs — otherwise the F3
    retriever monkey-patch persists into F4's run and the trace becomes
    confusing (story-5.7 line 318 "_install / _uninstall symmetry")."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    await Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=6).run()

    # After all attacks: callbacks should be uninstalled.
    assert (
        target.agent.before_tool_callback is None
    ), "F1/F4 left a before_tool_callback installed — uninstall is broken"
    assert (
        target.agent.before_model_callback is None
    ), "F2/F3 left a before_model_callback installed — uninstall is broken"


async def test_disconnect_called_on_happy_path() -> None:
    """Resource lifecycle — apply S5.6 PR #44 BLOCKING-1 fix at the Injector level too."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    await Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2).run()
    assert target.disconnect_count >= 1


async def test_disconnect_called_on_baseline_abort() -> None:
    """Even when baseline aborts, the adapter must be released."""
    target = _ScriptedTarget(_spec(), baseline_fail_simulation=True)
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    assert target.disconnect_count >= 1


# Round-2 regression tests for the 4-reviewer pass on PR #45.


async def test_baseline_abort_preserves_measured_pass_rate_on_state() -> None:
    """Regulator-facing data integrity: when baseline aborts, the state must
    carry the actual measured pass_rate, not the default 0.0. Catches the
    silent-failure-hunter HIGH-4 regression where _run_baseline would lose
    the measurement on the abort path."""
    target = _ScriptedTarget(_spec(), baseline_fail_simulation=True)
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    assert state.baseline_pass_rate > 0.0
    assert state.baseline_pass_rate < 0.8
    assert state.baseline_passed is False


async def test_attack_continues_when_one_invoke_raises() -> None:
    """One bad invoke must NOT kill the 24-attack audit (silent-failure-hunter
    BLOCKING-2). The exception surfaces as an error-status AttackResult."""
    target = _ScriptedTarget(_spec(), raise_on_invoke=RuntimeError)
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    await injector.run()
    # All 8 attacks (4 classes x 2 runs) attempted; each raised → error result
    assert state.total_attacks == 8
    for result in state.attack_results:
        assert result.status == "error"
        assert result.span_id.startswith("error:RuntimeError")


async def test_attack_with_dropped_span_id_records_error_result_not_silent_drop() -> None:
    """silent-failure-hunter BLOCKING-1: adapter that doesn't populate span_ids
    must produce an error-status AttackResult, NOT a silent skip."""
    target = _ScriptedTarget(_spec(), drop_span_ids=True)
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    await injector.run()
    # All 8 attempts recorded — not silently dropped
    assert state.total_attacks == 8
    for result in state.attack_results:
        assert result.status == "error"
        assert result.span_id == "missing:no-span-emitted"
        assert result.span_attributes.get("chaoslab.attack.span_missing") is True


async def test_attack_with_timeout_error_classifies_as_timeout_status() -> None:
    """Status classification: response.error containing 'timeout' substring
    classifies as 'timeout' rather than 'error'."""
    target = _ScriptedTarget(_spec(), error_on_invoke="ReadTimeout: target slow")
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    await injector.run()
    for result in state.attack_results:
        assert result.status == "timeout"


async def test_attack_with_generic_error_classifies_as_error_status() -> None:
    """Status classification: response.error without 'timeout' substring
    classifies as 'error'."""
    target = _ScriptedTarget(_spec(), error_on_invoke="tool produced invalid JSON")
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2)
    await injector.run()
    for result in state.attack_results:
        assert result.status == "error"


async def test_disconnect_called_exactly_once_per_run() -> None:
    """Injector connects once at attack-phase entry and disconnects once at
    finally. BaselineCheck owns its own lifecycle separately."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    await Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=2).run()
    # Two disconnects total: one from BaselineCheck, one from Injector
    assert target.disconnect_count == 2


async def test_build_plan_emits_correct_ordering_and_indices() -> None:
    """Direct test of _build_plan: 4 classes x runs_per_fault, ordered
    F1→F2→F3→F4, run_idx strictly increments 0..N-1, variant_idx cycles."""
    target = _ScriptedTarget(_spec())
    state = InjectorState()
    injector = Injector(target=target, state=state, prompt="test-prompt", runs_per_fault=3)
    plan = injector._build_plan()
    assert len(plan) == 12
    expected_classes = (
        ["malformed_tool_output"] * 3
        + ["prompt_injection"] * 3
        + ["context_poisoning"] * 3
        + ["latency_spike"] * 3
    )
    for i, run in enumerate(plan):
        assert run.run_idx == i
        assert run.fault_class == expected_classes[i]
        assert run.variant_idx == i % 3
