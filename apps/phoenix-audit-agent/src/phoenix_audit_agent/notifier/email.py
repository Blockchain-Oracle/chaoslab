"""The Resend send primitive (story-9.5).

Fail-closed when unconfigured, contained on SDK failure — a mail outage is
a logged, disclosed non-event, never an exception escaping into an audit
run or an unhandled 500.
"""

from __future__ import annotations

from typing import Any, cast

import resend
import structlog
from pydantic import BaseModel

from phoenix_audit_agent.config import get_settings

_log = structlog.get_logger(__name__)

# Module-attribute seam: the SDK call never leaves this module, and tests
# monkeypatch this name instead of the SDK class attribute.
send_async = resend.Emails.send_async


class EmailSendResult(BaseModel):
    """Outcome of one send. `sent=False` + `error` is the contained-failure
    shape — callers decide whether to surface (button: 502) or log (summary)."""

    sent: bool
    to: str
    attachment_included: bool = False
    error: str | None = None


def email_configured() -> bool:
    # `RESEND_API_KEY=` (present but empty) must fail the gate too — an empty
    # SecretStr would pass an is-None check and then auth-fail on every send.
    key = get_settings().RESEND_API_KEY
    return key is not None and bool(key.get_secret_value())


async def send_email(
    *, to: str, subject: str, html: str, attachment: dict[str, Any] | None = None
) -> EmailSendResult:
    """Send one email via Resend. `attachment` is the SDK's Attachment shape
    (base64 `content` + `filename` + `content_type`); None ⇒ the params carry
    no `attachments` key at all (an empty list is a different API statement).
    """
    settings = get_settings()
    if settings.RESEND_API_KEY is None:
        _log.warning("email_skipped_not_configured", to=to, subject=subject)
        return EmailSendResult(sent=False, to=to, error="not_configured: RESEND_API_KEY unset")
    # The SDK keeps the key as module-global state; apply it at the send
    # boundary so Settings rebuilds (tests, key rotation) take effect.
    resend.api_key = settings.RESEND_API_KEY.get_secret_value()
    params: dict[str, Any] = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if attachment is not None:
        params["attachments"] = [attachment]
    try:
        response = await send_async(cast("resend.Emails.SendParams", params))
    except Exception as exc:
        # Deliberately broad: mail must NEVER raise into a caller. The error
        # class rides in the result so the failure stays diagnosable.
        _log.error(
            "email_send_failed",
            to=to,
            subject=subject,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return EmailSendResult(sent=False, to=to, error=f"{type(exc).__name__}: {exc}")
    email_id = response.get("id") if isinstance(response, dict) else None
    _log.info("email_sent", to=to, subject=subject, email_id=email_id)
    return EmailSendResult(sent=True, to=to, attachment_included=attachment is not None)


__all__ = ["EmailSendResult", "email_configured", "send_email"]
