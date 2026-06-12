"""Unit tests for the Tier-3 discovery chain (`_discovery.run_discovery_chain`).

Each probe is tested in isolation + the order-of-resolution invariant is
locked. The adapter-level tests (`test_http_blackbox_adapter_unit.py`)
then assume discovery works and focus on the invoke/fingerprint paths.
"""

from __future__ import annotations

import httpx
import respx

from phoenix_audit_agent.injector.target_adapters._discovery import run_discovery_chain


@respx.mock
async def test_agent_card_short_circuits_on_first_hit() -> None:
    """When `/.well-known/agent-card.json` returns 200, no later probe fires."""
    card_route = respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json={"name": "test-bot", "interfaces": []})
    )
    later_route = respx.get("http://x/.well-known/mcp.json")
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "agent_card"
    assert (result.payload or {}).get("name") == "test-bot"
    assert card_route.call_count == 1
    assert later_route.call_count == 0  # short-circuit


@respx.mock
async def test_mcp_well_known_falls_through_after_404_on_agent_card() -> None:
    """Both well-known card paths 404 → fall through to MCP."""
    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/mcp.json").mock(
        return_value=httpx.Response(200, json={"protocol_version": "2024-11-05"})
    )
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "mcp_well_known"
    # Dual-convention probe records each path it tried with the
    # `agent_card:<path>` prefix so operators can grep the diagnostics.
    assert "agent_card:/.well-known/agent-card.json" in result.probes_attempted
    assert "agent_card:/.well-known/agent.json" in result.probes_attempted
    assert "mcp_well_known" in result.probes_attempted


@respx.mock
async def test_agent_json_fallback_when_agent_card_json_404s() -> None:
    """A2A dual-convention: agents that follow the older RFC-8615 / Codelabs
    convention (e.g. Google Codelabs Weather Agent, A2A Playground) serve
    their card at `/.well-known/agent.json` — NOT `/.well-known/agent-card.json`
    (the A2A v1.0 path our own target-agent uses). Without this fallback,
    "Point Phoenix Audit at any production AI agent" is a lie — we crash on
    the handshake. Locks the second-chance probe at the same logical step
    (still `discovery_path == "agent_card"` so downstream code is unchanged).
    """
    card_v1_route = respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(404)
    )
    card_legacy_route = respx.get("http://x/.well-known/agent.json").mock(
        return_value=httpx.Response(
            200, json={"name": "weather-agent", "url": "http://x", "version": "1.0.0"}
        )
    )
    later_route = respx.get("http://x/.well-known/mcp.json")
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "agent_card"
    assert (result.payload or {}).get("name") == "weather-agent"
    assert card_v1_route.call_count == 1
    assert card_legacy_route.call_count == 1
    assert later_route.call_count == 0
    # The probes_attempted list should record both attempts for diagnostics.
    assert "agent_card:/.well-known/agent-card.json" in result.probes_attempted
    assert "agent_card:/.well-known/agent.json" in result.probes_attempted


@respx.mock
async def test_agent_card_v1_short_circuits_before_agent_json_legacy() -> None:
    """Order matters: when v1.0 (`agent-card.json`) is present, the legacy
    `agent.json` path MUST NOT be probed. Protects against accidental flip
    of probe order in a future refactor."""
    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json={"name": "phoenix-target", "interfaces": []})
    )
    legacy_route = respx.get("http://x/.well-known/agent.json")
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "agent_card"
    assert (result.payload or {}).get("name") == "phoenix-target"
    assert legacy_route.call_count == 0


@respx.mock
async def test_mcp_initialize_falls_through_when_both_well_known_404() -> None:
    """A 200 from POST /mcp with `result.serverInfo` wins."""
    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/mcp.json").mock(return_value=httpx.Response(404))
    respx.post("http://x/mcp").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "weather-mcp", "version": "0.1.0"},
                },
            },
        )
    )
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "mcp_initialize"
    assert "serverInfo" in (result.payload or {})


@respx.mock
async def test_openapi_falls_through_after_well_known_and_mcp_fail() -> None:
    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/mcp.json").mock(return_value=httpx.Response(404))
    respx.post("http://x/mcp").mock(return_value=httpx.Response(404))
    respx.get("http://x/openapi.json").mock(
        return_value=httpx.Response(200, json={"openapi": "3.0.0", "paths": {}})
    )
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "openapi"


@respx.mock
async def test_openapi_alternates_walk_through_failures() -> None:
    """When /openapi.json fails to parse, the chain tries /openapi.yaml etc."""
    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/mcp.json").mock(return_value=httpx.Response(404))
    respx.post("http://x/mcp").mock(return_value=httpx.Response(404))
    respx.get("http://x/openapi.json").mock(
        return_value=httpx.Response(200, text="not json at all")
    )
    respx.get("http://x/openapi.yaml").mock(return_value=httpx.Response(404))
    respx.get("http://x/swagger.json").mock(
        return_value=httpx.Response(200, json={"swagger": "2.0", "info": {"title": "x"}})
    )
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "openapi"
    assert (result.payload or {}).get("swagger") == "2.0"


@respx.mock
async def test_input_schema_falls_through_to_swagger_ui_last() -> None:
    """When every JSON probe fails, swagger_ui HTML is the last positive signal."""
    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/mcp.json").mock(return_value=httpx.Response(404))
    respx.post("http://x/mcp").mock(return_value=httpx.Response(404))
    for openapi_path in (
        "/openapi.json",
        "/openapi.yaml",
        "/swagger.json",
        "/v3/api-docs",
        "/api-docs",
    ):
        respx.get(f"http://x{openapi_path}").mock(return_value=httpx.Response(404))
    for is_path in (
        "/input_schema",
        "/agent/input_schema",
        "/chain/input_schema",
        "/runnable/input_schema",
    ):
        respx.get(f"http://x{is_path}").mock(return_value=httpx.Response(404))
    respx.get("http://x/swagger-ui").mock(return_value=httpx.Response(404))
    respx.get("http://x/docs").mock(return_value=httpx.Response(200, text="<html>docs</html>"))

    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "swagger_ui"
    assert (result.payload or {}).get("path") == "/docs"


@respx.mock
async def test_all_probes_fail_returns_none_discovery_path() -> None:
    """No 200 anywhere → discovery_path is None and the full attempted list is preserved."""
    respx.get(host="x").mock(return_value=httpx.Response(404))
    respx.post(host="x").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path is None
    # ≥6 probes registered in `probes_attempted` per the chain
    assert len(result.probes_attempted) >= 6
    # raw_responses must carry the per-URL status codes so the operator
    # sees the full trace in the AdapterDiscoveryError message.
    assert len(result.raw_responses) >= 6


@respx.mock
async def test_transport_error_does_not_abort_the_chain() -> None:
    """A connect failure on probe 1 marks it as -1 and keeps walking."""
    respx.get("http://x/.well-known/agent-card.json").mock(side_effect=httpx.ConnectError("oops"))
    respx.get("http://x/.well-known/agent.json").mock(side_effect=httpx.ConnectError("oops"))
    respx.get("http://x/.well-known/mcp.json").mock(
        return_value=httpx.Response(200, json={"mcp": "ok"})
    )
    async with httpx.AsyncClient() as http:
        result = await run_discovery_chain(http, "http://x")
    assert result.discovery_path == "mcp_well_known"
    # The failed probe's URL is recorded with status -1 (transport-error sentinel).
    assert result.raw_responses.get("http://x/.well-known/agent-card.json") == -1
