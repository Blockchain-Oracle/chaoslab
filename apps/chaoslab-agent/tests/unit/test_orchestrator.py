"""SequentialAgent orchestrator structural + trace-as-assertion tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import cast

import pytest
from google.adk.agents.llm_agent import LlmAgent

# ADR-012: SequentialAgent is the pinned deprecated API for ADK 2.x.
from google.adk.agents.sequential_agent import SequentialAgent  # ty: ignore[deprecated]

from chaoslab_agent.config import JUDGE_LLM_LOCKED, get_settings


def _llm_sub_agents(orch: SequentialAgent) -> list[LlmAgent]:  # ty: ignore[deprecated]
    """Cast helper: sub_agents is typed as list[BaseAgent], but Phoenix Audit's
    factories return LlmAgent. Casting at the test boundary keeps each test free
    of per-line ty suppressions without weakening the production type contract.
    """
    return [cast(LlmAgent, a) for a in orch.sub_agents]


def _instruction_str(agent: LlmAgent) -> str:
    """LlmAgent.instruction is typed `str | Callable[...] | None`; Phoenix Audit's
    factories always supply a static str — narrow here at the test boundary."""
    instr = agent.instruction
    assert isinstance(instr, str), f"{agent.name} instruction not a static str: {type(instr)}"
    return instr


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip inherited env so Settings() defaults deterministically."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_build_orchestrator_returns_sequential_agent_instance() -> None:
    from chaoslab_agent.orchestrator import build_orchestrator

    orch = build_orchestrator()
    assert isinstance(orch, SequentialAgent)  # ty: ignore[deprecated]


def test_orchestrator_name_is_locked() -> None:
    """`ChaosLabOrchestrator` is the span name asserted in trace-as-assertion gates."""
    from chaoslab_agent.orchestrator import ORCHESTRATOR_NAME, build_orchestrator

    assert ORCHESTRATOR_NAME == "ChaosLabOrchestrator"
    assert build_orchestrator().name == ORCHESTRATOR_NAME


def test_orchestrator_has_exactly_three_sub_agents() -> None:
    from chaoslab_agent.orchestrator import build_orchestrator

    orch = build_orchestrator()
    assert len(orch.sub_agents) == 3


def test_sub_agent_names_are_injector_judge_patcher_in_order() -> None:
    """Sequential execution order is asserted at the span-tree layer; name order is the gate."""
    from chaoslab_agent.orchestrator import build_orchestrator

    orch = build_orchestrator()
    assert [a.name for a in orch.sub_agents] == ["Injector", "Judge", "Patcher"]


def test_all_sub_agents_use_locked_judge_llm() -> None:
    """ADR-007: every sub-agent must use gemini-3.5-flash, not Pro / Flash-Lite / Pro-preview."""
    from chaoslab_agent.orchestrator import build_orchestrator

    for a in _llm_sub_agents(build_orchestrator()):
        assert (
            a.model == JUDGE_LLM_LOCKED
        ), f"{a.name} model = {a.model!r}, expected {JUDGE_LLM_LOCKED!r}"


def test_sub_agent_output_keys_match_contract() -> None:
    """The {injector_result}/{judge_result} template substitution depends on these exact keys."""
    from chaoslab_agent.orchestrator import build_orchestrator

    keys = [a.output_key for a in _llm_sub_agents(build_orchestrator())]
    assert keys == ["injector_result", "judge_result", "patcher_result"]


def test_judge_instruction_references_injector_result_template() -> None:
    """State flow via ADK template substitution — Judge MUST read upstream output."""
    from chaoslab_agent.orchestrator import build_orchestrator

    judge = next(a for a in _llm_sub_agents(build_orchestrator()) if a.name == "Judge")
    assert "{injector_result}" in _instruction_str(judge)


def test_patcher_instruction_references_judge_result_template() -> None:
    from chaoslab_agent.orchestrator import build_orchestrator

    patcher = next(a for a in _llm_sub_agents(build_orchestrator()) if a.name == "Patcher")
    assert "{judge_result}" in _instruction_str(patcher)


def test_each_sub_agent_has_a_non_trivial_description() -> None:
    """Description is load-bearing for supervisor routing (architecture/03 §1.1)."""
    from chaoslab_agent.orchestrator import build_orchestrator

    for a in _llm_sub_agents(build_orchestrator()):
        assert a.description, f"{a.name} has no description"
        assert len(a.description) >= 20, f"{a.name} description too short: {a.description!r}"


def test_sub_agent_factories_are_importable_individually() -> None:
    """Each sub-agent ships its own factory module so Epic 5/6 can swap implementations."""
    from chaoslab_agent.injector.agent import build_injector_agent
    from chaoslab_agent.judge.agent import build_judge_agent
    from chaoslab_agent.patcher.agent import build_patcher_agent

    assert build_injector_agent().name == "Injector"
    assert build_judge_agent().name == "Judge"
    assert build_patcher_agent().name == "Patcher"


def test_sub_agent_instructions_are_stub_marked() -> None:
    """`STUB:` prefix is the §14-carve-out documented in the story file."""
    from chaoslab_agent.orchestrator import build_orchestrator

    for a in _llm_sub_agents(build_orchestrator()):
        instruction = _instruction_str(a)
        assert instruction.startswith(
            "STUB:"
        ), f"{a.name} instruction missing STUB: prefix: {instruction[:60]!r}"


# --- Trace-as-assertion (story-4.2 BDD criterion 5, PRIMARY correctness signal) --


async def test_orchestrator_emits_three_ordered_agent_spans(  # noqa: PLR0915 — trace-as-assertion test legitimately wires OTel + ADK + assertions
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trace-as-assertion: the SequentialAgent's span tree IS the correctness gate.

    Wires an in-memory OTel pipeline + GoogleADKInstrumentor, stubs the LLM call so
    no real Gemini traffic is required, drives the orchestrator via InMemoryRunner,
    and asserts on the captured spans.

    Note on span naming: the openinference-google-adk instrumentor wraps `BaseAgent.run_async`
    and creates spans named `agent_run [<agent.name>]` with `agent.name` attribute carrying
    the actual name + `openinference.span.kind == "AGENT"`. The story file's expected
    raw-name-only assertion predates the current instrumentor — we assert on the
    `agent.name` attribute instead, which is the load-bearing identifier.
    """
    from collections.abc import AsyncGenerator
    from typing import Any

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.events.event import Event
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Content, Part
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from chaoslab_agent.orchestrator import ORCHESTRATOR_NAME, build_orchestrator

    exporter = InMemorySpanExporter()
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exporter))
    instrumentor = GoogleADKInstrumentor()
    instrumentor.instrument(tracer_provider=tp)

    async def fake_run_async_impl(
        self: LlmAgent, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Bypass Gemini: yield a single synthetic final-response event per sub-agent."""
        content = Content(role="model", parts=[Part(text=f"{{}}stub-{self.name}-output")])
        yield Event(invocation_id=ctx.invocation_id, author=self.name, content=content)
        ctx.set_agent_state(self.name, end_of_agent=True)
        yield self._create_agent_state_event(ctx)

    monkeypatch.setattr(LlmAgent, "_run_async_impl", fake_run_async_impl)

    try:
        orch = build_orchestrator()
        runner = InMemoryRunner(agent=orch, app_name="chaoslab-test")
        session = await runner.session_service.create_session(
            app_name="chaoslab-test", user_id="trace-test"
        )
        new_message = Content(role="user", parts=[Part(text="run audit")])
        events: list[Any] = []
        async for event in runner.run_async(
            user_id="trace-test", session_id=session.id, new_message=new_message
        ):
            events.append(event)
        tp.force_flush(timeout_millis=2000)
        spans = exporter.get_finished_spans()
    finally:
        instrumentor.uninstrument()

    # Map each span's `agent.name` attribute -> span; orchestrator + 3 children all carry it.
    by_agent: dict[str, list[Any]] = {}
    for s in spans:
        attrs = dict(s.attributes or {})
        agent_name = attrs.get("agent.name")
        if isinstance(agent_name, str):
            by_agent.setdefault(agent_name, []).append(s)

    # 1. Exactly one orchestrator-named span (the parent of the chain).
    assert (
        ORCHESTRATOR_NAME in by_agent
    ), f"no span carried agent.name={ORCHESTRATOR_NAME!r}; saw: {sorted(by_agent)}"
    orch_spans = by_agent[ORCHESTRATOR_NAME]
    assert len(orch_spans) == 1, f"expected 1 orchestrator span, got {len(orch_spans)}"
    parent = orch_spans[0]

    # 2. Three children with agent.name in {Injector, Judge, Patcher}, in start_time order.
    children = sorted(
        (s for s in spans if s.parent and s.parent.span_id == parent.context.span_id),
        key=lambda s: s.start_time or 0,
    )
    child_names = [dict(s.attributes or {}).get("agent.name") for s in children]
    assert child_names == [
        "Injector",
        "Judge",
        "Patcher",
    ], f"expected ordered Injector/Judge/Patcher children; got {child_names}"

    # 3. Each child carries openinference.span.kind == "AGENT".
    for child in children:
        attrs = dict(child.attributes or {})
        kind = attrs.get("openinference.span.kind")
        assert (
            kind == "AGENT"
        ), f"{attrs.get('agent.name')!r} span.kind = {kind!r}, expected 'AGENT'"

    # 4. Sequential execution proven: Patcher started AFTER Judge ended.
    judge = next(s for s in children if dict(s.attributes or {}).get("agent.name") == "Judge")
    patcher = next(s for s in children if dict(s.attributes or {}).get("agent.name") == "Patcher")
    assert patcher.start_time is not None, "Patcher span missing start_time"
    assert judge.end_time is not None, "Judge span missing end_time"
    assert patcher.start_time >= judge.end_time, (
        f"Patcher started before Judge ended (start={patcher.start_time}, "
        f"judge_end={judge.end_time}) — parallel execution detected, expected sequential"
    )
