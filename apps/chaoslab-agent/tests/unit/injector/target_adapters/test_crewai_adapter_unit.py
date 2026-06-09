"""Unit tests for CrewAIAdapter — respx-mocked HTTP transport.

Follows the round-2 LangChain pattern: lock VALUES not just presence, behavior
probes instead of private-attr inspection, exact assertions where deterministic,
all lifecycle edges (disconnect-before-connect, idempotent, reconnect-after-
disconnect). The shared `_common.py` helpers (bearer_headers / coerce /
raise_for_status / record_and_raise) already have their own test coverage
in test__common.py — we don't re-test them here.
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
from chaoslab_agent.injector.target_adapters import AdapterTier, CrewAIAdapter, TargetSpec
from chaoslab_agent.injector.target_adapters.base import AdapterInvocation


def _spec(**overrides: Any) -> TargetSpec:
    payload: dict[str, Any] = {"tier": "tier2_crewai", "url": "http://localhost:8003"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


def _crew_info_body() -> dict[str, Any]:
    return {
        "name": "research-crew",
        "tools": ["calc", "search"],
        "hooks": ["before_tool_call"],
    }


# ---------------------------------------------------------------------------
# connect() — discovery via /crew/info
# ---------------------------------------------------------------------------


@respx.mock
async def test_connect_succeeds_and_fingerprint_exposes_crew_metadata() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    adapter = CrewAIAdapter(spec=_spec())
    await adapter.connect()
    fp = await adapter.fingerprint()
    assert fp.tier == AdapterTier.TIER2_CREWAI
    assert fp.framework == "crewai"
    assert fp.discovery_path == "crew_info"
    sig = fp.behavioral_signals or {}
    assert sig.get("crew_name") == "research-crew"
    assert sig.get("tool_count") == 2
    assert sig.get("hooks_available") is True


@respx.mock
async def test_connect_idempotent_when_called_twice() -> None:
    route = respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    adapter = CrewAIAdapter(spec=_spec())
    await adapter.connect()
    await adapter.connect()
    assert route.call_count == 1


@respx.mock
async def test_connect_404_raises_discovery_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(return_value=httpx.Response(404))
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="HTTP 404"):
        await adapter.connect()


@respx.mock
async def test_connect_unreachable_raises_connection_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="failed to reach CrewAI"):
        await adapter.connect()


@respx.mock
async def test_fingerprint_hooks_available_false_when_target_omits_hooks() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json={"name": "no-hooks", "tools": []})
    )
    adapter = CrewAIAdapter(spec=_spec())
    fp = await adapter.fingerprint()
    assert (fp.behavioral_signals or {}).get("hooks_available") is False
    assert (fp.behavioral_signals or {}).get("tool_count") == 0


# ---------------------------------------------------------------------------
# invoke() — kickoff + polling + termination states
# ---------------------------------------------------------------------------


@respx.mock
async def test_invoke_kickoffs_with_inputs_prompt_and_polls_to_completion() -> None:
    """BDD: POST /kickoff with body `{"inputs": {"prompt": ...}}` → poll until
    status=completed. Polling exactly 3 times locks the call-count contract."""
    import json as _json

    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    kickoff_route = respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"kickoff_id": "abc123"})
    )
    poll_route = respx.get("http://localhost:8003/kickoff/abc123").mock(
        side_effect=[
            httpx.Response(200, json={"status": "in_progress"}),
            httpx.Response(200, json={"status": "in_progress"}),
            httpx.Response(200, json={"status": "completed", "result": "final answer"}),
        ]
    )

    adapter = CrewAIAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="Find news"))

    assert kickoff_route.call_count == 1
    assert poll_route.call_count == 3
    assert result.response == "final answer"
    assert len(result.span_ids) == 1
    assert result.duration_ms >= 0.0
    assert result.metadata["output_coerced"] is False
    assert result.metadata["crew_name"] == "research-crew"
    body = _json.loads(kickoff_route.calls.last.request.content)
    assert body == {"inputs": {"prompt": "Find news"}}


@respx.mock
async def test_invoke_kickoff_missing_kickoff_id_raises_invocation_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"queued_at": "2026-06-09T19:00:00Z"})
    )
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="missing kickoff_id"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_kickoff_422_raises_invocation_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(422, text='{"detail":"invalid inputs"}')
    )
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="422"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_kickoff_503_raises_connection_error() -> None:
    """5xx → AdapterConnectionError (retryable) — round-2 SFH-I1."""
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(503, text="upstream busy")
    )
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="503"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_failed_status_raises_invocation_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"kickoff_id": "x1"})
    )
    respx.get("http://localhost:8003/kickoff/x1").mock(
        return_value=httpx.Response(200, json={"status": "failed", "error": "tool unavailable"})
    )
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="kickoff failed"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_dict_result_coerced_to_canonical_json() -> None:
    """Round-2 SFH-B1: dict result rendered as canonical JSON, not Python repr."""
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"kickoff_id": "x1"})
    )
    respx.get("http://localhost:8003/kickoff/x1").mock(
        return_value=httpx.Response(200, json={"status": "completed", "result": {"answer": 4}})
    )
    adapter = CrewAIAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == '{"answer": 4}'
    assert result.metadata["output_coerced"] is True


@respx.mock
async def test_invoke_transport_error_on_kickoff_raises_connection_error() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    respx.post("http://localhost:8003/kickoff").mock(side_effect=httpx.ConnectError("dead"))
    adapter = CrewAIAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="transport error"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


# ---------------------------------------------------------------------------
# fault-hook routing — webhook register / yield / teardown
# ---------------------------------------------------------------------------


@respx.mock
async def test_invoke_with_malformed_tool_output_fault_registers_and_tears_down_hook() -> None:
    """The webhook is POSTed before kickoff, the registration_id is surfaced
    in result.metadata, and a DELETE happens on the way out."""
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    register_route = respx.post("http://localhost:8003/hooks/before_tool_call").mock(
        return_value=httpx.Response(200, json={"registration_id": "reg-42"})
    )
    delete_route = respx.delete("http://localhost:8003/hooks/before_tool_call/reg-42").mock(
        return_value=httpx.Response(204)
    )
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"kickoff_id": "k1"})
    )
    respx.get("http://localhost:8003/kickoff/k1").mock(
        return_value=httpx.Response(200, json={"status": "completed", "result": "ok"})
    )
    adapter = CrewAIAdapter(spec=_spec())
    result = await adapter.invoke(
        AdapterInvocation(
            prompt="hi",
            fault_config={"kind": "malformed_tool_output", "tool_name": "calc"},
        )
    )
    assert register_route.call_count == 1
    assert delete_route.call_count == 1
    assert result.metadata["hook_registration_id"] == "reg-42"


@respx.mock
async def test_invoke_without_fault_does_not_register_hook() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    register_route = respx.post("http://localhost:8003/hooks/before_tool_call")
    respx.post("http://localhost:8003/kickoff").mock(
        return_value=httpx.Response(202, json={"kickoff_id": "k1"})
    )
    respx.get("http://localhost:8003/kickoff/k1").mock(
        return_value=httpx.Response(200, json={"status": "completed", "result": "ok"})
    )
    adapter = CrewAIAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert register_route.call_count == 0
    assert result.metadata["hook_registration_id"] is None


# ---------------------------------------------------------------------------
# lifecycle — disconnect-before-connect, idempotent, reconnect-after-disconnect
# ---------------------------------------------------------------------------


async def test_disconnect_without_prior_connect_is_safe() -> None:
    adapter = CrewAIAdapter(spec=_spec())
    await adapter.disconnect()  # must not raise


@respx.mock
async def test_disconnect_is_idempotent() -> None:
    respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    adapter = CrewAIAdapter(spec=_spec())
    await adapter.connect()
    await adapter.disconnect()
    await adapter.disconnect()  # must not raise


@respx.mock
async def test_disconnect_then_fingerprint_reconnects() -> None:
    schema_route = respx.get("http://localhost:8003/crew/info").mock(
        return_value=httpx.Response(200, json=_crew_info_body())
    )
    adapter = CrewAIAdapter(spec=_spec())
    await adapter.connect()
    assert schema_route.call_count == 1
    await adapter.disconnect()
    await adapter.fingerprint()  # reconnects under the hood
    assert schema_route.call_count == 2


def test_crewai_adapter_is_exported_from_package() -> None:
    from chaoslab_agent.injector import target_adapters

    assert hasattr(target_adapters, "CrewAIAdapter")
    assert "CrewAIAdapter" in target_adapters.__all__
