"""GET/PATCH /profile — the users/{uid} settings spine (story-9.12).

The uid always comes from the verified token: there is no profile-id
parameter, so cross-user reads/writes are impossible by construction.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.storage.models import HostingPref, UserProfile
from phoenix_audit_agent.storage.profiles import get_profile_store

router = APIRouter()

# Firestore's default retry deadline is ~60s; a settings save must fail loudly
# long before that (mirrors the runs.py write-timeout rationale).
_WRITE_TIMEOUT_SEC = 5.0


class ProfileUpdate(BaseModel):
    """extra='forbid' makes an unknown field a 422 instead of a
    silently-dropped write; exclude_unset keeps PATCH a true partial."""

    model_config = ConfigDict(extra="forbid")

    org_name: str | None = None
    framework_default: str | None = Field(default=None, min_length=1)
    hosting_pref: HostingPref | None = None
    onboarded: bool | None = None

    @field_validator("framework_default", "hosting_pref", "onboarded")
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        # An explicit null would survive exclude_unset and persist None into a
        # field the read model requires — bricking every later GET with a 500.
        if v is None:
            msg = "field cannot be null — omit it to leave it unchanged"
            raise ValueError(msg)
        return v

    @field_validator("org_name")
    @classmethod
    def _empty_clears(cls, v: str | None) -> str | None:
        # org_name is the one clearable field: "" means "remove my org name".
        return v or None


def _defaults(user: AuthedUser) -> UserProfile:
    return UserProfile(uid=user.uid, email=user.email)


@router.get("/profile", response_model=UserProfile)
async def get_profile(user: Annotated[AuthedUser, Depends(require_user)]) -> UserProfile:
    stored = await get_profile_store().get(user.uid)
    if stored is None:
        # Defaults are computed, never written — a GET must not create docs.
        return _defaults(user)
    # Email mirrors the verified token, not the stored copy.
    return stored.model_copy(update={"email": user.email})


@router.patch("/profile", response_model=UserProfile)
async def patch_profile(
    payload: ProfileUpdate, user: Annotated[AuthedUser, Depends(require_user)]
) -> UserProfile:
    store = get_profile_store()
    existing = await store.get(user.uid) or _defaults(user)
    fields: dict[str, Any] = {
        **payload.model_dump(exclude_unset=True),
        "uid": user.uid,
        "email": user.email,
        "created_at": existing.created_at or utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    # Validate the merged shape BEFORE writing (model_copy would bypass
    # validation); a field-level merge keeps unknown stored fields intact.
    merged = UserProfile.model_validate({**existing.model_dump(), **fields})
    try:
        await asyncio.wait_for(store.merge(user.uid, fields), timeout=_WRITE_TIMEOUT_SEC)
    except TimeoutError as err:
        raise HTTPException(
            status_code=503, detail="profile save timed out — settings storage unavailable"
        ) from err
    return merged


__all__ = ["router"]
