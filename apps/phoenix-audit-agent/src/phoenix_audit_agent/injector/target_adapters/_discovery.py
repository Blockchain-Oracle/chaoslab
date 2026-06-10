"""Tier-3 HTTP black-box discovery chain.

Per S3.6 + `context/05 §13.1`: walk through a fallback sequence of probes
to figure out what KIND of agent we're attacking when we have no a-priori
framework knowledge. The first probe that returns 200 wins; if all fail
we raise `AdapterDiscoveryError` at the adapter level.

Probes (in order):
  1. `agent_card`       — GET `/.well-known/agent-card.json` (A2A)
  2. `mcp_well_known`   — GET `/.well-known/mcp.json`
  3. `mcp_initialize`   — POST `/mcp` JSON-RPC initialize
  4. `openapi`          — GET `/openapi.json` (+ .yaml, swagger.json, v3/api-docs)
  5. `input_schema`     — GET `/input_schema` (+ /agent/…, /chain/…, /runnable/…) — LangServe
  6. `swagger_ui`       — GET `/swagger-ui`, `/docs`, `/redoc`, `/api/agents` — HTML signature only

The whole sequence is short-circuit + log-only — transport errors mark the
probe as `-1` in raw_responses but never abort the chain. The orchestrator
then sees the full `probes_attempted` list in the error message and can
suggest remediation to the operator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Probe path constants — module-level so a future story-3.6b can extend
# the chain by appending without breaking the order contract.
_AGENT_CARD_PATH: str = "/.well-known/agent-card.json"
_MCP_WELL_KNOWN_PATH: str = "/.well-known/mcp.json"
_MCP_INIT_PATH: str = "/mcp"
_OPENAPI_PATHS: tuple[str, ...] = (
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/v3/api-docs",
    "/api-docs",
)
_INPUT_SCHEMA_PATHS: tuple[str, ...] = (
    "/input_schema",
    "/agent/input_schema",
    "/chain/input_schema",
    "/runnable/input_schema",
)
_UI_PATHS: tuple[str, ...] = ("/swagger-ui", "/docs", "/redoc", "/api/agents")

_MCP_INIT_BODY: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "phoenix-audit-blackbox-probe", "version": "0.0.0"},
    },
}


@dataclass
class DiscoveryResult:
    """Outcome of `run_discovery_chain` — surfaced in fingerprint + errors."""

    discovery_path: str | None
    payload: dict[str, Any] | None
    probes_attempted: list[str] = field(default_factory=list)
    raw_responses: dict[str, int] = field(default_factory=dict)


async def run_discovery_chain(  # noqa: PLR0911 — 6 probe paths + 1 fall-through return; flattening would obscure the short-circuit chain
    http: httpx.AsyncClient, base: str
) -> DiscoveryResult:
    """Probe `base` for agent-discovery surfaces; return first hit or None."""
    attempted: list[str] = []
    raw: dict[str, int] = {}

    # Probe 1: agent_card
    attempted.append("agent_card")
    r = await _safe_get(http, f"{base}{_AGENT_CARD_PATH}", raw)
    payload = _try_json(r)
    if payload is not None:
        return DiscoveryResult("agent_card", payload, attempted, raw)

    # Probe 2: mcp_well_known
    attempted.append("mcp_well_known")
    r = await _safe_get(http, f"{base}{_MCP_WELL_KNOWN_PATH}", raw)
    payload = _try_json(r)
    if payload is not None:
        return DiscoveryResult("mcp_well_known", payload, attempted, raw)

    # Probe 3: mcp_initialize (POST JSON-RPC)
    attempted.append("mcp_initialize")
    r = await _safe_post(http, f"{base}{_MCP_INIT_PATH}", json=_MCP_INIT_BODY, raw=raw)
    payload = _try_json(r)
    if r is not None and r.status_code == HTTPStatus.OK.value and payload is not None:
        result = payload.get("result") if isinstance(payload, dict) else None
        if isinstance(result, dict) and "serverInfo" in result:
            return DiscoveryResult("mcp_initialize", result, attempted, raw)

    # Probe 4: openapi
    for openapi_path in _OPENAPI_PATHS:
        attempted.append(f"openapi:{openapi_path}")
        r = await _safe_get(http, f"{base}{openapi_path}", raw)
        payload = _try_json(r)
        if payload is not None:
            return DiscoveryResult("openapi", payload, attempted, raw)

    # Probe 5: input_schema (LangServe)
    for is_path in _INPUT_SCHEMA_PATHS:
        attempted.append(f"input_schema:{is_path}")
        r = await _safe_get(http, f"{base}{is_path}", raw)
        payload = _try_json(r)
        if payload is not None:
            return DiscoveryResult("input_schema", payload, attempted, raw)

    # Probe 6: swagger_ui — HTML signature only (no JSON payload).
    for ui_path in _UI_PATHS:
        attempted.append(f"ui:{ui_path}")
        r = await _safe_get(http, f"{base}{ui_path}", raw)
        if r is not None and r.status_code == HTTPStatus.OK.value:
            return DiscoveryResult("swagger_ui", {"path": ui_path}, attempted, raw)

    return DiscoveryResult(None, None, attempted, raw)


async def _safe_get(
    http: httpx.AsyncClient, url: str, raw: dict[str, int]
) -> httpx.Response | None:
    """GET that swallows httpx errors and records the status (or -1) in `raw`."""
    try:
        r = await http.get(url)
    except httpx.HTTPError as exc:
        logger.debug("blackbox_probe_failed url=%s err=%s", url, exc)
        raw[url] = -1
        return None
    raw[url] = r.status_code
    return r


async def _safe_post(
    http: httpx.AsyncClient,
    url: str,
    *,
    json: dict[str, Any],
    raw: dict[str, int],
) -> httpx.Response | None:
    try:
        r = await http.post(url, json=json)
    except httpx.HTTPError as exc:
        logger.debug("blackbox_probe_post_failed url=%s err=%s", url, exc)
        raw[url] = -1
        return None
    raw[url] = r.status_code
    return r


def _try_json(r: httpx.Response | None) -> dict[str, Any] | None:
    """Return parsed JSON dict iff status==200 AND body parses. Else None."""
    if r is None or r.status_code != HTTPStatus.OK.value:
        return None
    try:
        payload = r.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


__all__ = ["DiscoveryResult", "run_discovery_chain"]
