"""Trace-as-assertion tests for F3 ContextPoisoningFault.

These tests run offline (no Gemini cost) using ADK BaseRetrievalTool
and InMemoryRunner.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from google.genai.types import Content, Part
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span

from chaoslab_agent.adk_types import BaseRetrievalTool, CallbackContext, LlmRequest, ToolContext
from chaoslab_agent.injector.faults import ContextPoisoningFault
from chaoslab_agent.injector.faults.context_poisoning import POISON_MARKER

pytestmark = pytest.mark.integration

_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("chaoslab.test.injector.faults")


@pytest.fixture(autouse=True)
def exporter() -> InMemorySpanExporter:
    """Autouse so every test in the file starts with a clean exporter.

    Without autouse, tests that don't list `exporter` in their signature
    would observe stale spans from prior tests in the module — see
    test-analyzer B2.
    """
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


class FakeRetrievalTool(BaseRetrievalTool):
    """A minimal BaseRetrievalTool for RAG-inject testing."""

    def __init__(self, name: str = "fake_retriever") -> None:
        super().__init__(name=name, description="A fake retriever tool")

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        # Returns a list of document-like objects or strings
        return ["original doc 1", "original doc 2"]


class FakeAgent:
    """A fake agent containing tools."""

    def __init__(self) -> None:
        self.tools: list[Any] = [FakeRetrievalTool()]
        self.before_model_callback = None


async def _invoke_callback(
    fault: ContextPoisoningFault,
    req: LlmRequest,
) -> tuple[None, Span]:
    """Run the fault's callback inside an LLM span."""
    callback = fault.as_callback()
    with _TEST_TRACER.start_as_current_span("test.llm.call") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        await callback(callback_context=cast(CallbackContext, None), llm_request=req)
        user_prompt = ""
        if req.contents is not None:
            user_parts = []
            for msg in req.contents:
                if getattr(msg, "role", None) == "user" and msg.parts:
                    user_parts.append("".join(getattr(p, "text", "") or "" for p in msg.parts))
            user_prompt = "\n".join(user_parts)
        span.set_attribute("input.value", user_prompt)
    return None, span


def _last_span_by_kind(exporter: InMemorySpanExporter, kind: str) -> ReadableSpan:
    spans = [
        s
        for s in exporter.get_finished_spans()
        if s.attributes is not None and s.attributes.get("openinference.span.kind") == kind
    ]
    assert spans, f"no {kind} spans recorded"
    return spans[-1]


async def test_retriever_insert_lands_poison_at_document_index_zero_list(
    exporter: InMemorySpanExporter,
) -> None:
    fault = ContextPoisoningFault(mode="retriever_insert")
    agent = FakeAgent()
    fault.install(agent)

    tool = agent.tools[0]
    with _TEST_TRACER.start_as_current_span("test.retrieval") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        res = await tool.run_async(args={"query": "test"}, tool_context=cast(ToolContext, None))

    assert len(res) == 3
    assert isinstance(res[0], str)
    assert POISON_MARKER in res[0]

    span = _last_span_by_kind(exporter, "RETRIEVER")
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.type") == "context_poisoning"
    assert span.attributes.get("chaoslab.fault.mode") == "retriever_insert"


class StringRetrievalTool(BaseRetrievalTool):
    """A retriever returning raw string content."""

    def __init__(self) -> None:
        super().__init__(name="string_retriever", description="String retriever")

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        return "original raw text"


async def test_retriever_insert_lands_poison_for_raw_string_retrieval(
    exporter: InMemorySpanExporter,
) -> None:
    fault = ContextPoisoningFault(mode="retriever_insert")
    agent = FakeAgent()
    agent.tools = [StringRetrievalTool()]
    fault.install(agent)

    tool = agent.tools[0]
    with _TEST_TRACER.start_as_current_span("test.retrieval") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        res = await tool.run_async(args={"query": "test"}, tool_context=cast(ToolContext, None))

    assert isinstance(res, str)
    assert res.startswith(POISON_MARKER)
    assert "original raw text" in res


async def test_retriever_name_filter_matches(exporter: InMemorySpanExporter) -> None:
    fault = ContextPoisoningFault(mode="retriever_insert", target_retriever_name="string_retriever")
    agent = FakeAgent()
    agent.tools = [FakeRetrievalTool(), StringRetrievalTool()]
    fault.install(agent)
    null_ctx = cast(ToolContext, None)

    res_fake = await agent.tools[0].run_async(args={"query": "test"}, tool_context=null_ctx)
    assert len(res_fake) == 2

    res_str = await agent.tools[1].run_async(args={"query": "test"}, tool_context=null_ctx)
    assert isinstance(res_str, str)
    assert res_str.startswith(POISON_MARKER)


async def test_payload_override_applies_to_retriever_insert(
    exporter: InMemorySpanExporter,
) -> None:
    fault = ContextPoisoningFault(
        mode="retriever_insert", payload_override="CUSTOM RETRIEVER POISON"
    )
    agent = FakeAgent()
    fault.install(agent)

    res = await agent.tools[0].run_async(
        args={"query": "test"}, tool_context=cast(ToolContext, None)
    )
    assert res[0] == "CUSTOM RETRIEVER POISON"


