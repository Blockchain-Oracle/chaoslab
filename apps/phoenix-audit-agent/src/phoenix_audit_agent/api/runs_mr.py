"""POST /runs/{run_id}/gitlab-mr — review-first MR filing (story-9.17).

The MR is filed ONLY on an explicit human click, with the USER's OAuth
identity, into the USER's chosen project. There is no fallback to the
service token — filing as the wrong identity is worse than failing.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.integrations import gitlab_oauth
from phoenix_audit_agent.patcher import HardeningRecipe
from phoenix_audit_agent.patcher.gitlab_emitter import GitLabEmitterError, GitLabMREmitter
from phoenix_audit_agent.storage.models import RunCompletion
from phoenix_audit_agent.storage.runs import get_run_store, persist_run_completion

_log = structlog.get_logger(__name__)

router = APIRouter()


async def download_recipe(recipe_id: str) -> HardeningRecipe | None:
    """Rehydrate the structured recipe from its `{recipe_id}.json` sidecar
    (module attribute = test seam). None ⇒ artifact absent (pre-9.17 run)."""
    from google.cloud.exceptions import NotFound

    from phoenix_audit_agent.storage.gcs import get_storage_client

    settings = get_settings()

    def _download() -> bytes | None:
        client = get_storage_client()
        blob = client.bucket(settings.GCS_RECIPES_BUCKET).blob(f"{recipe_id}.json")
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    raw = await asyncio.to_thread(_download)
    if raw is None:
        return None
    return HardeningRecipe.model_validate_json(raw)


async def emit_recipe_mr(recipe: HardeningRecipe, *, project_id: str, oauth_token: str) -> str:
    """File branch+files+MR with the user's token (module attribute = seam)."""
    result = await GitLabMREmitter(oauth_token=oauth_token).emit(recipe, project_id=project_id)
    return result.mr_url


class GitLabMRRequest(BaseModel):
    project_id: int


class GitLabMRResponse(BaseModel):
    mr_url: str
    # False ⇒ the MR EXISTS on GitLab but the registry write-through failed —
    # disclosed so the UI can tell "filed" from "filed and recorded".
    persisted: bool


@router.post("/runs/{run_id}/gitlab-mr", response_model=GitLabMRResponse)
async def file_gitlab_mr(
    run_id: str,
    payload: GitLabMRRequest,
    user: Annotated[AuthedUser, Depends(require_user)],
) -> GitLabMRResponse:
    record = await get_run_store().get(run_id)
    # Foreign-owned reads as not-found — a 403 would CONFIRM the id exists.
    if record is None or record.owner_uid not in (None, user.uid):
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")
    if record.owner_uid is None:
        # Shared specimens are viewable by everyone — filable by no one.
        raise HTTPException(status_code=422, detail="sample runs cannot be filed as MRs")
    if record.recipe_id is None:
        raise HTTPException(status_code=409, detail="this run produced no hardening recipe")
    if record.mr_url:
        raise HTTPException(
            status_code=409, detail=f"an MR was already filed for this run: {record.mr_url}"
        )
    try:
        token = await gitlab_oauth.get_valid_access_token(user.uid)
    except (gitlab_oauth.NotConnectedError, gitlab_oauth.ConnectionExpiredError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except gitlab_oauth.GitLabUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    recipe = await download_recipe(record.recipe_id)
    if recipe is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "recipe artifact unavailable for this run — re-run the audit "
                "to produce a filable recipe"
            ),
        )
    try:
        mr_url = await emit_recipe_mr(recipe, project_id=str(payload.project_id), oauth_token=token)
    except GitLabEmitterError as exc:
        _log.error("gitlab_mr_filing_failed", run_id=run_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"MR filing failed: {exc}") from exc

    persisted = await persist_run_completion(
        run_id,
        RunCompletion(
            run_id=record.run_id,
            target_url=record.target_url,
            created_at=record.created_at,
            phase=record.phase,
            mr_url=mr_url,
        ),
    )
    if not persisted:
        _log.error("gitlab_mr_url_persist_failed", run_id=run_id, mr_url=mr_url)
    return GitLabMRResponse(mr_url=mr_url, persisted=persisted)


__all__ = ["router"]
