"""Unit tests for OpenAISDKAdapter — respx-mocked HTTP transport.

Follows the round-2 LangChain + CrewAI pattern: lock VALUES not just
presence, behavior probes (no private-attr inspection), exact assertions
where deterministic, lifecycle tests. Shared `_common.py` and
`_webhook_fault_proxy.py` already have their own coverage in their own
test files — we don't re-test their internals here.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from chaoslab_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from chaoslab_agent.injector.target_adapters import (
    AdapterTier,
    OpenAISDKAdapter,
    TargetSpec,
)
from chaoslab_agent.injector.target_adapters.base import AdapterInvocation


def _spec(**overrides: Any) -> TargetSpec:
    payload: dict[str, Any] = {"tier": "tier2_openai_sdk", "url": "http://localhost:8004"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


def _agents_body() -> list[dict[str, Any]]:
    return [
        {"name": "weather-agent", "tools": ["weather"], "hooks": ["function_tool"]},
        {"name": "summary-agent", "tools": ["search"], "hooks": []},
    ]


# ---------------------------------------------------------------------------
# connect() — discovery via /agents listing
# ---------------------------------------------------------------------------


@respx.mock
async def test_connect_succeeds_and_fingerprint_exposes_agents_metadata() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    await adapter.connect()
    fp = await adapter.fingerprint()
    assert fp.tier == AdapterTier.TIER2_OPENAI_SDK
    assert fp.framework == "openai-agents"
    assert fp.discovery_path == "agents_listing"
    sig = fp.behavioral_signals or {}
    assert sig.get("agent_count") == 2
    assert "weather-agent" in sig.get("agent_names", [])
    assert sig.get("hooks_available") is True


@respx.mock
async def test_connect_idempotent_when_called_twice() -> None:
    route = respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    await adapter.connect()
    await adapter.connect()
    assert route.call_count == 1


@respx.mock
async def test_connect_404_raises_discovery_error() -> None:
    respx.get("http://localhost:8004/agents").mock(return_value=httpx.Response(404))
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="HTTP 404"):
        await adapter.connect()


@respx.mock
async def test_connect_empty_agents_list_raises_discovery_error() -> None:
    """An empty `/agents` listing means there's nothing to /run against —
    fail loud at connect-time so the operator sees the misconfiguration
    BEFORE the first invoke."""
    respx.get("http://localhost:8004/agents").mock(return_value=httpx.Response(200, json=[]))
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="empty"):
        await adapter.connect()


@respx.mock
async def test_connect_non_list_payload_raises_discovery_error() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json={"agents": []})
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="non-list"):
        await adapter.connect()


@respx.mock
async def test_connect_unreachable_raises_connection_error() -> None:
    respx.get("http://localhost:8004/agents").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="failed to reach OpenAI"):
        await adapter.connect()


# ---------------------------------------------------------------------------
# invoke() — body shape + error mapping + auth + fault routing + lifecycle
# ---------------------------------------------------------------------------


@respx.mock
async def test_invoke_posts_run_with_input_and_default_agent_name() -> None:
    """Body shape: `{"input": prompt, "agent_name": <first agent's name>}`."""
    import json as _json

    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    route = respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(200, json={"output": "rain today"})
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="What's the weather?"))

    assert result.error is None
    assert result.response == "rain today"
    assert len(result.span_ids) == 1
    assert result.duration_ms >= 0.0
    assert result.metadata["output_coerced"] is False
    assert result.metadata["agent_name"] == "weather-agent"
    body = _json.loads(route.calls.last.request.content)
    assert body == {"input": "What's the weather?", "agent_name": "weather-agent"}


@respx.mock
async def test_invoke_422_raises_invocation_error_carrying_body() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(422, text='{"detail":"input required"}')
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="422"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_503_raises_connection_error() -> None:
    """5xx → AdapterConnectionError (retryable) — SFH-I1."""
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(503, text="upstream busy")
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="503"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_dict_output_coerced_to_canonical_json() -> None:
    """Round-2 SFH-B1: dict result rendered as canonical JSON, not Python repr."""
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(200, json={"output": {"answer": 4}})
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == '{"answer": 4}'
    assert result.metadata["output_coerced"] is True


@respx.mock
async def test_invoke_transport_error_on_run_raises_connection_error() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    respx.post("http://localhost:8004/run").mock(side_effect=httpx.ConnectError("dead"))
    adapter = OpenAISDKAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="transport error"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_with_malformed_tool_fault_registers_and_tears_down_hook() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    register = respx.post("http://localhost:8004/hooks/function_tool").mock(
        return_value=httpx.Response(200, json={"registration_id": "reg-9"})
    )
    delete = respx.delete("http://localhost:8004/hooks/function_tool/reg-9").mock(
        return_value=httpx.Response(204)
    )
    respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    result = await adapter.invoke(
        AdapterInvocation(
            prompt="hi",
            fault_config={"kind": "malformed_tool_output", "tool_name": "weather"},
        )
    )
    assert register.call_count == 1
    assert delete.call_count == 1
    assert result.metadata["hook_registration_id"] == "reg-9"


@respx.mock
async def test_invoke_without_fault_does_not_register_hook() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    register = respx.post("http://localhost:8004/hooks/function_tool")
    respx.post("http://localhost:8004/run").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert register.call_count == 0
    assert result.metadata["hook_registration_id"] is None


# ---------------------------------------------------------------------------
# lifecycle — disconnect-before-connect, idempotent, reconnect-after-disconnect
# ---------------------------------------------------------------------------


async def test_disconnect_without_prior_connect_is_safe() -> None:
    adapter = OpenAISDKAdapter(spec=_spec())
    await adapter.disconnect()  # must not raise


@respx.mock
async def test_disconnect_is_idempotent() -> None:
    respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    await adapter.connect()
    await adapter.disconnect()
    await adapter.disconnect()  # must not raise


@respx.mock
async def test_disconnect_then_fingerprint_reconnects() -> None:
    schema_route = respx.get("http://localhost:8004/agents").mock(
        return_value=httpx.Response(200, json=_agents_body())
    )
    adapter = OpenAISDKAdapter(spec=_spec())
    await adapter.connect()
    assert schema_route.call_count == 1
    await adapter.disconnect()
    await adapter.fingerprint()
    assert schema_route.call_count == 2


def test_openai_sdk_adapter_is_exported_from_package() -> None:
    from chaoslab_agent.injector import target_adapters

    assert hasattr(target_adapters, "OpenAISDKAdapter")
    assert "OpenAISDKAdapter" in target_adapters.__all__
