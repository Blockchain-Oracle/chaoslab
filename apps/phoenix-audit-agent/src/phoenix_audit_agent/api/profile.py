"""GET/PATCH /profile — the users/{uid} settings spine (story-9.12).

The uid always comes from the verified token: there is no profile-id
parameter, so cross-user reads/writes are impossible by construction.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.storage.models import HostingPref, UserProfile
from phoenix_audit_agent.storage.profiles import get_profile_store

router = APIRouter()


class ProfileUpdate(BaseModel):
    """extra='forbid' makes an unknown field a 422 instead of a
    silently-dropped write; exclude_unset keeps PATCH a true partial."""

    model_config = ConfigDict(extra="forbid")

    org_name: str | None = None
    framework_default: str | None = Field(default=None, min_length=1)
    hosting_pref: HostingPref | None = None
    onboarded: bool | None = None


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
    updates = payload.model_dump(exclude_unset=True)
    now = utc_now_iso()
    existing = await get_profile_store().get(user.uid) or _defaults(user)
    merged = existing.model_copy(
        update={
            **updates,
            "email": user.email,
            "created_at": existing.created_at or now,
            "updated_at": now,
        }
    )
    await get_profile_store().set(merged)
    return merged


__all__ = ["router"]
