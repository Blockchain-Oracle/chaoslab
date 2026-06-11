"""Report-email + scheduled-summary composition (story-9.5).

Two senders, two failure postures:
- `send_report_email` (the button) — a dead PDF artifact PROPAGATES so the
  endpoint can 502; emailing "your signed report" without the report would
  be a silent lie.
- `maybe_send_scheduled_summary` (the finalize hook) — contained end-to-end;
  a mail problem must never fail, or even surface from, an audit finalize.
"""

from __future__ import annotations

import asyncio
import base64
from html import escape

import structlog

from phoenix_audit_agent.api.runs import sign_blob_url
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.notifier.email import EmailSendResult, email_configured, send_email
from phoenix_audit_agent.storage.models import RunRecord
from phoenix_audit_agent.storage.profiles import get_profile_store
from phoenix_audit_agent.storage.runs import get_run_store
from phoenix_audit_agent.storage.schedules import get_schedule_store

_log = structlog.get_logger(__name__)

# Resend's hard cap is 40 MB per message AFTER base64 inflation (~4/3x).
# 25 MB of raw PDF encodes to ~33 MB, leaving headroom for headers + body.
ATTACHMENT_CAP_BYTES = 25 * 1024 * 1024


async def download_report_pdf(run_id: str) -> bytes:
    """Module attribute = test seam. Blocking GCS read runs in a thread."""
    from phoenix_audit_agent.storage.gcs import get_storage_client

    settings = get_settings()

    def _download() -> bytes:
        client = get_storage_client()
        blob = client.bucket(settings.GCS_RECIPES_BUCKET).blob(f"reports/{run_id}/report.pdf")
        return blob.download_as_bytes()

    return await asyncio.to_thread(_download)


async def _signed_report_url(record: RunRecord) -> str | None:
    """Fresh-signed PDF link, or None (contained) — an email with a working
    attachment but a broken link row is still worth sending."""
    if not record.report_available:
        return None
    try:
        return await sign_blob_url(f"reports/{record.run_id}/report.pdf")
    except Exception:
        _log.error("email_report_link_sign_failed", run_id=record.run_id, exc_info=True)
        return None


def _link_rows(record: RunRecord, report_url: str | None) -> list[str]:
    rows: list[str] = []
    if report_url is not None:
        rows.append(f'<p><a href="{escape(report_url)}">Download the signed report (PDF)</a></p>')
    portal = get_settings().PUBLIC_WEB_URL.rstrip("/")
    if portal:
        rows.append(
            f'<p><a href="{escape(portal)}/report/{escape(record.run_id)}">'
            "View this audit in Phoenix Audit</a></p>"
        )
    return rows


def _tally_row(record: RunRecord) -> str:
    return (
        f"<p>Verdict: <strong>{record.passed} passed</strong> · "
        f"<strong>{record.failed} failed</strong> · {record.errored} errored · "
        f"{record.transport_failed} transport-failed.</p>"
    )


async def send_report_email(record: RunRecord, *, to: str) -> EmailSendResult:
    """Email the signed PDF to `to`. Oversize PDFs fall back to link-only —
    DISCLOSED via `attachment_included=False`, never silent."""
    pdf = await download_report_pdf(record.run_id)
    attachment: dict[str, str] | None = None
    if len(pdf) <= ATTACHMENT_CAP_BYTES:
        attachment = {
            "content": base64.b64encode(pdf).decode("ascii"),
            "filename": f"phoenix-audit-{record.run_id}.pdf",
            "content_type": "application/pdf",
        }
    else:
        _log.warning(
            "report_email_attachment_omitted_oversize",
            run_id=record.run_id,
            size_bytes=len(pdf),
            cap_bytes=ATTACHMENT_CAP_BYTES,
        )
    report_url = await _signed_report_url(record)
    if attachment is None and report_url is None:
        # The two contained fallbacks must not COMPOSE into an artifact email
        # carrying neither artifact nor route to it. With no attachment the
        # signed link is load-bearing — raise so the endpoint 502s honestly.
        msg = f"report email for {record.run_id} would carry neither attachment nor link"
        raise RuntimeError(msg)
    html = "\n".join(
        [
            f"<p>Here is the signed audit report for <strong>{escape(record.target_url)}</strong> "
            f"(run <code>{escape(record.run_id)}</code>).</p>",
            _tally_row(record),
            *_link_rows(record, report_url),
        ]
    )
    return await send_email(
        to=to,
        subject=f"Your signed audit report — {record.run_id}",
        html=html,
        attachment=attachment,
    )


