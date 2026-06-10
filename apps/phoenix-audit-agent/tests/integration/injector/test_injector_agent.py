"""Integration tests: Injector x remote fault delivery (the REAL contract).

The scripted target here simulates the DEPLOYED target faithfully: it accepts
the fault descriptor from ``AdapterInvocation.fault_config``, registers it on
the REAL target-side executor (``target_agent.fault_hooks.HookState`` — the
same code the Cloud Run target runs), drives the installed callbacks inside
test-traced spans, and reports the genuine 32-hex trace id back in metadata.

This is the composition the old suite never exercised: the previous fakes
hand-fed ``metadata={"trace_id": ...}`` and exposed a ``.agent`` attribute no
real adapter has — the suite passed while the shipped pipeline recorded every
probe as a transport error (evidence-chain repair, 2026-06-10).
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

from phoenix_audit_agent.adk_types import (
    BaseRetrievalTool,
    CallbackContext,
    LlmRequest,
    ToolContext,
)
from phoenix_audit_agent.errors import BaselineAbortError, FaultDeliveryError
from phoenix_audit_agent.injector.agent import Injector, InjectorState
from phoenix_audit_agent.injector.target_adapters import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)
from target_agent.fault_hooks import HookState

pytestmark = pytest.mark.integration

_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("phoenix-audit.test.injector.agent")


@pytest.fixture(autouse=True)
def exporter() -> InMemorySpanExporter:
    """Clean exporter per test — matches the autouse pattern from PR #42-44."""
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


def _spec() -> TargetSpec:
    return TargetSpec(tier=AdapterTier.TIER1_ADK, url=HttpUrl("http://localhost:8001/"))


class _ScriptedRetriever(BaseRetrievalTool):
    """Minimal retriever for F3 retriever_insert to patch."""

    def __init__(self) -> None:
        super().__init__(name="scripted_retriever", description="A scripted retriever")

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        return ["doc-1", "doc-2"]


class _ServedAgent:
    """The agent object living 'inside' the simulated remote target."""

    def __init__(self) -> None:
        self.before_tool_callback: Any = None
        self.before_model_callback: Any = None
        self.tools: list[Any] = [_ScriptedRetriever()]


class _HookedRemoteTarget(TargetAdapter):
    """Faithful stand-in for the deployed target + ADK adapter pair.

    invoke() mirrors ADKAdapter's contract: register fault_config on the
    (real) hook executor, drive the target work inside one traced span,
    tear down, and report trace_id + fault_delivered in metadata.
    """

    def __init__(
        self,
        spec: TargetSpec,
        *,
        baseline_fail_simulation: bool = False,
        drop_trace_id: bool = False,
        omit_fault_delivered: bool = False,
        error_on_invoke: str | None = None,
        raise_on_invoke: type[BaseException] | None = None,
    ) -> None:
        super().__init__(spec)
        self.served_agent = _ServedAgent()
        self.hook_state = HookState(self.served_agent)
        self.received_configs: list[dict[str, Any]] = []
        self.baseline_configs: list[Any] = []
        self._baseline_fail_simulation = baseline_fail_simulation
        self._drop_trace_id = drop_trace_id
        self._omit_fault_delivered = omit_fault_delivered
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
        if invocation.fault_config is None:
            self.baseline_configs.append(None)
        if self._baseline_fail_simulation and self._invoke_count % 5 in (1, 2, 3):
            return AdapterResult(
                response="", span_ids=[], duration_ms=1.0, error="baseline-fail-simulation"
            )
        in_attack_phase = invocation.fault_config is not None
        if in_attack_phase and self._raise_on_invoke is not None:
            raise self._raise_on_invoke("scripted invoke failure")

        registration_id: str | None = None
        if in_attack_phase:
            self.received_configs.append(invocation.fault_config)
            registration_id = await self.hook_state.register(invocation.fault_config)
        try:
            with _TEST_TRACER.start_as_current_span("phoenix-audit.adapter.test.invoke") as span:
                trace_id = f"{span.get_span_context().trace_id:032x}"
                adapter_span_id = f"{span.get_span_context().span_id:016x}"
                await self._drive_target_work(invocation)
        finally:
            if registration_id is not None:
                await self.hook_state.unregister(registration_id)

        metadata: dict[str, Any] = {"agent_card_name": "scripted-target"}
        if not self._drop_trace_id:
            metadata["trace_id"] = trace_id
        if in_attack_phase and not self._omit_fault_delivered:
            metadata["fault_delivered"] = True
        return AdapterResult(
            response="ok",
            span_ids=[adapter_span_id],
            duration_ms=1.0,
            error=self._error_on_invoke if in_attack_phase else None,
            metadata=metadata,
        )

    async def _drive_target_work(self, invocation: AdapterInvocation) -> None:
        """Simulate the target's request handling under the installed fault."""
        agent = self.served_agent
        config = invocation.fault_config or {}

        if agent.before_tool_callback is not None:
            with _TEST_TRACER.start_as_current_span("test.tool") as span:
                span.set_attribute("openinference.span.kind", "TOOL")

                class _Tool:
                    name = "scripted_tool"

                try:
                    await agent.before_tool_callback(_Tool(), {}, cast(ToolContext, None))
                except RuntimeError as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.record_exception(e)

        if agent.before_model_callback is not None:
            with _TEST_TRACER.start_as_current_span("test.llm") as span:
                span.set_attribute("openinference.span.kind", "LLM")
                req = LlmRequest(
                    model="gemini-3.5-flash",
                    contents=[Content(role="user", parts=[Part(text=invocation.prompt)])],
                )
                await agent.before_model_callback(cast(CallbackContext, None), req)

        if config.get("mode") == "retriever_insert":
            with _TEST_TRACER.start_as_current_span("test.retriever") as span:
                span.set_attribute("openinference.span.kind", "RETRIEVER")
                await agent.tools[0].run_async(args={}, tool_context=cast(ToolContext, None))


