"""S-EC5: ADKAdapter evidence-chain contract — trace_id, traceparent, fault hooks.

The Judge fetches the TARGET's spans from Phoenix by the trace_id the adapter
reports. That only works if (a) the adapter actually reports it, and (b) the
outgoing A2A request carries `traceparent` so the target's spans join the
same trace. Fault delivery goes over the target's /hooks/adk surface; a
fault that cannot be delivered must RAISE — recording a no-fault invocation
as an attack result would silently inflate the pass rate.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import pytest
import respx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from phoenix_audit_agent.errors import FaultDeliveryError
from phoenix_audit_agent.injector.target_adapters import ADKAdapter, TargetSpec
from phoenix_audit_agent.injector.target_adapters import adk_adapter as adk_module
from phoenix_audit_agent.injector.target_adapters.base import AdapterInvocation

_HEX32 = re.compile(r"^[0-9a-f]{32}$")

_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider()
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))


@pytest.fixture(autouse=True)
def _recording_tracer(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    _EXPORTER.clear()
    monkeypatch.setattr(adk_module, "_TRACER", _PROVIDER.get_tracer("evidence-test"))
    return _EXPORTER


def _spec() -> TargetSpec:
    return TargetSpec.model_validate({"tier": "tier1_adk", "url": "http://localhost:8001"})


def _valid_agent_card() -> dict[str, Any]:
    return {
        "name": "naive-target-agent",
        "description": "Customer-support bot under audit.",
        "url": "http://localhost:8001/",
        "version": "0.1.0",
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "support", "name": "support", "description": "d", "tags": ["support"]}],
        "protocolVersion": "0.3.0",
    }


def _jsonrpc_message_response(text: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": "0",
        "result": {
            "kind": "message",
            "role": "agent",
            "messageId": "m-1",
            "parts": [{"kind": "text", "text": text}],
        },
    }


def _mock_card() -> None:
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )


_FAULT_CONFIG = {"kind": "prompt_injection", "attack": "role_hijacking", "payload": "X"}


@respx.mock
async def test_invoke_reports_32hex_trace_id_in_metadata() -> None:
    _mock_card()
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(200, json=_jsonrpc_message_response("ok"))
    )
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert _HEX32.fullmatch(result.metadata["trace_id"]), result.metadata
    await adapter.disconnect()


@respx.mock
async def test_outgoing_jsonrpc_post_carries_matching_traceparent() -> None:
    _mock_card()
    captured: dict[str, str] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["traceparent"] = request.headers.get("traceparent", "")
        return httpx.Response(200, json=_jsonrpc_message_response("ok"))

    respx.post("http://localhost:8001/").mock(side_effect=_capture)
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert captured["traceparent"], "JSON-RPC POST must carry traceparent"
    assert result.metadata["trace_id"] in captured["traceparent"]
    await adapter.disconnect()


@respx.mock
async def test_fault_config_registers_then_tears_down_hook() -> None:
    _mock_card()
    calls: list[str] = []

    def _hook_post(request: httpx.Request) -> httpx.Response:
        calls.append("register")
        assert json.loads(request.content)["fault_config"] == _FAULT_CONFIG
        return httpx.Response(200, json={"registration_id": "reg-1"})

    def _rpc(request: httpx.Request) -> httpx.Response:
        calls.append("invoke")
        return httpx.Response(200, json=_jsonrpc_message_response("ok"))

    def _hook_delete(request: httpx.Request) -> httpx.Response:
        calls.append("teardown")
        return httpx.Response(200, json={"status": "removed"})

    respx.post("http://localhost:8001/hooks/adk").mock(side_effect=_hook_post)
    respx.post("http://localhost:8001/").mock(side_effect=_rpc)
    respx.delete("http://localhost:8001/hooks/adk/reg-1").mock(side_effect=_hook_delete)

    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi", fault_config=_FAULT_CONFIG))
    assert calls == ["register", "invoke", "teardown"]
    assert result.metadata["fault_delivered"] is True
    await adapter.disconnect()


@respx.mock
async def test_undeliverable_fault_raises_not_silent() -> None:
    """Target without hooks (404) -> FaultDeliveryError. Invoking anyway would
    record a healthy response as if the attack ran — a silently inflated pass."""
    _mock_card()
    respx.post("http://localhost:8001/hooks/adk").mock(
        return_value=httpx.Response(404, json={"detail": "fault hooks disabled"})
    )
    rpc = respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(200, json=_jsonrpc_message_response("ok"))
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(FaultDeliveryError, match="hooks"):
        await adapter.invoke(AdapterInvocation(prompt="hi", fault_config=_FAULT_CONFIG))
    assert rpc.call_count == 0, "must NOT invoke the target after failed fault delivery"
    await adapter.disconnect()


@respx.mock
async def test_no_fault_config_skips_hook_surface_entirely() -> None:
    _mock_card()
    hook = respx.post("http://localhost:8001/hooks/adk").mock(
        return_value=httpx.Response(200, json={"registration_id": "nope"})
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(200, json=_jsonrpc_message_response("ok"))
    )
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert hook.call_count == 0
    assert "fault_delivered" not in result.metadata
    await adapter.disconnect()
