"""Unit tests for the permissive A2A card resolver.

The card resolver wraps `a2a.client.A2ACardResolver` with two extensions
required by Phoenix Audit's "audit any A2A v1.0 agent" promise:

1. **Dual-convention probe**: try `/.well-known/agent-card.json` (A2A v1.0)
   first, fall back to `/.well-known/agent.json` (RFC-8615 / Codelabs) on 404.
   Same logic as PR #130's ADK adapter hotfix, now centralized so the
   `/validate` preflight endpoint can reuse it without going through the
   full ADK adapter lifecycle.

2. **Permissive synthesis**: when the SDK's Pydantic validation rejects a
   card shape (e.g. Weather Agent's pre-v1 `methods` array instead of
   `skills` + `defaultInputModes`), extract the minimum identifying fields
   — `name` and `url` — and synthesize a minimal AgentCard with sane
   defaults. The signed audit cover surfaces a "pre-v1 schema; basic audit
   only" warning so the regulator sees we couldn't read the full skills
   manifest.
"""

from __future__ import annotations

import httpx
import pytest
import respx


@pytest.fixture(autouse=True)
def _isolate_httpx() -> None:
    """respx auto-installs on each test; this fixture is structural only."""
    return


def _v1_card_payload(name: str = "test-agent", url: str = "http://x") -> dict:
    """Minimal A2A v1.0-conformant card (matches AIScan, PostalForm, et al.)."""
    return {
        "name": name,
        "description": "A test agent.",
        "url": url,
        "version": "1.0.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "echo",
                "name": "echo",
                "description": "Echo the input back.",
                "tags": ["test"],
            }
        ],
    }


def _pre_v1_card_payload() -> dict:
    """Pre-v1 / Codelabs Weather Agent shape — uses `methods` instead of
    `skills` + `defaultInputModes`. SDK rejects this; permissive parser
    must synthesize a minimal card from `name` + `url`."""
    return {
        "name": "Global Weather Agent",
        "description": "Real-time weather information.",
        "url": "http://x",
        "version": "1.0.0",
        "capabilities": {"streaming": True},
        "securitySchemes": {"unauthenticated": {"type": "none"}},
        "methods": [
            {"name": "message/send", "description": "Handles weather queries."},
            {"name": "message/stream", "description": "Streams forecast as SSE."},
        ],
    }


@respx.mock
async def test_v1_card_returns_mode_v1() -> None:
    """Happy path — AIScan-shape card at the v1.0 path → mode=v1."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_v1_card_payload(name="AIScan"))
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "v1"
    assert result.card.name == "AIScan"
    assert result.discovery_path == "/.well-known/agent-card.json"
    assert result.warnings == []
    assert result.auth == "none"
    assert result.skills_count == 1


@respx.mock
async def test_legacy_path_card_returns_mode_v1() -> None:
    """v1.0 path 404 → legacy path 200 with v1-shape → still mode=v1.

    The dual-convention probe order is fixed (v1.0 → legacy) so an agent
    serving on the older RFC-8615 convention but with the modern shape is
    handled as first-class — not "permissive".
    """
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(
        return_value=httpx.Response(200, json=_v1_card_payload(name="weather-modern"))
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "v1"
    assert result.card.name == "weather-modern"
    assert result.discovery_path == "/.well-known/agent.json"


@respx.mock
async def test_pre_v1_card_falls_back_to_permissive() -> None:
    """Weather-Agent-shape (`methods` array, no `skills` / `defaultInputModes`)
    → mode=permissive with synthesized AgentCard + warning.

    This is the load-bearing test for the user's "any production agent"
    promise. Without this, pre-v1 cards (Codelabs samples, older A2A
    examples) crash the wizard and the demo lies.
    """
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=_pre_v1_card_payload())
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "permissive"
    assert result.card.name == "Global Weather Agent"
    assert result.card.url == "http://x"
    # The synthesized card MUST satisfy a2a-sdk's downstream consumers
    # (ClientFactory etc.) — that's the point of synthesizing instead of
    # leaving the raw dict for the SDK to reject again.
    assert result.card.default_input_modes == ["text/plain"]
    assert result.card.default_output_modes == ["text/plain"]
    assert result.card.skills == []
    assert result.warnings
    assert any("pre-v1" in w.lower() or "basic audit" in w.lower() for w in result.warnings)


@respx.mock
async def test_permissive_falls_back_when_url_missing() -> None:
    """A card with `name` but no `url` field — synthesize using the base URL
    the user pasted. Common for ADK-style agents that omit `url` and assume
    the host root is the dispatch endpoint."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    payload = {
        "name": "partial-card-agent",
        "description": "no url field",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "methods": [{"name": "message/send"}],
    }
    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "permissive"
    assert result.card.name == "partial-card-agent"
    assert result.card.url == "http://x"


