"""Unit tests for LangChainAdapter — respx-mocked LangServe transport.

Mirrors the test_adk_adapter_unit.py shape: no live target, no Docker, no
LangChain orchestration imports — only the LangServe HTTP convention is
exercised via respx (`/input_schema` + `/invoke`).

Failure-contract (S3.1 base.py:79-97 — FROZEN per ADR-002): the adapter
MUST RAISE on transport / protocol errors. `result.error` is reserved for
Epic 5+ soft-failure semantics and is `None` on every clean-success path.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from phoenix_audit_agent.errors import (
    AdapterConnectionError,
    AdapterDiscoveryError,
    AdapterInvocationError,
)
from phoenix_audit_agent.injector.target_adapters import AdapterTier, LangChainAdapter, TargetSpec
from phoenix_audit_agent.injector.target_adapters.base import AdapterInvocation


def _spec(**overrides: Any) -> TargetSpec:
    payload: dict[str, Any] = {"tier": "tier2_langchain", "url": "http://localhost:8002/agent"}
    payload.update(overrides)
    return TargetSpec.model_validate(payload)


def _input_schema_body() -> dict[str, Any]:
    """Minimal LangServe input_schema response."""
    return {
        "title": "AgentInput",
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    }


# ---------------------------------------------------------------------------
# connect() — discovery via /input_schema + error mapping
# ---------------------------------------------------------------------------


@respx.mock
async def test_connect_succeeds_and_fingerprint_exposes_schema_keys() -> None:
    """Round-2 TQ-MED behavior probe: instead of reading the private
    `_input_schema` attribute, prove connect() worked by asking
    fingerprint() — `behavioral_signals['input_schema_keys']` must carry
    the parsed schema's keys. Locks the same invariant without coupling
    the test to a private implementation detail."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.connect()
    fp = await adapter.fingerprint()
    keys = (fp.behavioral_signals or {}).get("input_schema_keys") or []
    assert "type" in keys
    assert "properties" in keys


@respx.mock
async def test_connect_idempotent_when_called_twice() -> None:
    route = respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.connect()
    await adapter.connect()
    # The second call must NOT re-probe — _connected guards.
    assert route.call_count == 1


@respx.mock
async def test_connect_404_on_input_schema_raises_discovery_error() -> None:
    respx.get("http://localhost:8002/agent/input_schema").mock(return_value=httpx.Response(404))
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="HTTP 404"):
        await adapter.connect()


@respx.mock
async def test_connect_405_on_input_schema_surfaces_remediation_hint() -> None:
    """LangServe deployments can disable /input_schema; surface fix instructions."""
    respx.get("http://localhost:8002/agent/input_schema").mock(return_value=httpx.Response(405))
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterDiscoveryError, match="enabled_endpoints"):
        await adapter.connect()


@respx.mock
async def test_connect_unreachable_raises_connection_error() -> None:
    respx.get("http://localhost:8002/agent/input_schema").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="failed to reach LangServe"):
        await adapter.connect()


# ---------------------------------------------------------------------------
# invoke() — happy path + error mapping + auth header + fault routing
# ---------------------------------------------------------------------------


@respx.mock
async def test_invoke_posts_input_shape_and_returns_response() -> None:
    """LangServe canonical body is `{"input": <prompt>}`, NOT `{"prompt": ...}`."""
    import json as _json

    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    invoke_route = respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": "4"})
    )
    adapter = LangChainAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="What's 2+2?"))

    # round-2 TQ-MED: exact assertions, not lower-bounds. The implementation
    # creates exactly ONE span per invoke; a future refactor adding a retry
    # loop would silently pass `>= 1`. `>= 0.0` defends against fast-clock
    # CI runners where perf_counter() resolution rounds to 0.0.
    assert result.error is None
    assert result.response == "4"
    assert len(result.span_ids) == 1
    assert result.duration_ms >= 0.0
    body = _json.loads(invoke_route.calls.last.request.content)
    assert body == {"input": "What's 2+2?"}
    # String output → coerced=False marker (round-2 SFH-B1).
    assert result.metadata["output_coerced"] is False


