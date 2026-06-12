"""POST /validate — preflight A2A AgentCard probe for the wizard.

Called by the web wizard on URL paste: dual-convention probe + permissive
parse via `target_adapters._card_resolver`, returns a tiny JSON the wizard
renders inline ("✓ AIScan — A2A v0.3.0 · 6 skills · no auth").

Auth: `require_user` per every other /api/agent/* route.
SSRF: reuses `_url_guard.validate_target_url` so this endpoint can't be
turned into a metadata-server exfiltration vector.

The actual card-discovery + permissive synthesis lives in
`injector/target_adapters/_card_resolver.py` so the auditor's
`ADKAdapter.connect()` and this endpoint share one source of truth.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from phoenix_audit_agent.api._url_guard import validate_target_url
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.injector.target_adapters._card_resolver import (
    CardNotFoundError,
    CardTransportError,
    MalformedCardError,
    resolve_card,
)

_log = structlog.get_logger(__name__)

router = APIRouter()

# Generous enough for slow agents but bounded so a misbehaving target can't
# stall the wizard. Cloud Run-shaped agents typically respond in <1s.
_VALIDATE_TIMEOUT_S = 8.0


class ValidateRequest(BaseModel):
    """Wizard payload — just the URL the user pasted."""

    target_url: str = Field(min_length=1)

    @field_validator("target_url")
    @classmethod
    def _guard_url(cls, v: str) -> str:
        # Same SSRF guard the /run endpoint uses. Rejects loopback,
        # link-local, and the GCP metadata server; raises ValueError on
        # invalid → FastAPI maps to 422.
        return validate_target_url(v)


class ValidateResponse(BaseModel):
    """Wizard response — tiny + flat so the React component renders without
    branching on nested shapes. `valid` is the only field clients must read;
    everything else is optional metadata for the inline-success state."""

    valid: bool
    mode: str | None = None  # "v1" | "permissive" when valid=True
    name: str | None = None
    protocol_version: str | None = None
    version: str | None = None
    skills_count: int | None = None
    auth: str | None = None
    transport: str | None = None
    card_url: str | None = None
    discovery_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    reason: str | None = None  # populated only when valid=False


def _success_response(probe: Any) -> ValidateResponse:
    """Map a CardProbeResult to the wire-shaped ValidateResponse."""
    card = probe.card
    return ValidateResponse(
        valid=True,
        mode=probe.mode,
        name=card.name,
        protocol_version=card.protocol_version,
        version=card.version,
        skills_count=probe.skills_count,
        auth=probe.auth,
        transport=card.preferred_transport,
        card_url=card.url,
        discovery_path=probe.discovery_path,
        warnings=probe.warnings,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_target(
    payload: ValidateRequest,
    user: Annotated[AuthedUser, Depends(require_user)],
) -> ValidateResponse:
    """Probe the target's well-known agent card and report the verdict.

    Never raises on a network-level failure — the wizard wants a
    structured "valid=false, reason=..." instead of a 500. Only SSRF
    (validation-time) returns a 422 because that's a programmer/UX bug,
    not a discoverable target.
    """
    _log.info("validate_endpoint_invoked", uid=user.uid, target_url=payload.target_url)
    async with httpx.AsyncClient(timeout=_VALIDATE_TIMEOUT_S) as http:
        try:
            probe = await resolve_card(http, payload.target_url)
        except CardNotFoundError as exc:
            return ValidateResponse(valid=False, reason=str(exc))
        except MalformedCardError as exc:
            return ValidateResponse(valid=False, reason=f"malformed card: {exc}")
        except CardTransportError as exc:
            return ValidateResponse(valid=False, reason=f"transport error: {exc}")
    return _success_response(probe)


__all__ = ["router"]
