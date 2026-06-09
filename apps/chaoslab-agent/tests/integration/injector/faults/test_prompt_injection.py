"""Trace-as-assertion tests for F2 PromptInjectionFault.

The spec (story-5.3 BDD lines 48-73) calls for verifying that each prompt
injection attack type produces an LLM span with the expected
``chaoslab.fault.type`` / ``chaoslab.fault.attack`` attributes and the
attack-specific OWASP LLM01 payload inside the prompt.

These tests exercise the callback contract directly against a real ADK
``LlmRequest`` + a real OpenTelemetry ``InMemorySpanExporter`` — they do
NOT drive Gemini, so they run without ``@pytest.mark.online`` cost.
"""

from __future__ import annotations

from typing import cast

import pytest
from google.genai.types import Content, Part
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span

from chaoslab_agent.adk_types import CallbackContext, LlmRequest
from chaoslab_agent.injector.faults import PromptInjectionFault

pytestmark = pytest.mark.integration

_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("chaoslab.test.injector.faults")


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


async def _invoke_callback(
    fault: PromptInjectionFault,
    req: LlmRequest,
) -> tuple[None, Span]:
    """Run the fault's callback inside an LLM span on the test tracer."""
    callback = fault.as_callback()
    with _TEST_TRACER.start_as_current_span("test.llm.call") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        await callback(cast(CallbackContext, None), req)
        user_prompt = ""
        if req.contents is not None:
            for msg in reversed(req.contents):
                if getattr(msg, "role", None) == "user" and msg.parts:
                    user_prompt = "".join(getattr(p, "text", "") or "" for p in msg.parts)
                    break
        span.set_attribute("input.value", user_prompt)
    return None, span


def _last_llm_span(exporter: InMemorySpanExporter) -> ReadableSpan:
    spans = [
        s
        for s in exporter.get_finished_spans()
        if s.attributes is not None and s.attributes.get("openinference.span.kind") == "LLM"
    ]
    assert spans, "no LLM spans recorded"
    return spans[-1]


async def test_instruction_override_lands_in_llm_input_value(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="instruction_override")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await _invoke_callback(fault, req)

    # 1) Verify payload was appended in LlmRequest
    assert req.contents is not None
    assert req.contents[0].parts is not None
    last_part = req.contents[0].parts[-1]
    user_text = last_part.text or ""
    assert "IGNORE ALL PRIOR INSTRUCTIONS" in user_text

    # 2) Verify span attributes and input.value
    span = _last_llm_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.type") == "prompt_injection"
    assert span.attributes.get("chaoslab.fault.attack") == "instruction_override"

    input_value = span.attributes.get("input.value")
    assert isinstance(input_value, str)
    assert "IGNORE" in input_value.upper()
    assert "INSTRUCTIONS" in input_value.upper()


async def test_role_hijacking_lands_in_llm_input_value(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="role_hijacking")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert req.contents[0].parts is not None
    last_part = req.contents[0].parts[-1]
    user_text = last_part.text or ""
    assert "SYSTEM OVERRIDE" in user_text
    assert "admin mode" in user_text

    span = _last_llm_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.attack") == "role_hijacking"

    input_value = span.attributes.get("input.value")
    assert isinstance(input_value, str)
    assert "ADMIN MODE" in input_value.upper() or "SYSTEM OVERRIDE" in input_value.upper()


async def test_payload_smuggling_lands_in_llm_input_value(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="payload_smuggling")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert req.contents[0].parts is not None
    last_part = req.contents[0].parts[-1]
    user_text = last_part.text or ""
    assert "attacker payload" in user_text or "aWdub3Jl" in user_text

    span = _last_llm_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.attack") == "payload_smuggling"

    input_value = span.attributes.get("input.value")
    assert isinstance(input_value, str)
    assert "attacker payload" in input_value or "base64" in input_value


async def test_indirect_injection_lands_in_llm_input_value(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="indirect_injection")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert req.contents[0].parts is not None
    last_part = req.contents[0].parts[-1]
    user_text = last_part.text or ""
    assert "Retrieved document note" in user_text

    span = _last_llm_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.attack") == "indirect_injection"

    input_value = span.attributes.get("input.value")
    assert isinstance(input_value, str)
    assert "Retrieved document note" in input_value or "9999" in input_value


async def test_payload_override_applies_custom_string(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="instruction_override", payload_override="CUSTOM INJECTION")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await _invoke_callback(fault, req)

    assert req.contents is not None
    assert req.contents[0].parts is not None
    last_part = req.contents[0].parts[-1]
    user_text = last_part.text or ""
    assert user_text == "normal queryCUSTOM INJECTION"

    span = _last_llm_span(exporter)
    assert span.attributes is not None
    input_value = span.attributes.get("input.value")
    assert input_value == "normal queryCUSTOM INJECTION"


async def test_user_role_not_found_leaves_contents_intact(
    exporter: InMemorySpanExporter,
) -> None:
    fault = PromptInjectionFault(attack="instruction_override")
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="model", parts=[Part(text="response text")])],
    )
    await _invoke_callback(fault, req)

    # Contents must remain completely unaltered.
    assert req.contents is not None
    assert len(req.contents) == 1
    assert req.contents[0].parts is not None
    assert req.contents[0].parts[0].text == "response text"

    span = _last_llm_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("chaoslab.fault.type") == "prompt_injection"


async def test_callback_accepts_adk_kwarg_invocation_contract() -> None:
    """ADK calls `callback(callback_context=..., llm_request=...)` (kwargs).

    See google/adk/flows/llm_flows/base_llm_flow.py:230. Param names must match
    or this would crash in production with TypeError. Regression guard.
    """
    fault = PromptInjectionFault(attack="instruction_override")
    callback = fault.as_callback()
    req = LlmRequest(
        model="gemini-2.5-flash",
        contents=[Content(role="user", parts=[Part(text="normal query")])],
    )
    await callback(callback_context=cast(CallbackContext, None), llm_request=req)
    assert req.contents is not None
    assert req.contents[0].parts is not None
    user_text = req.contents[0].parts[-1].text or ""
    assert "IGNORE ALL PRIOR INSTRUCTIONS" in user_text
