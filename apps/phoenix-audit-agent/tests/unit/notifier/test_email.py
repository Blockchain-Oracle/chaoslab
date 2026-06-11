"""notifier/email.py — the Resend send primitive (story-9.5).

Offline by design: the SDK call is the module attribute `send_async`,
monkeypatched here. No network, no @pytest.mark.online.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "RESEND_", "EMAIL_", "PUBLIC_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _configure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    get_settings.cache_clear()


# --- configuration gate -------------------------------------------------------


def test_not_configured_without_key() -> None:
    from phoenix_audit_agent.notifier import email

    assert email.email_configured() is False


def test_configured_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.notifier import email

    _configure(monkeypatch)
    assert email.email_configured() is True


def test_empty_key_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """`RESEND_API_KEY=` (present but empty) must fail the gate — an empty
    SecretStr would otherwise pass is-None and auth-fail on every send."""
    from phoenix_audit_agent.notifier import email

    monkeypatch.setenv("RESEND_API_KEY", "")
    get_settings.cache_clear()
    assert email.email_configured() is False


async def test_send_unconfigured_fails_closed_without_sdk_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No key ⇒ sent=False + 'not_configured' error; the SDK is never touched."""
    from phoenix_audit_agent.notifier import email

    called = False

    async def boom(params: dict[str, Any]) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"id": "never"}

    monkeypatch.setattr(email, "send_async", boom)
    result = await email.send_email(to="a@example.com", subject="s", html="<p>x</p>")
    assert result.sent is False
    assert result.error is not None
    assert "not_configured" in result.error
    assert called is False


# --- happy path ---------------------------------------------------------------


async def test_send_success_params_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.notifier import email

    _configure(monkeypatch)
    captured: dict[str, Any] = {}

    async def fake_send(params: dict[str, Any]) -> dict[str, Any]:
        captured.update(params)
        return {"id": "email_123"}

    monkeypatch.setattr(email, "send_async", fake_send)
    result = await email.send_email(to="a@example.com", subject="Audit done", html="<p>hi</p>")

    assert result.sent is True
    assert result.to == "a@example.com"
    assert result.error is None
    assert captured["to"] == ["a@example.com"]
    assert captured["subject"] == "Audit done"
    assert captured["html"] == "<p>hi</p>"
    # Sender comes from Settings — the default is the verified product domain.
    assert captured["from"] == get_settings().EMAIL_FROM
    assert "phxaudit.xyz" in captured["from"]
    # The API key is applied at the send boundary, from the SecretStr.
    assert email.resend.api_key == "re_test_key"


async def test_send_attachment_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.notifier import email

    _configure(monkeypatch)
    captured: dict[str, Any] = {}

    async def fake_send(params: dict[str, Any]) -> dict[str, Any]:
        captured.update(params)
        return {"id": "email_456"}

    monkeypatch.setattr(email, "send_async", fake_send)
    attachment = {
        "content": "aGVsbG8=",
        "filename": "phoenix-audit-run_x.pdf",
        "content_type": "application/pdf",
    }
    result = await email.send_email(
        to="a@example.com", subject="s", html="<p>x</p>", attachment=attachment
    )
    assert result.sent is True
    assert result.attachment_included is True
    assert captured["attachments"] == [attachment]


async def test_send_no_attachment_key_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """No attachment ⇒ no 'attachments' key — an empty list is a different
    statement to the API than an absent field."""
    from phoenix_audit_agent.notifier import email

    _configure(monkeypatch)
    captured: dict[str, Any] = {}

    async def fake_send(params: dict[str, Any]) -> dict[str, Any]:
        captured.update(params)
        return {"id": "email_789"}

    monkeypatch.setattr(email, "send_async", fake_send)
    result = await email.send_email(to="a@example.com", subject="s", html="<p>x</p>")
    assert result.attachment_included is False
    assert "attachments" not in captured


# --- containment --------------------------------------------------------------


async def test_send_failure_contained(monkeypatch: pytest.MonkeyPatch) -> None:
    """An SDK error becomes a sent=False result — never an exception. The
    error string names the failure class so logs stay diagnosable."""
    from phoenix_audit_agent.notifier import email

    _configure(monkeypatch)

    class FakeResendDownError(RuntimeError):
        pass

    async def fake_send(params: dict[str, Any]) -> dict[str, Any]:
        raise FakeResendDownError("resend is down")

    monkeypatch.setattr(email, "send_async", fake_send)
    result = await email.send_email(to="a@example.com", subject="s", html="<p>x</p>")
    assert result.sent is False
    assert result.error is not None
    assert "FakeResendDown" in result.error