async def test_history_insert_prepends_poisoned_message(
    exporter: InMemorySpanExporter,
) -> None:
    fault = ContextPoisoningFault(mode="history_insert")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal user query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert len(req.contents) == 2
    assert req.contents[0].parts is not None
    assert POISON_MARKER in (req.contents[0].parts[0].text or "")

    span = _last_span_by_kind(exporter, "LLM")
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.type") == "context_poisoning"
    assert span.attributes.get("chaoslab.fault.mode") == "history_insert"

    input_value = span.attributes.get("input.value")
    assert isinstance(input_value, str)
    assert POISON_MARKER in input_value


async def test_history_insert_with_payload_override(
    exporter: InMemorySpanExporter,
) -> None:
    fault = ContextPoisoningFault(mode="history_insert", payload_override="CUSTOM HISTORY POISON")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal user query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert req.contents[0].parts is not None
    assert req.contents[0].parts[0].text == "CUSTOM HISTORY POISON"


async def test_history_callback_accepts_adk_kwarg_invocation_contract() -> None:
    """ADK calls `callback(callback_context=..., llm_request=...)` (kwargs).

    See google/adk/flows/llm_flows/base_llm_flow.py:230. Param names must match
    or this would crash in production with TypeError. Regression guard.
    """
    fault = ContextPoisoningFault(mode="history_insert")
    callback = fault.as_callback()
    req = LlmRequest(
        model="gemini-3.5-flash",
        contents=[Content(role="user", parts=[Part(text="hello")])],
    )
    await callback(callback_context=cast(CallbackContext, None), llm_request=req)
    assert req.contents is not None
    assert len(req.contents) == 2
    assert req.contents[0].parts is not None
    assert POISON_MARKER in (req.contents[0].parts[0].text or "")


# ---------------------------------------------------------------------------
# Regression tests for post-review hardening (silent-failure-hunter + type-design)
# ---------------------------------------------------------------------------


async def test_retriever_insert_raises_when_no_retriever_on_target() -> None:
    """No silent no-op when the target has no BaseRetrievalTool (silent-failure-hunter H1)."""

    class EmptyAgent:
        def __init__(self) -> None:
            self.tools: list[Any] = []
            self.before_model_callback = None

    fault = ContextPoisoningFault(mode="retriever_insert")
    with pytest.raises(RuntimeError, match=r"no BaseRetrievalTool matched"):
        fault.install(EmptyAgent())


async def test_retriever_insert_raises_when_filter_excludes_all_retrievers() -> None:
    """Same when target_retriever_name filter matches nothing."""
    fault = ContextPoisoningFault(mode="retriever_insert", target_retriever_name="does_not_exist")
    with pytest.raises(RuntimeError, match=r"no BaseRetrievalTool matched"):
        fault.install(FakeAgent())


async def test_retriever_patch_raises_on_unsupported_result_type() -> None:
    """No silent no-op when retriever returns neither list nor str (silent-failure-hunter H2)."""

    class DictRetrievalTool(BaseRetrievalTool):
        def __init__(self) -> None:
            super().__init__(name="dict_retriever", description="Returns dict")

        async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
            return {"unsupported": "shape"}

    fault = ContextPoisoningFault(mode="retriever_insert")
    agent = FakeAgent()
    agent.tools = [DictRetrievalTool()]
    fault.install(agent)

    with _TEST_TRACER.start_as_current_span("test.retrieval") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        with pytest.raises(RuntimeError, match=r"unsupported type 'dict'"):
            await agent.tools[0].run_async(
                args={"query": "test"}, tool_context=cast(ToolContext, None)
            )

    s = _last_span_by_kind(_TEST_EXPORTER, "RETRIEVER")
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.injected") is False


async def test_install_is_not_idempotent_raises_on_double_install() -> None:
    """Calling install() twice on the same agent raises rather than silently re-wrapping
    (silent-failure-hunter H3 + code-reviewer N2)."""
    fault = ContextPoisoningFault(mode="history_insert")
    agent = FakeAgent()
    fault.install(agent)
    with pytest.raises(RuntimeError, match=r"called twice on the same agent"):
        fault.install(agent)


async def test_history_insert_preserves_existing_before_model_callback() -> None:
    """If the target already has a before_model_callback, F3 appends rather than overwrites
    (code-reviewer N2)."""

    async def existing_cb(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
        pass

    agent = FakeAgent()
    agent.before_model_callback = existing_cb  # type: ignore[assignment]
    fault = ContextPoisoningFault(mode="history_insert")
    fault.install(agent)

    assert isinstance(agent.before_model_callback, list)
    assert agent.before_model_callback[0] is existing_cb
    assert agent.before_model_callback[1] is not existing_cb


async def test_retriever_patch_records_injected_true_attribute() -> None:
    """The injected boolean attr is the canonical "fault landed" signal — verify the
    happy path sets it to True."""
    fault = ContextPoisoningFault(mode="retriever_insert")
    agent = FakeAgent()
    fault.install(agent)

    with _TEST_TRACER.start_as_current_span("test.retrieval") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        await agent.tools[0].run_async(args={"query": "test"}, tool_context=cast(ToolContext, None))

    s = _last_span_by_kind(_TEST_EXPORTER, "RETRIEVER")
    assert s.attributes is not None
    assert s.attributes.get("chaoslab.fault.injected") is True
