"""Unit tests for ADKAdapter — respx-mocked transport (no live target).

These tests exercise the AgentCard discovery + JSON-RPC happy/sad paths
without touching the network. The integration suite (sibling file in
tests/integration) exercises the same code against the real target_agent
service on localhost:8001.

Failure-contract reminder: per the frozen S3.1 contract (base.py:79-97)
the adapter MUST RAISE on transport / protocol errors. ``result.error``
is reserved for Epic 5+ soft-failure and is always ``None`` today.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from phoenix_audit_agent.errors import AdapterConnectionError, AdapterDiscoveryError
from phoenix_audit_agent.injector.target_adapters import AdapterTier, ADKAdapter, TargetSpec
from phoenix_audit_agent.injector.target_adapters.adk_adapter import _bearer_headers
from phoenix_audit_agent.injector.target_adapters.base import AdapterInvocation


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


def _jsonrpc_task_response(
    *, status_message_text: str | None, history: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Build a JSON-RPC response whose result is a Task (long-running flow)."""
    status: dict[str, Any] = {"state": "completed"}
    if status_message_text is not None:
        status["message"] = {
            "kind": "message",
            "role": "agent",
            "messageId": "task-status-msg",
            "parts": [{"kind": "text", "text": status_message_text}],
        }
    return {
        "jsonrpc": "2.0",
        "id": "0",
        "result": {
            "kind": "task",
            "id": "task-1",
            "contextId": "ctx-1",
            "status": status,
            "history": history or [],
        },
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
    """Pydantic validation on AgentCard rejects an incomplete payload."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json={"name": "x"})
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterDiscoveryError, match="malformed AgentCard"):
        await adapter.connect()


@respx.mock
async def test_connect_with_bearer_auth_propagates_header() -> None:
    """spec.auth bearer must land in Authorization on the GET /.well-known/agent-card.json."""

    def _capture(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer secret-token-abc"
        return httpx.Response(200, json=_valid_agent_card())

    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(side_effect=_capture)
    adapter = ADKAdapter(_spec(auth={"bearer": "secret-token-abc"}))
    await adapter.connect()
    await adapter.disconnect()


@respx.mock
async def test_invoke_bearer_auth_propagates_on_jsonrpc_post() -> None:
    """spec.auth bearer must ALSO land on the JSON-RPC POST, not just the discovery GET.

    silent-failure-hunter PR #41 Round-1 #5: without this test the Authorization
    header could silently drop on every invoke if a2a-sdk's JSONRPC transport
    bypassed httpx.AsyncClient defaults.
    """

    def _capture_get(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer api-token-xyz"
        return httpx.Response(200, json=_valid_agent_card())

    def _capture_post(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer api-token-xyz", (
            f"Authorization header dropped on POST; got {dict(request.headers)!r}"
        )
        return httpx.Response(200, json=_jsonrpc_message_response("ok"))

    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(side_effect=_capture_get)
    respx.post("http://localhost:8001/").mock(side_effect=_capture_post)
    adapter = ADKAdapter(_spec(auth={"bearer": "api-token-xyz"}))
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == "ok"
    await adapter.disconnect()


@respx.mock
async def test_invoke_returns_response_text_from_message() -> None:
    """JSON-RPC happy path: target returns a Message with TextPart."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(
            200, json=_jsonrpc_message_response("Your order ships tomorrow.")
        )
    )
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="status?"))
    assert result.error is None
    assert result.response == "Your order ships tomorrow."
    assert len(result.span_ids) >= 1
    assert result.duration_ms > 0.0
    assert result.metadata["agent_card_name"] == "naive-target-agent"
    await adapter.disconnect()


