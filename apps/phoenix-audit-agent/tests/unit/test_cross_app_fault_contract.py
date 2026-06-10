"""Cross-app contract: auditor descriptors ↔ target executor ↔ judge readers.

The fault descriptors are produced in THIS app, executed in target-agent's
hook surface, and their span evidence is read back by THIS app's judge. The
three live in different modules (two different apps) — this test pins them
against silent drift, the failure mode that shipped a pipeline whose contract
existed only inside test fakes (evidence-chain repair, 2026-06-10).

The uv workspace installs both apps into one venv, so importing target_agent
here is a real cross-package check, not a fixture.
"""

from __future__ import annotations

import contextlib

import pytest

from phoenix_audit_agent.injector.agent import _FAULT_CLASSES, Injector, InjectorState
from phoenix_audit_agent.injector.faults.descriptors import as_descriptor
from target_agent import fault_hooks


class _NullAdapter:
    pass


def _plan_descriptors() -> list[dict]:
    injector = Injector.model_construct(
        target=_NullAdapter(),
        state=InjectorState(),
        prompt="contract check",
        runs_per_fault=6,
    )
    return [as_descriptor(injector._build_fault(a)) for a in injector._build_plan()]


def test_every_planned_descriptor_is_executable_by_the_target() -> None:
    """The DEFAULT 24-attack plan must produce only descriptors the target's
    executor accepts — a kind/mode the executor rejects means probes that
    error on every real run."""
    for descriptor in _plan_descriptors():
        if descriptor.get("mode") == "retriever_insert":
            # Needs an agent with a retrieval tool — validated separately below.
            continue
        cb = fault_hooks.build_callback(descriptor)
        assert (
            cb.before_tool is not None
            or cb.before_model is not None
            or (descriptor.get("mode") == "retriever_insert")
        )


def test_retriever_insert_descriptors_match_the_demo_targets_kb_tool() -> None:
    """The demo target ships search_policy_kb (BaseRetrievalTool) precisely so
    the F3 retriever_insert probes are REAL — assert the wiring holds."""
    from google.adk.tools.retrieval import BaseRetrievalTool

    from target_agent.agent import root_agent

    retriever_descriptors = [d for d in _plan_descriptors() if d.get("mode") == "retriever_insert"]
    assert retriever_descriptors, "the F3 battery must include retriever_insert variants"
    assert any(isinstance(t, BaseRetrievalTool) for t in root_agent.tools), (
        "demo target lost its retrieval tool — retriever_insert probes would 422 on every real run"
    )
    for d in retriever_descriptors:
        # None = patch every retrieval tool; a specific name must exist on the target.
        wanted = d.get("target_retriever_name")
        if wanted is not None:
            assert any(getattr(t, "name", None) == wanted for t in root_agent.tools)


def test_descriptor_kinds_cover_exactly_the_fault_classes() -> None:
    kinds = {d["kind"] for d in _plan_descriptors()}
    assert kinds == set(_FAULT_CLASSES)


@pytest.mark.parametrize(
    ("config", "expected_attr_type"),
    [
        (
            {
                "kind": "malformed_tool_output",
                "mode": "type_mismatch",
                "rate": 1.0,
                "target_tool_name": None,
                "payload": {"status": 200},
            },
            "malformed_tool_output",
        ),
        (
            {"kind": "prompt_injection", "attack": "role_hijacking", "payload": "X"},
            "prompt_injection",
        ),
        (
            {
                "kind": "context_poisoning",
                "mode": "history_insert",
                "target_retriever_name": None,
                "payload": "X",
            },
            "context_poisoning",
        ),
        ({"kind": "latency_spike", "delay_ms": 1, "timeout_ms": 100}, "latency_spike"),
    ],
)
async def test_executor_writes_the_attr_namespace_the_auditor_reads(
    config: dict, expected_attr_type: str
) -> None:
    """The target executor must write `phoenix_audit.fault.type` (underscore
    namespace) — the value the report's trace-as-assertion checks and the
    Injector's span_attributes mirror. One namespace, no hyphen variant."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("contract")

    cb = fault_hooks.build_callback(config)

    class _Tool:
        name = "anything"

    class _Req:
        contents = None

    with tracer.start_as_current_span("probe"):
        if cb.before_tool is not None:
            with contextlib.suppress(RuntimeError):
                await cb.before_tool(_Tool(), {}, None)
        if cb.before_model is not None:
            await cb.before_model(None, _Req())

    attrs = exporter.get_finished_spans()[0].attributes or {}
    assert attrs.get("phoenix_audit.fault.type") == expected_attr_type
    assert not any(k.startswith("phoenix-audit.") for k in attrs), (
        "hyphenated namespace detected — the judge reads phoenix_audit.* only"
    )
