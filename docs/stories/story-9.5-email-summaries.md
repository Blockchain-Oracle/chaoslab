# story-9.5 — email-summaries: Resend delivery + "Email me this report"

**Epic:** 9 · **Depends on:** story-9.3 (monitoring-scheduler — `deliver_email` flag), story-9.12 (user-profile — owner email lookup)
**Source:** Wave C1 in the unified-finish plan (`~/.claude/plans/there-i-want-you-toasty-ember.md`). Recovered S9.5 scope PLUS the "Email me this report" button Abu locked 2026-06-10.

## Why

A Director of AI Governance doesn't live in our portal — they live in their inbox. Two delivery moments matter: (1) a **scheduled** monitoring audit finishes and the owner gets a verdict summary with a link to the signed evidence, without ever opening the app; (2) a user reading a finished report clicks **"Email me this report"** and the signed PDF lands in their inbox as a forwardable, regulator-ready artifact. Today `ScheduleRecord.deliver_email` exists but nothing reads it — the flag is a silent lie in the UI.

Delivery is Resend (`resend` Python SDK, `Emails.send_async`), sender `reports@phxaudit.xyz` (domain added in Resend eu-west-1; DNS verification completes with C3). Mail is a **notification channel, never an audit dependency**: a Resend outage must not fail a run, and a fallback path must disclose itself (CLAUDE.md silent-failure rule 4).

## BDD acceptance criteria

