"""GET /runs + GET /runs/{run_id} — the audit-registry read API.

Artifact URLs are signed FRESH at read time from deterministic object paths
(reports/{run_id}/..., {recipe_id}.md) — stored v4 URLs would expire before
the judging window ends.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage.models import RunRecord, RunSource
from phoenix_audit_agent.storage.runs import get_run_store

_log = structlog.get_logger(__name__)

router = APIRouter()

_REPORT_ARTIFACTS = ("report.pdf", "report.json", "signature.json")


async def sign_blob_url(blob_name: str) -> str:
    """v4 signed GET URL for an existing blob (module attribute = test seam)."""
    from phoenix_audit_agent.patcher.markdown_emitter import _build_default_client

    settings = get_settings()

    def _sign() -> str:
        client = _build_default_client()
        blob = client.bucket(settings.GCS_RECIPES_BUCKET).blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS),
            method="GET",
        )

    return await asyncio.to_thread(_sign)


class RunListResponse(BaseModel):
    runs: list[RunRecord]


class RunDetailResponse(BaseModel):
    run: RunRecord
    artifact_urls: dict[str, str]


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    agent_id: str | None = None,
    source: RunSource | None = None,
    limit: int = 50,
) -> RunListResponse:
    rows = await get_run_store().list_runs(agent_id=agent_id, source=source, limit=min(limit, 200))
    return RunListResponse(runs=rows)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str) -> RunDetailResponse:
    record = await get_run_store().get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    blob_names: dict[str, str] = {}
    if record.report_available:
        for name in _REPORT_ARTIFACTS:
            blob_names[name] = f"reports/{record.run_id}/{name}"
    if record.recipe_id:
        blob_names["recipe.md"] = f"{record.recipe_id}.md"

    urls: dict[str, str] = {}
    if blob_names:
        signed: list[Any] = await asyncio.gather(
            *(sign_blob_url(b) for b in blob_names.values()), return_exceptions=True
        )
        for (name, blob), result in zip(blob_names.items(), signed, strict=True):
            if isinstance(result, BaseException):
                # A signing failure must not 500 the whole record view; the
                # absent key tells the UI exactly which artifact is unavailable.
                _log.error("artifact_url_sign_failed", run_id=run_id, blob=blob, error=str(result))
                continue
            urls[name] = result
    return RunDetailResponse(run=record, artifact_urls=urls)


__all__ = ["router", "sign_blob_url"]