def _fault_tagged_spans(exporter: InMemorySpanExporter) -> list[Any]:
    return [
        s
        for s in exporter.get_finished_spans()
        if s.attributes and "phoenix_audit.fault.type" in s.attributes
    ]


def _injector(target: _HookedRemoteTarget, **kwargs: Any) -> Injector:
    return Injector(
        target=target,
        state=InjectorState(),
        prompt="Please look up order ORD-1001.",
        **kwargs,
    )


async def test_full_run_emits_24_annotated_spans_across_4_fault_classes(
    exporter: InMemorySpanExporter,
) -> None:
    target = _HookedRemoteTarget(_spec())
    state = await _injector(target).run()
    assert state.total_attacks == 24
    tagged = _fault_tagged_spans(exporter)
    assert len(tagged) >= 24
    kinds = {s.attributes["phoenix_audit.fault.type"] for s in tagged}
    assert kinds == {
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    }


async def test_every_attack_delivered_exactly_one_descriptor() -> None:
    target = _HookedRemoteTarget(_spec())
    await _injector(target).run()
    assert len(target.received_configs) == 24
    assert all("kind" in c for c in target.received_configs)
    # Baseline invokes (n=5) carry NO fault_config — never attack the
    # steady-state measurement.
    assert len(target.baseline_configs) == 5


async def test_attack_results_use_32hex_trace_indexed_span_ids() -> None:
    target = _HookedRemoteTarget(_spec())
    state = await _injector(target).run()
    for result in state.attack_results:
        assert result.status == "ok", result
        assert len(result.span_id) == 32
        assert result.span_id == result.trace_id
        assert int(result.span_id, 16) != 0
        assert result.span_attributes["phoenix_audit.adapter_span_id"]


async def test_f2_and_f3_results_carry_the_attack_payload() -> None:
    target = _HookedRemoteTarget(_spec())
    state = await _injector(target).run()
    payload_classes = {"prompt_injection", "context_poisoning"}
    for result in state.attack_results:
        if result.fault_class in payload_classes:
            assert result.attack_payload, result.fault_class
        else:
            assert result.attack_payload is None


async def test_broken_baseline_aborts_before_any_attack() -> None:
    target = _HookedRemoteTarget(_spec(), baseline_fail_simulation=True)
    injector = _injector(target)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    assert injector.state.total_attacks == 0
    assert target.received_configs == []


async def test_runs_per_fault_configures_attack_count_per_class() -> None:
    target = _HookedRemoteTarget(_spec())
    state = await _injector(target, runs_per_fault=3).run()
    assert state.total_attacks == 12
    assert all(n == 3 for n in state.fault_breakdown().values())


