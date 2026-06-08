"""Unit tests for ADKAdapter — respx-mocked transport (no live target).

These tests exercise the AgentCard discovery + JSON-RPC happy/sad paths
without touching the network. The integration suite (sibling file in
tests/integration) exercises the same code against the real target_agent
service on localhost:8001.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from chaoslab_agent.errors import AdapterDiscoveryError
from chaoslab_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from chaoslab_agent.injector.target_adapters.base import AdapterInvocation


def _spec(**overrides: Any) -> TargetSpec:
    payload: dict[str, Any] = {"tier": "tier1_adk", "url": "http://localhost:8001"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


def _valid_agent_card() -> dict[str, Any]:
    """Minimal AgentCard satisfying a2a-sdk's required fields."""
    return {
        "name": "naive-target-agent",
        "description": "Customer-support bot under audit.",
        "url": "http://localhost:8001/",
        "version": "0.1.0",
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "support",
                "name": "support",
                "description": "Answer support questions.",
                "tags": ["support"],
            }
        ],
        "protocolVersion": "0.3.0",
    }


@respx.mock
async def test_connect_parses_agent_card() -> None:
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    adapter = ADKAdapter(_spec())
    await adapter.connect()
    assert adapter._connected is True
    assert adapter._agent_card is not None
    assert adapter._agent_card["name"] == "naive-target-agent"
    await adapter.disconnect()


@respx.mock
async def test_connect_missing_card_raises_discovery_error() -> None:
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterDiscoveryError, match="no AgentCard"):
        await adapter.connect()
    assert adapter._connected is False


@respx.mock
async def test_connect_malformed_json_raises_discovery_error() -> None:
    """a2a-sdk's JSON decoder raises A2AClientJSONError; we wrap as AdapterDiscoveryError."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, content=b"not-json-{[")
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterDiscoveryError, match="malformed AgentCard"):
        await adapter.connect()


@respx.mock
async def test_connect_missing_required_card_fields_raises_discovery_error() -> None:
    """Pydantic validation on AgentCard rejects an incomplete payload, which a2a-sdk
    surfaces as A2AClientJSONError (it wraps both decode and validation paths)."""
    bad_card = {"name": "x"}  # missing every other required field
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=bad_card)
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterDiscoveryError, match="malformed AgentCard"):
        await adapter.connect()


@respx.mock
async def test_connect_with_bearer_auth_propagates_header() -> None:
    """When spec.auth has a bearer key, it must land in the Authorization header."""

    def _capture_route(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer secret-token-abc"
        return httpx.Response(200, json=_valid_agent_card())

    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(side_effect=_capture_route)
    adapter = ADKAdapter(_spec(auth={"bearer": "secret-token-abc"}))
    await adapter.connect()
    await adapter.disconnect()


@respx.mock
async def test_invoke_returns_response_text_from_message() -> None:
    """JSON-RPC happy path: target returns a Message with TextPart."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    a2a_response = {
        "jsonrpc": "2.0",
        "id": "0",
        "result": {
            "kind": "message",
            "role": "agent",
            "messageId": "msg-1",
            "parts": [{"kind": "text", "text": "Your order #123 ships tomorrow."}],
        },
    }
    respx.post("http://localhost:8001/").mock(return_value=httpx.Response(200, json=a2a_response))

    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="What's my order status?"))
    assert result.error is None
    assert result.response == "Your order #123 ships tomorrow."
    assert len(result.span_ids) >= 1
    assert result.duration_ms > 0.0
    assert result.metadata["agent_card_name"] == "naive-target-agent"
    await adapter.disconnect()


@respx.mock
async def test_invoke_handles_jsonrpc_error_response() -> None:
    """A2A error response surfaces in AdapterResult.error, not as an exception."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    a2a_error = {
        "jsonrpc": "2.0",
        "id": "0",
        "error": {"code": -32603, "message": "internal target error"},
    }
    respx.post("http://localhost:8001/").mock(return_value=httpx.Response(200, json=a2a_error))

    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.error is not None
    assert "internal target error" in result.error
    assert result.response == ""
    await adapter.disconnect()


@respx.mock
async def test_invoke_auto_connects_when_not_connected() -> None:
    """invoke() without prior connect() must auto-connect, not raise."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": "0",
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "messageId": "m",
                    "parts": [{"kind": "text", "text": "ok"}],
                },
            },
        )
    )
    adapter = ADKAdapter(_spec())
    assert adapter._connected is False
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert adapter._connected is True
    assert result.response == "ok"
    await adapter.disconnect()


@respx.mock
async def test_connect_is_idempotent() -> None:
    """Two consecutive connect() calls must not double-fetch the AgentCard."""
    route = respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    adapter = ADKAdapter(_spec())
    await adapter.connect()
    await adapter.connect()
    assert route.call_count == 1
    await adapter.disconnect()


async def test_disconnect_without_prior_connect_is_safe() -> None:
    """disconnect() must not raise on a never-connected adapter."""
    adapter = ADKAdapter(_spec())
    await adapter.disconnect()
    assert adapter._connected is False


@respx.mock
async def test_fingerprint_returns_tier1_with_framework_metadata() -> None:
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    adapter = ADKAdapter(_spec())
    fp = await adapter.fingerprint()
    assert fp.tier is AdapterTier.TIER1_ADK
    assert fp.framework == "google-adk"
    assert fp.discovery_path == "agent_card"
    assert fp.agent_card is not None
    assert fp.agent_card["name"] == "naive-target-agent"
    await adapter.disconnect()


@respx.mock
async def test_invoke_propagates_session_id_to_context() -> None:
    """The Injector's session_id (multi-turn fault scenarios) must reach the target."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    captured: dict[str, Any] = {}

    def _capture_request(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": "0",
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "messageId": "m",
                    "parts": [{"kind": "text", "text": "ok"}],
                },
            },
        )

    respx.post("http://localhost:8001/").mock(side_effect=_capture_request)

    adapter = ADKAdapter(_spec())
    await adapter.invoke(AdapterInvocation(prompt="hi", session_id="sess-xyz"))
    msg = captured["body"]["params"]["message"]
    assert msg.get("contextId") == "sess-xyz"
    await adapter.disconnect()