@respx.mock
async def test_invoke_extracts_text_from_task_status_message() -> None:
    """Task result with status.message → text comes from status.message."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(
            200, json=_jsonrpc_task_response(status_message_text="processed via Task")
        )
    )
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == "processed via Task"
    assert result.error is None
    await adapter.disconnect()


@respx.mock
async def test_invoke_task_history_fallback_filters_user_role() -> None:
    """Task with no status.message → fall back to history, ignoring the user prompt echo.

    code-reviewer + test-analyzer PR #41 Round-1 (2-way): the previous
    implementation concatenated ALL history messages, which would echo the
    user's prompt back as if it were the agent's reply.
    """
    user_echo = {
        "kind": "message",
        "role": "user",
        "messageId": "u-1",
        "parts": [{"kind": "text", "text": "USER PROMPT — must not appear"}],
    }
    agent_reply = {
        "kind": "message",
        "role": "agent",
        "messageId": "a-1",
        "parts": [{"kind": "text", "text": "agent answer"}],
    }
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(
            200,
            json=_jsonrpc_task_response(status_message_text=None, history=[user_echo, agent_reply]),
        )
    )
    adapter = ADKAdapter(_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="probe"))
    assert "USER PROMPT" not in result.response
    assert result.response == "agent answer"
    await adapter.disconnect()


@respx.mock
async def test_invoke_jsonrpc_error_response_raises_connection_error() -> None:
    """Per FROZEN S3.1 contract: transport/protocol errors RAISE; no soft fail."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": "0",
                "error": {"code": -32603, "message": "internal target error"},
            },
        )
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterConnectionError, match="A2A protocol error"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))
    await adapter.disconnect()


@respx.mock
async def test_invoke_http_500_on_jsonrpc_post_raises_connection_error() -> None:
    """HTTP 5xx on the JSON-RPC POST must RAISE, never silently land in result.error.

    Convergent finding (silent-failure + code + test reviewers): the broad
    `except Exception` in the prior implementation would have swallowed this
    as `result.error = "..."` — that violates the S3.1 contract.
    """
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(return_value=httpx.Response(500, text="boom"))
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterConnectionError):
        await adapter.invoke(AdapterInvocation(prompt="hi"))
    await adapter.disconnect()


@respx.mock
async def test_invoke_auto_connects_when_not_connected() -> None:
    """invoke() without prior connect() must auto-connect, not raise."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    respx.post("http://localhost:8001/").mock(
        return_value=httpx.Response(200, json=_jsonrpc_message_response("ok"))
    )
    adapter = ADKAdapter(_spec())
    assert adapter._connected is False
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert adapter._connected is True
    assert result.response == "ok"
    await adapter.disconnect()


@respx.mock
async def test_invoke_auto_connect_failure_propagates_discovery_error() -> None:
    """If invoke() triggers an auto-connect that hits 404, the discovery error
    propagates — NOT absorbed into result.error.

    test-analyzer PR #41 Round-1 Sev 5.
    """
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(404)
    )
    adapter = ADKAdapter(_spec())
    with pytest.raises(AdapterDiscoveryError, match="no AgentCard"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


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
    """The Injector's session_id must reach the target as Message.contextId."""
    respx.get("http://localhost:8001/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_valid_agent_card())
    )
    captured: dict[str, Any] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_jsonrpc_message_response("ok"))

    respx.post("http://localhost:8001/").mock(side_effect=_capture)
    adapter = ADKAdapter(_spec())
    await adapter.invoke(AdapterInvocation(prompt="hi", session_id="sess-xyz"))
    assert captured["body"]["params"]["message"]["contextId"] == "sess-xyz"
    await adapter.disconnect()


async def test_auth_dict_without_bearer_raises_discovery_error() -> None:
    """Round-2 review (SFH-B2 + CR-#3): silently sending NO auth for a
    non-`bearer` key dict is a footgun — pattern #2. The shared
    `_common.bearer_headers` now raises AdapterDiscoveryError naming the
    keys that WERE provided so the operator sees the typo immediately."""
    from phoenix_audit_agent.errors import AdapterDiscoveryError

    spec = _spec(auth={"x-api-key": "alt-scheme-not-supported-yet"})
    with pytest.raises(AdapterDiscoveryError, match="no 'bearer' key"):
        _bearer_headers(spec)
