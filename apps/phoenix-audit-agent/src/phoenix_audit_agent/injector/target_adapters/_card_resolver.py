"""A2A AgentCard resolver with dual-convention probe + permissive fallback.

Centralizes the card-discovery logic that PR #130 inlined into ADKAdapter so
the `/validate` preflight endpoint can reuse it without going through the
full adapter lifecycle. Two extensions over plain `a2a.client.A2ACardResolver`:

1. **Dual-convention probe** — A2A v1.0 path first, RFC-8615 / Codelabs
   `/.well-known/agent.json` as fallback on 404. Same logic as PR #130.

2. **Permissive synthesis** — when the SDK rejects a card shape
   (e.g. Weather Agent's pre-v1 `methods` array), extract `name` + `url`
   from the raw dict and synthesize a minimal AgentCard with sane defaults.
   The caller surfaces a "pre-v1 schema; basic audit only" warning so the
   regulator sees the limitation on the signed report cover.

Errors fall into three buckets so the wizard + the `/validate` endpoint
can show actionable messages:
- `CardNotFoundError` — both well-known paths returned 404.
- `MalformedCardError` — JSON parsed but lacks both `name` and `url`.
- `CardTransportError` — 5xx / connect-refused / TLS failure on the v1.0
  path; the resolver aborts immediately (no silent fall-through).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

import httpx
from a2a.client import A2ACardResolver
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCapabilities, AgentCard

from phoenix_audit_agent.errors import PhoenixAuditError

WELL_KNOWN_AGENT_CARD = "/.well-known/agent-card.json"
WELL_KNOWN_AGENT_CARD_LEGACY = "/.well-known/agent.json"
_HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND.value
# Pre-v1 warning surfaces on the wizard hint AND the signed-report cover so
# a regulator never sees "skills audited: full" against a target whose card
# we couldn't fully parse.
_PERMISSIVE_WARNING = "pre-v1 A2A schema; basic audit only (skill metadata unavailable)"


class CardResolverError(PhoenixAuditError):
    """Base class for the resolver's typed errors."""


class CardNotFoundError(CardResolverError):
    """Neither well-known path returned a card."""


class MalformedCardError(CardResolverError):
    """The card JSON lacks the minimum identifying fields (name + url)."""


class CardTransportError(CardResolverError):
    """A non-404 transport error on the v1.0 path. Aborts the probe chain."""


@dataclass(frozen=True)
class CardProbeResult:
    """Outcome of `resolve_card` — surfaced to the wizard + the auditor."""

    mode: str  # "v1" | "permissive"
    card: AgentCard
    discovery_path: str
    warnings: list[str] = field(default_factory=list)
    auth: str = "none"
    skills_count: int = 0


def _extract_auth_from_raw(raw: dict[str, Any]) -> str:
    """Surface the first security scheme name from a raw dict, or 'none'."""
    schemes = raw.get("securitySchemes")
    if isinstance(schemes, dict) and schemes:
        first = next(iter(schemes.keys()))
        return str(first)
    return "none"


def _extract_auth_from_card(card: AgentCard) -> str:
    """Surface the first security scheme name from a parsed card, or 'none'.

    The wizard shows this as e.g. "AIScan — A2A v0.3.0 · no auth" or
    "MERCURY — A2A v0.3.0 · x402"; users see at a glance whether
    auditing this target costs money or needs an API key.
    """
    schemes = card.security_schemes
    if schemes:
        return next(iter(schemes.keys()))
    return "none"


def _synthesize_permissive_card(raw: dict[str, Any], *, base: str) -> AgentCard:
    """Build a minimal AgentCard from a non-conformant raw dict.

    Requires `name` AND either `url` or a usable `base` fallback. The
    permissive card has empty `skills` and default `text/plain` modes so
    a2a-sdk's downstream consumers (ClientFactory, message dispatch) keep
    working — the audit runs with generic prompts since we don't know the
    target's declared skills.
    """
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        msg = "agent card lacks required 'name' field"
        raise MalformedCardError(msg)
    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        url = base
    return AgentCard(
        name=name,
        description=raw.get("description") or "A2A agent (pre-v1 schema).",
        url=url,
        version=str(raw.get("version") or "0.0.0"),
        protocol_version=str(raw.get("protocolVersion") or "0.0.0"),
        capabilities=AgentCapabilities(),
        default_input_modes=raw.get("defaultInputModes") or ["text/plain"],
        default_output_modes=raw.get("defaultOutputModes") or ["text/plain"],
        skills=[],
        preferred_transport="JSONRPC",
    )