async def test_per_attack_teardown_leaves_target_clean() -> None:
    target = _HookedRemoteTarget(_spec())
    await _injector(target).run()
    assert target.served_agent.before_tool_callback is None
    assert target.served_agent.before_model_callback is None
    docs = await target.served_agent.tools[0].run_async(args={}, tool_context=None)
    assert docs == ["doc-1", "doc-2"], "retriever patch must be removed after the run"


async def test_disconnect_called_on_happy_path() -> None:
    target = _HookedRemoteTarget(_spec())
    await _injector(target).run()
    assert target.disconnect_count >= 1


async def test_disconnect_called_on_baseline_abort() -> None:
    target = _HookedRemoteTarget(_spec(), baseline_fail_simulation=True)
    with pytest.raises(BaselineAbortError):
        await _injector(target).run()
    # BaselineCheck owns its own lifecycle; the outer finally never ran a
    # connect, so we only require no leaked connection state.
    assert target.disconnect_count >= 1


async def test_baseline_abort_preserves_measured_pass_rate_on_state() -> None:
    target = _HookedRemoteTarget(_spec(), baseline_fail_simulation=True)
    injector = _injector(target)
    with pytest.raises(BaselineAbortError):
        await injector.run()
    assert injector.state.baseline_passed is False
    assert injector.state.baseline_pass_rate == pytest.approx(0.4)


async def test_attack_continues_when_one_invoke_raises() -> None:
    target = _HookedRemoteTarget(_spec(), raise_on_invoke=ValueError)
    state = await _injector(target).run()
    assert state.total_attacks == 24
    assert all(r.status == "error" for r in state.attack_results)


async def test_fault_delivery_error_is_contained_per_attack() -> None:
    target = _HookedRemoteTarget(_spec(), raise_on_invoke=FaultDeliveryError)
    state = await _injector(target).run()
    assert state.total_attacks == 24
    assert all(r.status == "error" for r in state.attack_results)
    assert all(
        r.span_attributes.get("phoenix_audit.attack.exception") == "FaultDeliveryError"
        for r in state.attack_results
    )


async def test_dropped_trace_id_records_error_result_not_silent_drop() -> None:
    target = _HookedRemoteTarget(_spec(), drop_trace_id=True)
    state = await _injector(target).run()
    assert state.total_attacks == 24
    for r in state.attack_results:
        assert r.status == "error"
        assert r.span_id == "missing:no-trace-emitted"


async def test_missing_fault_delivered_marker_records_error_result() -> None:
    """An adapter that ignored fault_config must not let a healthy response
    score the attack — the no-fault invocation would inflate the pass rate."""
    target = _HookedRemoteTarget(_spec(), omit_fault_delivered=True)
    state = await _injector(target).run()
    assert state.total_attacks == 24
    for r in state.attack_results:
        assert r.status == "error"
        assert r.span_attributes["phoenix_audit.attack.fault_delivered"] is False


async def test_attack_with_timeout_error_classifies_as_timeout_status() -> None:
    target = _HookedRemoteTarget(_spec(), error_on_invoke="upstream timeout after 5000ms")
    state = await _injector(target).run()
    assert all(r.status == "timeout" for r in state.attack_results)


async def test_attack_with_generic_error_classifies_as_error_status() -> None:
    target = _HookedRemoteTarget(_spec(), error_on_invoke="target exploded")
    state = await _injector(target).run()
    assert all(r.status == "error" for r in state.attack_results)


async def test_disconnect_called_exactly_once_per_run() -> None:
    target = _HookedRemoteTarget(_spec())
    await _injector(target).run()
    # one for BaselineCheck's own lifecycle + one for the attack phase
    assert target.disconnect_count == 2


async def test_build_plan_emits_correct_ordering_and_indices() -> None:
    target = _HookedRemoteTarget(_spec())
    injector = _injector(target, runs_per_fault=2)
    plan = injector._build_plan()
    assert [r.run_idx for r in plan] == list(range(8))
    expected_classes = [
        "malformed_tool_output",
        "malformed_tool_output",
        "prompt_injection",
        "prompt_injection",
        "context_poisoning",
        "context_poisoning",
        "latency_spike",
        "latency_spike",
    ]
    for i, run in enumerate(plan):
        assert run.fault_class == expected_classes[i]
