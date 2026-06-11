"""GET /runs + GET /runs/{run_id} — the audit-registry read API.

Artifact URLs are signed FRESH at read time from deterministic object paths
(reports/{run_id}/..., {recipe_id}.md) — stored v4 URLs would expire before
the judging window ends.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.reporter import REPORT_ARTIFACT_NAMES
from phoenix_audit_agent.storage.models import RunRecord, RunSource
from phoenix_audit_agent.storage.runs import get_run_store

_log = structlog.get_logger(__name__)

router = APIRouter()


async def sign_blob_url(blob_name: str) -> str:
    """v4 signed GET URL for an existing blob (module attribute = test seam)."""
    from phoenix_audit_agent.storage.gcs import get_storage_client, signed_get_url

    settings = get_settings()

    def _sign() -> str:
        client = get_storage_client()
        blob = client.bucket(settings.GCS_RECIPES_BUCKET).blob(blob_name)
        # No content-disposition: each artifact has a dedicated in-app viewer
        # (/report/[id]/json, /signature, /recipe/[id]) that fetches it
        # server-side; the signed URL only feeds those viewers + the
        # explicit "Download report.json" buttons inside each viewer.
        return signed_get_url(blob, ttl=timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS))

    return await asyncio.to_thread(_sign)


class RunListResponse(BaseModel):
    runs: list[RunRecord]
    # True when the filtered query hit the index-free window's cap — older
    # matching runs may exist beyond it (disclosed, never silent).
    truncated: bool = False


class RunDetailResponse(BaseModel):
    run: RunRecord
    artifact_urls: dict[str, str]
    # Artifacts whose URL signing FAILED — distinct from "artifact does not
    # exist" so the UI can show retry vs absent (CLAUDE.md pattern #4).
    artifact_url_errors: dict[str, str] = {}
    # Story-9.21: Phoenix deep-link config. null when PHOENIX_UI_BASE is
    # unset — the web renders NO deep-link affordance rather than a dead one.
    phoenix_ui_base: str | None = None
    phoenix_project: str | None = None


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    user: Annotated[AuthedUser, Depends(require_user)],
    agent_id: str | None = None,
    source: RunSource | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> RunListResponse:
    rows, truncated = await get_run_store().list_runs(
        agent_id=agent_id, source=source, limit=limit, visible_to=user.uid
    )
    return RunListResponse(runs=rows, truncated=truncated)


async def _detail_response(record: RunRecord) -> RunDetailResponse:
    """Fresh-sign every artifact URL the record has earned."""
    blob_names: dict[str, str] = {}
    if record.report_available:
        for name in REPORT_ARTIFACT_NAMES:
            blob_names[name] = f"reports/{record.run_id}/{name}"
    if record.events_available:
        blob_names["events.json"] = f"reports/{record.run_id}/events.json"
    if record.recipe_id:
        blob_names["recipe.md"] = f"{record.recipe_id}.md"

    urls: dict[str, str] = {}
    errors: dict[str, str] = {}
    if blob_names:
        signed: list[Any] = await asyncio.gather(
            *(sign_blob_url(b) for b in blob_names.values()), return_exceptions=True
        )
        for (name, blob), result in zip(blob_names.items(), signed, strict=True):
            if isinstance(result, BaseException):
                # A signing failure must not 500 the whole record view — but it
                # must stay DISTINGUISHABLE from "artifact does not exist".
                _log.error(
                    "artifact_url_sign_failed", run_id=record.run_id, blob=blob, error=str(result)
                )
                errors[name] = type(result).__name__
                continue
            urls[name] = result
    settings = get_settings()
    ui_base = settings.PHOENIX_UI_BASE.rstrip("/") or None
    return RunDetailResponse(
        run=record,
        artifact_urls=urls,
        artifact_url_errors=errors,
        phoenix_ui_base=ui_base,
        phoenix_project=settings.TARGET_PHOENIX_PROJECT if ui_base else None,
    )


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str, user: Annotated[AuthedUser, Depends(require_user)]
) -> RunDetailResponse:
    record = await get_run_store().get(run_id)
    # Foreign-owned reads as not-found — a 403 would CONFIRM the id exists.
    if record is None or record.owner_uid not in (None, user.uid):
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")
    return await _detail_response(record)


class EmailReportResponse(BaseModel):
    sent: bool
    to: str
    # False ⇒ the mail went out link-only (oversize PDF fallback) — the
    # caller must be able to tell, never assume the PDF rode along.
    attachment_included: bool


@router.post("/runs/{run_id}/email", response_model=EmailReportResponse)
async def email_report(
    run_id: str, user: Annotated[AuthedUser, Depends(require_user)]
) -> EmailReportResponse:
    """Email the signed report PDF to the VERIFIED token email — no free-text
    recipient, so this can never become a spam relay (story-9.5)."""
    # Lazy import: report_mail imports sign_blob_url from this module.
    from phoenix_audit_agent.notifier import report_mail
    from phoenix_audit_agent.notifier.email import email_configured

    if not email_configured():
        raise HTTPException(
            status_code=503, detail="email delivery not configured (RESEND_API_KEY unset)"
        )
    record = await get_run_store().get(run_id)
    if record is None or record.owner_uid not in (None, user.uid):
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")
    if not record.report_available:
        raise HTTPException(status_code=409, detail="report not yet available for this run")
    if not user.email:
        raise HTTPException(
            status_code=422, detail="signed-in account has no email address on its token"
        )
    try:
        result = await report_mail.send_report_email(record, to=user.email)
    except Exception as exc:
        # PDF download / signing infrastructure failure — visible, never a
        # pretend-sent. The class name is enough detail for the UI + logs.
        _log.error("report_email_failed", run_id=run_id, exc_info=True)
        raise HTTPException(
            status_code=502, detail=f"report email failed: {type(exc).__name__}"
        ) from exc
    if not result.sent:
        raise HTTPException(status_code=502, detail=f"report email failed: {result.error}")
    return EmailReportResponse(
        sent=True, to=result.to, attachment_included=result.attachment_included
    )


@router.get("/featured-run", response_model=RunDetailResponse)
async def featured_run() -> RunDetailResponse:
    """Public (deliberately unauthenticated) — the newest ownerless finished
    run with a replay timeline. Backs the landing /replay showcase; owned
    runs can never surface here."""
    rows, truncated = await get_run_store().list_runs(limit=200, visible_to=None)
    for record in rows:
        if record.owner_uid is None and record.phase == "succeeded" and record.events_available:
            return await _detail_response(record)
    if truncated:
        # Samples may exist beyond the newest-200 window — disclosed, so the
        # public showcase going dark under growth is greppable, not silent.
        _log.warning("featured_run_404_window_truncated", scanned=len(rows))
    raise HTTPException(status_code=404, detail="no featured run available")


__all__ = ["router", "sign_blob_url"]
