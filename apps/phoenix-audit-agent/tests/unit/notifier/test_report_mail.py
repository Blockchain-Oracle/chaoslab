"""notifier/report_mail.py — report email + scheduled-summary composition
(story-9.5). Every send is offline: `send_email`, `sign_blob_url`, and the
PDF download are module-attribute seams monkeypatched here.
"""

from __future__ import annotations

import base64
import os
from collections.abc import Iterator
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import profiles as profile_storage
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage import schedules as schedule_storage
from phoenix_audit_agent.storage.models import RunRecord, ScheduleRecord

from ..storage.fakes import InMemoryProfileStore, InMemoryRunStore, InMemoryScheduleStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "RESEND_", "EMAIL_", "PUBLIC_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    schedule_storage.set_schedule_store(InMemoryScheduleStore())
    profile_storage.set_profile_store(InMemoryProfileStore())
    yield
    run_storage.set_run_store(None)
    schedule_storage.set_schedule_store(None)
    profile_storage.set_profile_store(None)
    get_settings.cache_clear()


class _SendSpy:
    """Captures send_email kwargs; configurable result/exception."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raises: Exception | None = None

    async def __call__(self, **kwargs: Any) -> Any:
        from phoenix_audit_agent.notifier.email import EmailSendResult

        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return EmailSendResult(
            sent=True,
            to=kwargs["to"],
            attachment_included=kwargs.get("attachment") is not None,
        )


@pytest.fixture
def send_spy(monkeypatch: pytest.MonkeyPatch) -> _SendSpy:
    from phoenix_audit_agent.notifier import report_mail

    spy = _SendSpy()
    monkeypatch.setattr(report_mail, "send_email", spy)

    async def fake_sign(blob_name: str) -> str:
        return f"https://signed.example/{blob_name}"

    monkeypatch.setattr(report_mail, "sign_blob_url", fake_sign)
    return spy


def _record(run_id: str = "run_abc123def456", **kw: Any) -> RunRecord:
    defaults: dict[str, Any] = {
        "target_url": "https://target.example",
        "created_at": "2026-06-11T10:00:00Z",
        "phase": "succeeded",
        "passed": 6,
        "failed": 2,
        "report_available": True,
        "owner_uid": "user-a",
    }
    defaults.update(kw)
    return RunRecord(run_id=run_id, **defaults)


# --- send_report_email ---------------------------------------------------------


async def test_report_email_attaches_pdf(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    from phoenix_audit_agent.notifier import report_mail

    pdf = b"%PDF-1.7 fake report bytes"

    async def fake_download(run_id: str) -> bytes:
        assert run_id == "run_abc123def456"
        return pdf

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    result = await report_mail.send_report_email(_record(), to="a@example.com")

    assert result.sent is True
    assert result.attachment_included is True
    assert len(send_spy.calls) == 1
    call = send_spy.calls[0]
    assert call["to"] == "a@example.com"
    attachment = call["attachment"]
    assert attachment["filename"] == "phoenix-audit-run_abc123def456.pdf"
    assert attachment["content_type"] == "application/pdf"
    assert attachment["content"] == base64.b64encode(pdf).decode("ascii")
    # The body carries a fresh-signed link to the PDF artifact.
    assert "https://signed.example/reports/run_abc123def456/report.pdf" in call["html"]


async def test_report_email_oversize_pdf_falls_back_to_link_only(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """Past the cap the mail still goes out link-only — and the fallback is
    DISCLOSED via attachment_included=False (docs/architecture.md pattern #4)."""
    from phoenix_audit_agent.notifier import report_mail

    monkeypatch.setattr(report_mail, "ATTACHMENT_CAP_BYTES", 8)

    async def fake_download(run_id: str) -> bytes:
        return b"way more than eight bytes"

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    result = await report_mail.send_report_email(_record(), to="a@example.com")

    assert result.sent is True
    assert result.attachment_included is False
    assert send_spy.calls[0]["attachment"] is None
    assert "report.pdf" in send_spy.calls[0]["html"]


async def test_report_email_download_failure_propagates(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """The button path surfaces a dead artifact loudly (endpoint maps it to
    502) — sending a report email without its report would be a silent lie."""
    from phoenix_audit_agent.notifier import report_mail

    async def fake_download(run_id: str) -> bytes:
        raise RuntimeError("gcs unavailable")

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    with pytest.raises(RuntimeError, match="gcs unavailable"):
        await report_mail.send_report_email(_record(), to="a@example.com")
    assert send_spy.calls == []


async def test_report_email_sign_failure_contained(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """A broken link row must never block a perfectly good PDF — the mail
    still sends, attachment intact, link row omitted."""
    from phoenix_audit_agent.notifier import report_mail

    async def fake_download(run_id: str) -> bytes:
        return b"%PDF-1.7 fine"

    async def bad_sign(blob_name: str) -> str:
        raise RuntimeError("signing infrastructure down")

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    monkeypatch.setattr(report_mail, "sign_blob_url", bad_sign)
    result = await report_mail.send_report_email(_record(), to="a@example.com")

    assert result.sent is True
    assert result.attachment_included is True
    assert "Download the signed report" not in send_spy.calls[0]["html"]


async def test_report_email_raises_when_no_attachment_and_no_link(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """The two contained fallbacks must not COMPOSE into an artifact email
    with neither artifact nor route to it — raise (endpoint maps to 502)."""
    from phoenix_audit_agent.notifier import report_mail

    monkeypatch.setattr(report_mail, "ATTACHMENT_CAP_BYTES", 8)

    async def fake_download(run_id: str) -> bytes:
        return b"way more than eight bytes"

    async def bad_sign(blob_name: str) -> str:
        raise RuntimeError("signing infrastructure down")

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    monkeypatch.setattr(report_mail, "sign_blob_url", bad_sign)
    with pytest.raises(RuntimeError, match="neither attachment nor link"):
        await report_mail.send_report_email(_record(), to="a@example.com")
    assert send_spy.calls == []


async def test_report_email_escapes_hostile_target_url(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    from phoenix_audit_agent.notifier import report_mail

    async def fake_download(run_id: str) -> bytes:
        return b"%PDF-1.7"

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    record = _record(target_url="https://x.example/<script>alert(1)</script>")
    await report_mail.send_report_email(record, to="a@example.com")
    html = send_spy.calls[0]["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


async def test_report_email_portal_link_branches(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """Empty PUBLIC_WEB_URL ⇒ no portal row (never a localhost link in a
    customer inbox); set ⇒ rstripped origin + /report/{run_id}."""
    from phoenix_audit_agent.notifier import report_mail

    async def fake_download(run_id: str) -> bytes:
        return b"%PDF-1.7"

    monkeypatch.setattr(report_mail, "download_report_pdf", fake_download)
    await report_mail.send_report_email(_record(), to="a@example.com")
    assert "View this audit" not in send_spy.calls[0]["html"]

    monkeypatch.setenv("PUBLIC_WEB_URL", "https://phxaudit.xyz/")
    get_settings.cache_clear()
    await report_mail.send_report_email(_record(), to="a@example.com")
    assert "https://phxaudit.xyz/report/run_abc123def456" in send_spy.calls[1]["html"]


# --- maybe_send_scheduled_summary -----------------------------------------------


async def _seed(
    *,
    deliver_email: bool = True,
    profile_email: str | None = "a@example.com",
    schedule_owner: str | None = "user-a",
    email_recipient: str | None = None,
    record_kw: dict[str, Any] | None = None,
) -> RunRecord:
    record = _record(schedule_id="sch_1", **(record_kw or {}))
    await run_storage.get_run_store().create(record)
    await schedule_storage.get_schedule_store().upsert(
        ScheduleRecord(
            schedule_id="sch_1",
            target_url="https://target.example",
            owner_uid=schedule_owner,
            deliver_email=deliver_email,
            email_recipient=email_recipient,
            next_fire_at="2026-06-11T00:00:00+00:00",
            created_at="2026-06-11T00:00:00+00:00",
        )
    )
    if profile_email is not None:
        await profile_storage.get_profile_store().merge(
            "user-a", {"uid": "user-a", "email": profile_email}
        )
    return record


async def test_summary_sent_when_deliver_email(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed()
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")

    assert len(send_spy.calls) == 1
    call = send_spy.calls[0]
    assert call["to"] == "a@example.com"
    assert "https://target.example" in call["html"]
    # Verdict tally is the summary's payload — both counts must appear.
    assert "6" in call["html"]
    assert "2" in call["html"]
    # Fresh-signed report link included when report_available.
    assert "https://signed.example/reports/run_abc123def456/report.pdf" in call["html"]
    # Summaries never attach the PDF — link-only by design.
    assert call.get("attachment") is None


async def test_summary_prefers_schedule_email_recipient(send_spy: _SendSpy) -> None:
    """story-9.3 contract: the schedules API requires email_recipient when
    deliver_email=true and the UI collects it — it must NOT be silently
    rerouted to the profile address."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed(email_recipient="compliance-team@corp.example")
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert len(send_spy.calls) == 1
    assert send_spy.calls[0]["to"] == "compliance-team@corp.example"


async def test_summary_crashed_run_sends_failure_wording(send_spy: _SendSpy) -> None:
    """A crashed monitoring run must email too — and must never read as
    'complete — 0 passed / 0 failed'."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed(record_kw={"phase": "failed", "passed": 0, "failed": 0})
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert len(send_spy.calls) == 1
    call = send_spy.calls[0]
    assert "FAILED" in call["subject"]
    assert "complete" not in call["subject"]
    assert "FAILED before completing" in call["html"]


async def test_summary_mid_pipeline_phase_reads_as_crash(send_spy: _SendSpy) -> None:
    """When the crash-path events write also failed, the record keeps a
    mid-pipeline phase — any non-succeeded phase gets crash wording."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed(record_kw={"phase": "judge"})
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert "FAILED" in send_spy.calls[0]["subject"]


async def test_summary_skipped_when_deliver_email_false(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed(deliver_email=False)
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []


async def test_summary_skipped_for_manual_runs(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    record = _record()  # no schedule_id
    await run_storage.get_run_store().create(record)
    await report_mail.maybe_send_scheduled_summary(record.run_id)
    assert send_spy.calls == []


async def test_summary_skipped_without_profile_email(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed(profile_email=None)
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []


async def test_summary_skipped_on_owner_mismatch(send_spy: _SendSpy) -> None:
    """A run claiming a schedule owned by someone else must not trigger mail —
    defense in depth against a forged schedule_id on the record."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed(schedule_owner="user-b")
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []


async def test_summary_skipped_when_schedule_deleted(send_spy: _SendSpy) -> None:
    """Lifecycle race: schedule deleted while its run was in flight — the
    record's schedule_id dangles; finalize must skip, not AttributeError."""
    from phoenix_audit_agent.notifier import report_mail

    record = _record(schedule_id="sch_gone")
    await run_storage.get_run_store().create(record)
    await report_mail.maybe_send_scheduled_summary(record.run_id)
    assert send_spy.calls == []


async def test_summary_skipped_with_blank_profile_email(send_spy: _SendSpy) -> None:
    """email='' is falsy-but-present (silent-failure pattern #1) — a profile
    stored with a blank address must skip, never send to ''."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed(profile_email="")
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []


async def test_summary_skipped_with_null_profile_email(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed(profile_email=None)
    await profile_storage.get_profile_store().merge("user-a", {"uid": "user-a", "email": None})
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []


async def test_summary_sign_failure_still_sends(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    """A signing outage degrades the summary (no link row) — it must not
    kill the send."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed()

    async def bad_sign(blob_name: str) -> str:
        raise RuntimeError("signing infrastructure down")

    monkeypatch.setattr(report_mail, "sign_blob_url", bad_sign)
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert len(send_spy.calls) == 1
    assert "Download the signed report" not in send_spy.calls[0]["html"]


async def test_summary_without_report_omits_link_row(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed(record_kw={"report_available": False})
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert len(send_spy.calls) == 1
    assert "Download the signed report" not in send_spy.calls[0]["html"]


async def test_summary_send_failure_contained(send_spy: _SendSpy) -> None:
    """A mail outage must never fail (or even surface from) the finalize."""
    from phoenix_audit_agent.notifier import report_mail

    await _seed()
    send_spy.raises = RuntimeError("resend exploded")
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")  # no raise


async def test_summary_missing_run_contained(send_spy: _SendSpy) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await report_mail.maybe_send_scheduled_summary("run_nonexistent0")  # no raise
    assert send_spy.calls == []


async def test_summary_skipped_when_not_configured(
    monkeypatch: pytest.MonkeyPatch, send_spy: _SendSpy
) -> None:
    from phoenix_audit_agent.notifier import report_mail

    await _seed()
    monkeypatch.delenv("RESEND_API_KEY")
    get_settings.cache_clear()
    await report_mail.maybe_send_scheduled_summary("run_abc123def456")
    assert send_spy.calls == []