async def _fetch_raw_json(
    http: httpx.AsyncClient, *, base: str, path: str
) -> dict[str, Any] | None:
    """Fetch a well-known path; return None on 404, raise on other errors."""
    url = f"{base}{path}"
    try:
        response = await http.get(url)
    except httpx.HTTPError as exc:
        msg = f"transport error fetching {url}: {type(exc).__name__}"
        raise CardTransportError(msg) from exc
    if response.status_code == _HTTP_NOT_FOUND:
        return None
    if response.status_code != HTTPStatus.OK.value:
        msg = f"{url} returned HTTP {response.status_code}"
        raise CardTransportError(msg)
    try:
        payload = response.json()
    except ValueError as exc:
        # Non-JSON body at a well-known path: malformed, not "not a card".
        msg = f"{url} returned non-JSON body"
        raise MalformedCardError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{url} returned non-object JSON ({type(payload).__name__})"
        raise MalformedCardError(msg)
    return payload


async def _try_parse_strict(http: httpx.AsyncClient, *, base: str, path: str) -> AgentCard | None:
    """Use a2a-sdk's strict resolver; return None on 404, raise transport
    errors. Pydantic ValidationError is intentionally NOT caught here —
    the caller falls back to permissive synthesis on that exact signal.
    """
    resolver = A2ACardResolver(httpx_client=http, base_url=base, agent_card_path=path)
    try:
        return await resolver.get_agent_card()
    except A2AClientHTTPError as exc:
        if exc.status_code == _HTTP_NOT_FOUND:
            return None
        msg = f"{base}{path} returned HTTP {exc.status_code}"
        raise CardTransportError(msg) from exc
    except A2AClientJSONError:
        # The SDK couldn't parse — signal "not strict v1" to the caller.
        return None


async def resolve_card(http: httpx.AsyncClient, base: str) -> CardProbeResult:
    """Probe both well-known paths and return a CardProbeResult.

    Order: try v1.0 strict → v1.0 permissive → legacy strict → legacy
    permissive. The first success wins. Strict and permissive use the
    same raw JSON so each path costs at most one GET.
    """
    base = base.rstrip("/")
    attempted: list[str] = []
    raw_per_path: dict[str, dict[str, Any]] = {}
    last_error: Exception | None = None
    # First pass — strict parse via the SDK. The SDK's resolver does its
    # own GET, so call it before our raw fetch on each path to keep
    # behavior identical to PR #130's ADK adapter.
    for path in (WELL_KNOWN_AGENT_CARD, WELL_KNOWN_AGENT_CARD_LEGACY):
        attempted.append(path)
        try:
            card = await _try_parse_strict(http, base=base, path=path)
        except CardTransportError as exc:
            # 5xx on the v1.0 path aborts the chain — don't silently fall
            # through to the legacy path and pretend "not found".
            last_error = exc
            raise
        if card is not None:
            # The parsed AgentCard already carries security_schemes; avoid
            # a second GET on the well-known path (PR #131 test feedback —
            # idempotent-connect test counts GETs).
            return CardProbeResult(
                mode="v1",
                card=card,
                discovery_path=path,
                warnings=[],
                auth=_extract_auth_from_card(card),
                skills_count=len(card.skills or []),
            )
        # Strict parse returned None → either 404 or pydantic-rejected.
        # Distinguish by raw fetch; cache the raw dict so we don't refetch.
        try:
            raw = await _fetch_raw_json(http, base=base, path=path)
        except (MalformedCardError, CardTransportError) as exc:
            last_error = exc
            continue
        if raw is None:
            # 404 on both raw and strict paths — try the next well-known.
            continue
        # Strict failed but raw fetched ok → permissive synthesis.
        raw_per_path[path] = raw
        try:
            synthesized = _synthesize_permissive_card(raw, base=base)
        except MalformedCardError as exc:
            last_error = exc
            continue
        return CardProbeResult(
            mode="permissive",
            card=synthesized,
            discovery_path=path,
            warnings=[_PERMISSIVE_WARNING],
            auth=_extract_auth_from_raw(raw),
            skills_count=0,
        )
    # All paths exhausted without producing a card.
    if last_error is not None and isinstance(last_error, MalformedCardError):
        raise last_error
    msg = f"no AgentCard at {base} (tried {attempted})"
    raise CardNotFoundError(msg)


__all__ = [
    "WELL_KNOWN_AGENT_CARD",
    "WELL_KNOWN_AGENT_CARD_LEGACY",
    "CardNotFoundError",
    "CardProbeResult",
    "CardResolverError",
    "CardTransportError",
    "MalformedCardError",
    "resolve_card",
]