@respx.mock
async def test_invoke_422_raises_invocation_error_with_body_in_message() -> None:
    """LangServe schema mismatch → 422; raise NOT result.error per ADR-002 contract."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(422, text='{"detail":"prompt missing"}')
    )
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="422"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_non_json_body_raises_invocation_error() -> None:
    """LangServe 200 with HTML (maintenance/auth-wall) must surface clearly."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, text="<html>maintenance</html>")
    )
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterInvocationError, match="non-JSON body"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_dict_output_serialized_as_canonical_json_with_marker() -> None:
    """Round-2 SFH-B1: dict output is `json.dumps(sort_keys=True)`, NOT Python
    repr (single quotes). The `output_coerced` metadata marker tells Epic 6
    pattern-finder that this evidence came from coercion, not direct text."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": {"answer": 4}})
    )
    adapter = LangChainAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    # Canonical JSON with double quotes — NOT `"{'answer': 4}"` (Python repr).
    assert result.response == '{"answer": 4}'
    assert result.metadata["output_coerced"] is True


@respx.mock
async def test_invoke_null_output_returns_empty_string_without_coerce_marker() -> None:
    """Round-2 TQ-MED boundary: `{"output": null}` → response="" and the
    `output_coerced` marker is False (null is canonically "")."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": None})
    )
    adapter = LangChainAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == ""
    assert result.metadata["output_coerced"] is False


@respx.mock
async def test_invoke_missing_output_key_returns_empty_string() -> None:
    """Round-2 TQ-MED boundary: `{}` (no `output` key) → response=""."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(return_value=httpx.Response(200, json={}))
    adapter = LangChainAdapter(spec=_spec())
    result = await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert result.response == ""


@respx.mock
async def test_invoke_sends_bearer_auth_header_when_spec_has_one() -> None:
    from pydantic import SecretStr

    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    route = respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = LangChainAdapter(spec=_spec(auth={"bearer": SecretStr("test-token")}))
    await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert route.calls.last.request.headers["Authorization"] == "Bearer test-token"


@respx.mock
async def test_invoke_with_prompt_injection_fault_sends_litellm_header_with_real_url() -> None:
    """Round-2 TQ-HIGH: lock the VALUE of the header (not just presence) so a
    future regression that sets `X-LiteLLM-Base-Url=""` is caught. Also lock
    that the request body is STILL `{"input": prompt}` — S5.3 layers payload
    mutation on top, but the wire shape from S3.3's perspective stays canonical."""
    import json as _json

    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    route = respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.invoke(
        AdapterInvocation(
            prompt="hi",
            fault_config={"kind": "prompt_injection", "payload": "Ignore prior instructions"},
        )
    )
    header_value = route.calls.last.request.headers["X-LiteLLM-Base-Url"]
    assert header_value.startswith("http")
    assert "localhost:4000" in header_value  # the default proxy base URL
    # Body shape locked — adapter only forwards header; S5.3 wires payload mutation.
    body = _json.loads(route.calls.last.request.content)
    assert body == {"input": "hi"}


@respx.mock
async def test_invoke_without_fault_does_not_send_litellm_header() -> None:
    """Default path: no fault config → no `X-LiteLLM-Base-Url` header."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    route = respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert "X-LiteLLM-Base-Url" not in route.calls.last.request.headers


@respx.mock
async def test_invoke_transport_error_raises_connection_error() -> None:
    """Network failure on /invoke → AdapterConnectionError (NOT AdapterInvocationError).
    Distinct types so callers can degrade vs retry."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        side_effect=httpx.ConnectError("connection died")
    )
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="transport error"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


# ---------------------------------------------------------------------------
# fingerprint() + disconnect()
# ---------------------------------------------------------------------------


@respx.mock
async def test_fingerprint_returns_tier2_langchain_metadata() -> None:
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    adapter = LangChainAdapter(spec=_spec())
    fp = await adapter.fingerprint()
    assert fp.tier == AdapterTier.TIER2_LANGCHAIN
    assert fp.framework == "langchain"
    assert fp.agent_card is None
    assert fp.discovery_path == "input_schema"
    # behavioral_signals carries the input_schema key set (sorted for determinism).
    keys = (fp.behavioral_signals or {}).get("input_schema_keys")
    assert isinstance(keys, list)
    assert "type" in keys