- **Given** `RESEND_API_KEY` is unset, **then** `email_configured()` is `False`, `POST /runs/{run_id}/email` returns **503** with a "not configured" detail, and the scheduled-summary hook logs `email_skipped_not_configured` and returns without raising. Fail-closed, loud, contained.
- **Given** a schedule with `deliver_email=True` fires and its run finalizes, **then** the finalize path sends a summary email to **the schedule's `email_recipient`** (the story-9.3 contract — the schedules API 422s `deliver_email=true` without it; profile email is only the legacy-schedule fallback) containing: target URL, pass/fail/error tally, and a fresh-signed report link when `report_available` (link via the existing `sign_blob_url` seam). **Given** `deliver_email=False`, **then** no send is attempted. **Given** neither schedule nor profile carries an address, **then** the send is skipped with a structured `schedule_email_skipped_no_address` warning. **Given** Resend raises, **then** the finalize still completes — the failure is logged, never propagated. _(AMENDED per PR #111 review: original spec said profile email; that silently bypassed the recipient story-9.3 makes users configure.)_
- **Given** a scheduled run CRASHES (any non-`succeeded` phase at the crash finalize), **then** the owner still gets an email — subject `Scheduled audit FAILED — <target>`, crash wording, no fabricated tally. A silent inbox must never be mistakable for "all healthy". _(ADDED per PR #111 review MED-4.)_
- **Given** the oversize-attachment fallback AND a signing failure compose on the button path (no attachment AND no link), **then** `send_report_email` raises and the endpoint 502s — an artifact email carrying neither artifact nor route to it must never send. _(ADDED per PR #111 review HIGH-2.)_
- **Given** a scheduled run, **when** it is launched by the tick, **then** `RunRequest.schedule_id` carries the schedule's id into `RunRecord.schedule_id` (persisted), so the finalize hook can resolve `deliver_email` without a side-channel. Manual runs persist `schedule_id=None`.
- **Given** an authenticated owner (or any signed-in user for a sample run, `owner_uid is None`) calls `POST /runs/{run_id}/email` on a run with `report_available=True`, **then** the signed PDF (`reports/{run_id}/report.pdf`) is fetched from GCS and sent as an attachment to the **token email**, with a fresh-signed report link in the body, and the response is `{"sent": true, "to": <email>, "attachment_included": true}`. A non-owner's request returns **404** (existence not disclosed). A run with `report_available=False` returns **409**. A token without an email claim returns **422**.
- **Given** the PDF exceeds the attachment cap (25 MB raw — base64 inflates ~4/3× toward Resend's 40 MB message limit), **then** the email still sends link-only and the response discloses `"attachment_included": false` — the fallback is visible, never silent.
- **Given** Resend errors on the button path, **then** the endpoint returns **502** with the error class in the detail — the user sees the failure; nothing pretends to have sent.
- **Given** the report page for a finished run with `report_available`, **then** an "Email me this report" button renders; clicking it POSTs through the proxy and shows explicit sent/failure state (vitest). The proxy allowlist admits `runs/{run_id}/email` (allowlist test updated).
- Offline tests only: the Resend SDK call is a module-attribute seam (`notifier.email.send_async`-style) monkeypatched in tests; no network, no `@pytest.mark.online`.

## File map

- Settings: `apps/phoenix-audit-agent/src/phoenix_audit_agent/config.py` — `RESEND_API_KEY: SecretStr | None = None`, `EMAIL_FROM: str = "Phoenix Audit <reports@phxaudit.xyz>"`, `PUBLIC_WEB_URL: str = ""` (portal links in email bodies; empty ⇒ link row omitted, never a localhost link in a customer inbox).
- NEW `apps/phoenix-audit-agent/src/phoenix_audit_agent/notifier/__init__.py` + `notifier/email.py` — Resend primitive: `email_configured()`, `EmailSendResult` model (`sent`, `to`, `attachment_included`, `error`), `send_email(*, to, subject, html, attachment=None)`; contained `resend.ResendError` + unexpected-exception handling; sets `resend.api_key` per call from Settings (never at import).
- NEW `notifier/report_mail.py` — composition layer: `send_report_email(record, *, to)` (PDF bytes via `storage.gcs`, cap check, signed link) and `maybe_send_scheduled_summary(run_id)` (registry → schedule → profile email → summary send; every arm contained + logged).
- `apps/phoenix-audit-agent/src/phoenix_audit_agent/storage/models.py` — `RunRecord.schedule_id: str | None = None`.
- `apps/phoenix-audit-agent/src/phoenix_audit_agent/main.py` — `RunRequest.schedule_id: str | None = None`; `_launch_scheduled_run` forwards `schedule.schedule_id`; `launch_run` persists it on the created record.
- `apps/phoenix-audit-agent/src/phoenix_audit_agent/audit_runner_emit.py` — `finalize_run` tail calls `maybe_send_scheduled_summary(run_id)` (contained; after completion persist + complete frame so a mail outage can't delay the UI).
- `apps/phoenix-audit-agent/src/phoenix_audit_agent/api/runs.py` — `POST /runs/{run_id}/email` (`require_user`, owner/sample scope identical to `get_run`).
- `apps/phoenix-audit-agent/pyproject.toml` — add `resend` dependency.
- Web: `apps/phoenix-audit-web/app/api/agent/[...path]/route.ts` — allowlist `+/^runs\/[a-zA-Z0-9_-]+\/email$/`; `lib/email-report.ts` (NEW — pure request + state/label logic, per the project's node-env vitest idiom) + `components/artifacts/email-report-button.tsx` (NEW — thin client component: idle/sending/sent/failed) mounted on the report page next to the download actions.
- Tests: `apps/phoenix-audit-agent/tests/unit/notifier/test_email.py` (NEW), `tests/unit/notifier/test_report_mail.py` (NEW), `tests/unit/api/test_runs_email_api.py` (NEW), schedule-id threading asserts in a NEW `tests/unit/test_schedule_id_threading.py`, finalize-hook wiring in `tests/unit/test_finalize_email_hook.py` (NEW); web `tests/proxy-allowlist.test.ts` (extend) + `tests/email-report.test.ts` (NEW).

## Notes

- **Live-send verification is deliberately out of scope** for this story's gates: `reports@phxaudit.xyz` sends real mail only after Abu's remaining Resend DNS rows land + the dashboard Verify click (C3). The story ships offline-tested; the C3 task includes one real send as its smoke.
- Recipient policy: the button sends ONLY to the verified token email (`AuthedUser.email`) — no free-text recipient field, so the endpoint can't be turned into a spam relay.
- `resend.api_key` is module-global state in the SDK; set it inside the send wrapper from `get_settings().RESEND_API_KEY` so tests can rebuild Settings without import-order traps. The SecretStr unwraps only at that boundary.
- Attachment content rides as base64 `str` in the SDK's `Attachment` TypedDict (`{"content": <b64>, "filename": "phoenix-audit-<run_id>.pdf", "content_type": "application/pdf"}`).
- The scheduled-summary hook reads the persisted `RunRecord` (registry get by `run_id`) rather than threading schedule/email params through `drive_audit` — one new field on the record beats five new parameters through the pipeline.
- `notifier/` keeps both modules well under the 400-line cap; the emit module gains only the one contained call.
- GCS PDF fetch runs in `asyncio.to_thread` like `sign_blob_url`; a download failure on the button path is a 502 (visible), on the summary path contained (link-only summary still sends — disclosed via `attachment_included=False` in the log line).