@respx.mock
async def test_missing_name_and_url_raises_malformed() -> None:
    """JSON with NEITHER `name` NOR `url` — not a card at all; surface as
    MalformedCardError instead of silently synthesizing a meaningless one."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import (
        MalformedCardError,
        resolve_card,
    )

    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json={"random": "junk"})
    )
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        with pytest.raises(MalformedCardError):
            await resolve_card(http, "http://x")


@respx.mock
async def test_5xx_aborts_no_silent_retry() -> None:
    """A 5xx on the v1.0 path is a server error — abort, don't fall through
    to the legacy path. Otherwise an outage on the modern path silently
    masquerades as an "agent uses legacy convention" 404.
    """
    from phoenix_audit_agent.injector.target_adapters._card_resolver import (
        CardTransportError,
        resolve_card,
    )

    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(500))
    legacy_route = respx.get("http://x/.well-known/agent.json")
    async with httpx.AsyncClient() as http:
        with pytest.raises(CardTransportError):
            await resolve_card(http, "http://x")
    # Legacy path must NOT be probed on 5xx.
    assert legacy_route.call_count == 0


@respx.mock
async def test_both_paths_404_raises_not_found() -> None:
    """When neither path returns a card, the error message names BOTH
    paths so the operator/user can see what was tried."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import (
        CardNotFoundError,
        resolve_card,
    )

    respx.get("http://x/.well-known/agent-card.json").mock(return_value=httpx.Response(404))
    respx.get("http://x/.well-known/agent.json").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        with pytest.raises(CardNotFoundError) as exc_info:
            await resolve_card(http, "http://x")
    msg = str(exc_info.value)
    assert "/.well-known/agent-card.json" in msg
    assert "/.well-known/agent.json" in msg


@respx.mock
async def test_auth_scheme_extracted_for_v1_card() -> None:
    """If the v1 card declares securitySchemes, the resolver surfaces the
    first scheme name as `result.auth` for the wizard to display."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    payload = _v1_card_payload()
    payload["securitySchemes"] = {
        "bearer-token": {"type": "http", "scheme": "bearer"},
    }
    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "v1"
    assert result.auth == "bearer-token"


@respx.mock
async def test_x402_extension_surfaces_as_auth_x402() -> None:
    """x402 stablecoin paywalls are declared in the AgentCard `extensions`
    array (NOT securitySchemes) per github.com/google-agentic-commerce/a2a-x402.
    The wizard's amber-hint depends on us reporting it as auth='x402' so a
    paywalled target shows ⚠ instead of a misleading green ✓."""
    from phoenix_audit_agent.injector.target_adapters._card_resolver import resolve_card

    payload = _v1_card_payload(name="paywalled-agent")
    payload["extensions"] = [
        {
            "uri": "https://github.com/google-a2a/a2a-x402/v0.1",
            "description": "stablecoin paywall",
            "required": True,
        }
    ]
    respx.get("http://x/.well-known/agent-card.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with httpx.AsyncClient() as http:
        result = await resolve_card(http, "http://x")
    assert result.mode == "v1"
    assert result.auth == "x402"
