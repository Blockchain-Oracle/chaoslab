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
from a2a.types import AgentCapabilities, AgentCard

from phoenix_audit_agent.errors import PhoenixAuditError

WELL_KNOWN_AGENT_CARD = "/.well-known/agent-card.json"
WELL_KNOWN_AGENT_CARD_LEGACY = "/.well-known/agent.json"
_HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND.value
# Pre-v1 warning surfaces on the wizard hint AND the signed-report cover so
# a regulator never sees "skills audited: full" against a target whose card
# we couldn't fully parse.
_PERMISSIVE_WARNING = "pre-v1 A2A schema; basic audit only (skill metadata unavailable)"
# Cap the well-known body — attacker-hosted /.well-known/agent-card.json
# returning a multi-GB stream would OOM the worker (security-review HIGH).
# Real agent cards are <10 KiB; 1 MiB is a generous ceiling.
_MAX_CARD_BYTES = 1 * 1024 * 1024


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


# x402 is declared in the AgentCard `extensions` array (NOT securitySchemes)
# per github.com/google-agentic-commerce/a2a-x402 — surfacing it here so the
# wizard can warn "audit requires a funded wallet" instead of falsely showing
# the target as unauthenticated.
_X402_EXTENSION_URI_PREFIX = "https://github.com/google-a2a/a2a-x402"


def _has_x402_extension(extensions: Any) -> bool:
    if not isinstance(extensions, list):
        return False
    for ext in extensions:
        uri = ext.get("uri") if isinstance(ext, dict) else getattr(ext, "uri", None)
        if isinstance(uri, str) and uri.startswith(_X402_EXTENSION_URI_PREFIX):
            return True
    return False


def _extract_auth_from_raw(raw: dict[str, Any]) -> str:
    """Surface the auth scheme from a raw dict, or 'none'.

    Checks `extensions` for x402 first (per-call stablecoin paywall) then
    falls back to `securitySchemes` (OpenAPI-style apiKey / bearer / oauth2
    / mtls). Either way the auditor can't drive the target without creds.
    """
    if _has_x402_extension(raw.get("extensions")):
        return "x402"
    schemes = raw.get("securitySchemes")
    if isinstance(schemes, dict) and schemes:
        first = next(iter(schemes.keys()))
        return str(first)
    return "none"


def _extract_auth_from_card(card: AgentCard) -> str:
    """Surface the auth scheme from a parsed card, or 'none'.

    Same precedence as the raw extractor: x402 extension first, then
    `security_schemes`. Wizard renders this as a ⚠ amber hint so the user
    knows auditing this target needs credentials (audit will 401 / 402
    without them); BYO-token flow is a future PR.
    """
    if _has_x402_extension(getattr(card, "extensions", None)):
        return "x402"
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
    # Body-size cap (security-review HIGH). Reject Content-Length over the
    # cap upfront; the read itself is bounded by httpx's response.content
    # buffer (capped by the timeout + transport limits).
    declared_len = response.headers.get("content-length")
    if declared_len and declared_len.isdigit() and int(declared_len) > _MAX_CARD_BYTES:
        msg = f"{url} response too large ({declared_len} bytes)"
        raise MalformedCardError(msg)
    if len(response.content) > _MAX_CARD_BYTES:
        msg = f"{url} response too large ({len(response.content)} bytes)"
        raise MalformedCardError(msg)
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


async def resolve_card(http: httpx.AsyncClient, base: str) -> CardProbeResult:
    """Probe both well-known paths and return a CardProbeResult.

    Order: v1.0 path strict → v1.0 permissive → legacy path strict →
    legacy permissive. The first success wins. We always fetch the raw
    dict first then validate in-process — one GET per path, and the raw
    dict stays available for x402-extension / securitySchemes inspection
    even when pydantic drops fields the parsed AgentCard model doesn't
    declare (e.g. `extensions`).
    """
    from pydantic import ValidationError  # local import — pydantic re-export indirection

    base = base.rstrip("/")
    attempted: list[str] = []
    last_error: Exception | None = None
    for path in (WELL_KNOWN_AGENT_CARD, WELL_KNOWN_AGENT_CARD_LEGACY):
        attempted.append(path)
        try:
            raw = await _fetch_raw_json(http, base=base, path=path)
        except CardTransportError:
            # 5xx aborts the chain — don't silently fall through to the
            # legacy path and pretend "not found".
            raise
        except MalformedCardError as exc:
            last_error = exc
            continue
        if raw is None:
            continue  # 404 — try the next well-known path
        # Strict validate in-process so we know whether to surface mode=v1
        # or mode=permissive without paying for a second GET.
        try:
            card = AgentCard.model_validate(raw)
        except ValidationError:
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
        return CardProbeResult(
            mode="v1",
            card=card,
            discovery_path=path,
            warnings=[],
            # Extract from raw, not the parsed card: pydantic drops
            # `extensions` (where x402 lives), so the parsed AgentCard
            # can't tell us about stablecoin paywalls.
            auth=_extract_auth_from_raw(raw),
            skills_count=len(card.skills or []),
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