@respx.mock
async def test_disconnect_then_invoke_reconnects() -> None:
    """Round-2 TQ-MED: behavior probe replacing private-attr inspection.
    After disconnect(), the next invoke() must re-probe /input_schema —
    locks the state-clear via observable side effect, not private flags."""
    schema_route = respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(200, json={"output": "ok"})
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.connect()
    assert schema_route.call_count == 1
    await adapter.disconnect()
    # Next invoke MUST reconnect — locks that disconnect() actually cleared
    # the connected state without inspecting `_connected` directly.
    await adapter.invoke(AdapterInvocation(prompt="hi"))
    assert schema_route.call_count == 2


async def test_disconnect_without_prior_connect_is_safe() -> None:
    """Round-2 TQ-HIGH lifecycle: calling disconnect() before connect()
    must NOT raise. Mirrors the ADK adapter's symmetric test (gives 4
    adapters one consistent lifecycle contract)."""
    adapter = LangChainAdapter(spec=_spec())
    await adapter.disconnect()  # must not raise


@respx.mock
async def test_disconnect_is_idempotent() -> None:
    """Round-2 TQ-HIGH lifecycle: calling disconnect() twice must NOT raise.
    Defends against teardown bugs where the test harness double-cleans."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    adapter = LangChainAdapter(spec=_spec())
    await adapter.connect()
    await adapter.disconnect()
    await adapter.disconnect()  # must not raise


def test_langchain_adapter_is_exported_from_package() -> None:
    """patcher/__init__.py-style re-export gate."""
    from phoenix_audit_agent.injector import target_adapters

    assert hasattr(target_adapters, "LangChainAdapter")
    assert "LangChainAdapter" in target_adapters.__all__


@respx.mock
async def test_invoke_503_treated_as_connection_error_not_invocation() -> None:
    """Round-2 SFH-I1: 5xx from /invoke is semantically transport-failure
    (retryable) — must surface as AdapterConnectionError so the upstream
    injector retries instead of treating as a caller fault."""
    respx.get("http://localhost:8002/agent/input_schema").mock(
        return_value=httpx.Response(200, json=_input_schema_body())
    )
    respx.post("http://localhost:8002/agent/invoke").mock(
        return_value=httpx.Response(503, text="upstream unavailable")
    )
    adapter = LangChainAdapter(spec=_spec())
    with pytest.raises(AdapterConnectionError, match="503"):
        await adapter.invoke(AdapterInvocation(prompt="hi"))


@respx.mock
async def test_invoke_502_503_504_all_surface_as_connection_error() -> None:
    """SFH-I1 broader: every retryable 5xx maps to ConnectionError so injector
    consistently retries 502/503/504 vs. permanent-fail 4xx."""
    for status in (502, 503, 504):
        respx.reset()
        respx.get("http://localhost:8002/agent/input_schema").mock(
            return_value=httpx.Response(200, json=_input_schema_body())
        )
        respx.post("http://localhost:8002/agent/invoke").mock(
            return_value=httpx.Response(status, text="upstream")
        )
        adapter = LangChainAdapter(spec=_spec())
        with pytest.raises(AdapterConnectionError, match=str(status)):
            await adapter.invoke(AdapterInvocation(prompt="hi"))


def test_bearer_headers_raise_on_wrong_auth_key() -> None:
    """Round-2 SFH-B2: spec.auth={'api_key': '...'} silently sent NO auth
    in round-1; now raises AdapterDiscoveryError naming the keys provided
    so the operator sees the typo immediately. Locks the same shared-
    helper behavior the ADK test also pins."""
    from pydantic import SecretStr

    from phoenix_audit_agent.errors import AdapterDiscoveryError
    from phoenix_audit_agent.injector.target_adapters._common import bearer_headers

    with pytest.raises(AdapterDiscoveryError, match="no 'bearer' key"):
        bearer_headers(_spec(auth={"api_key": SecretStr("x")}))