async def maybe_send_scheduled_summary(run_id: str) -> None:
    """Finalize hook: when the run was launched by a schedule with
    `deliver_email`, email the owner a verdict summary. Contained end-to-end."""
    try:
        await _send_scheduled_summary(run_id)
    except Exception:
        _log.error("schedule_email_failed", run_id=run_id, exc_info=True)


async def _send_scheduled_summary(run_id: str) -> None:
    record = await get_run_store().get(run_id)
    if record is None or record.schedule_id is None:
        return
    schedule = await get_schedule_store().get(record.schedule_id)
    if schedule is None:
        # A dangling schedule_id is an anomaly (schedule deleted mid-run),
        # not a by-design skip — distinct log from deliver_email=False.
        _log.warning(
            "schedule_email_skipped_schedule_missing",
            run_id=run_id,
            schedule_id=record.schedule_id,
        )
        return
    if not schedule.deliver_email:
        return
    # A send is OWED from here down — config/address problems are warnings.
    if not email_configured():
        _log.warning("email_skipped_not_configured", run_id=run_id)
        return
    if record.owner_uid is None or schedule.owner_uid != record.owner_uid:
        # Defense in depth: a record claiming a schedule it doesn't own must
        # never trigger mail (forged-linkage guard; see story-9.5 notes).
        # Both owners ride in the log so ops can tell "ownerless sample with
        # a dangling linkage" from a genuine forged-linkage signal.
        _log.warning(
            "schedule_email_skipped_owner_mismatch",
            run_id=run_id,
            schedule_id=record.schedule_id,
            record_owner=record.owner_uid,
            schedule_owner=schedule.owner_uid,
        )
        return
    # Recipient: the schedule's own email_recipient is the story-9.3 contract
    # (the schedules API 422s deliver_email=true without it; the monitoring UI
    # collects it) — profile email is only the fallback for legacy schedules.
    address = schedule.email_recipient
    if not address:
        profile = await get_profile_store().get(record.owner_uid)
        address = profile.email if profile is not None else None
    if not address:
        _log.warning("schedule_email_skipped_no_address", run_id=run_id, owner_uid=record.owner_uid)
        return
    if record.phase != "succeeded":
        # Crash wording for ANY non-succeeded phase — when the crash-path
        # events write also failed, the record may still carry a mid-pipeline
        # phase; "complete — 0 passed / 0 failed" would be a lie. A silent
        # inbox must never be mistakable for "all healthy" — the crash of a
        # monitoring run is the summary that matters MOST.
        subject = f"Scheduled audit FAILED — {record.target_url}"
        body_rows = [
            f"<p>Scheduled audit of <strong>{escape(record.target_url)}</strong> "
            "<strong>FAILED before completing</strong>. Any partial timeline is "
            "preserved for replay.</p>",
            *_link_rows(record, None),
        ]
    else:
        subject = f"Scheduled audit complete — {record.passed} passed / {record.failed} failed"
        report_url = await _signed_report_url(record)
        body_rows = [
            f"<p>Scheduled audit of <strong>{escape(record.target_url)}</strong> finished.</p>",
            _tally_row(record),
            *_link_rows(record, report_url),
        ]
    # Summaries are link-only by design — the signed PDF attaches on the
    # explicit "Email me this report" path, not on every scheduled run.
    result = await send_email(
        to=address, subject=subject, html="\n".join(body_rows), attachment=None
    )
    if not result.sent:
        _log.error("schedule_email_send_failed", run_id=run_id, error=result.error)


__all__ = [
    "ATTACHMENT_CAP_BYTES",
    "download_report_pdf",
    "maybe_send_scheduled_summary",
    "send_report_email",
]
