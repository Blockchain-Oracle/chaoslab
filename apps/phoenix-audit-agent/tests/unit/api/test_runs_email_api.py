"""POST /runs/{run_id}/email — "Email me this report" (story-9.5).

Recipient is ALWAYS the verified token email — no free-text recipient, so
the endpoint can't be turned into a spam relay. Composition is delegated to
notifier.report_mail (monkeypatched seam); this module tests the HTTP
contract: auth scope, config gate, state guards, failure disclosure.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import RunRecord

from ..storage.fakes import InMemoryRunStore

RUN_ID = "run_abc123def456"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_", "RESEND_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Callable[..., None]) -> Callable[..., None]:
    auth_as(uid="user-a", email="a@example.com")
    return auth_as


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def send_spy(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace report_mail.send_report_email; returns the captured calls."""
    from phoenix_audit_agent.notifier import report_mail
    from phoenix_audit_agent.notifier.email import EmailSendResult

    calls: list[dict[str, Any]] = []

    async def fake(record: RunRecord, *, to: str) -> EmailSendResult:
        calls.append({"record": record, "to": to})
        return EmailSendResult(sent=True, to=to, attachment_included=True)

    monkeypatch.setattr(report_mail, "send_report_email", fake)
    return calls


async def _seed(**kw: Any) -> RunRecord:
    defaults: dict[str, Any] = {
        "target_url": "https://target.example",
        "created_at": "2026-06-11T10:00:00Z",
        "phase": "succeeded",
        "report_available": True,
        "owner_uid": "user-a",
    }
    defaults.update(kw)
    record = RunRecord(run_id=RUN_ID, **defaults)
    await run_storage.get_run_store().create(record)
    return record


# --- contract -------------------------------------------------------------------


async def test_email_report_success(
    client: httpx.AsyncClient, send_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 200, r.text
    assert r.json() == {"sent": True, "to": "a@example.com", "attachment_included": True}
    assert len(send_spy) == 1
    assert send_spy[0]["to"] == "a@example.com"
    assert send_spy[0]["record"].run_id == RUN_ID


async def test_sample_run_emailable_by_any_user(
    client: httpx.AsyncClient, send_spy: list[dict[str, Any]]
) -> None:
    """Ownerless sample runs are visible-to-all — emailing one to YOURSELF
    is the demo path a judge walks."""
    await _seed(owner_uid=None)
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 200, r.text
    assert send_spy[0]["to"] == "a@example.com"


async def test_foreign_run_reads_as_not_found(
    client: httpx.AsyncClient, send_spy: list[dict[str, Any]]
) -> None:
    await _seed(owner_uid="user-b")
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 404
    assert send_spy == []


async def test_missing_run_404(client: httpx.AsyncClient, send_spy: list[dict[str, Any]]) -> None:
    r = await client.post("/runs/run_nonexistent0/email")
    assert r.status_code == 404
    assert send_spy == []


async def test_report_not_available_409(
    client: httpx.AsyncClient, send_spy: list[dict[str, Any]]
) -> None:
    await _seed(report_available=False)
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 409
    assert send_spy == []


async def test_token_without_email_422(
    client: httpx.AsyncClient,
    send_spy: list[dict[str, Any]],
    auth_as: Callable[..., None],
) -> None:
    auth_as(uid="user-a", email=None)
    await _seed()
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 422
    assert send_spy == []


async def test_unconfigured_503(
    client: httpx.AsyncClient,
    send_spy: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RESEND_API_KEY")
    get_settings.cache_clear()
    await _seed()
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 503
    assert send_spy == []


async def test_send_failure_502_disclosed(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A contained Resend failure (sent=False result) surfaces as 502 with
    the error in the detail — the button must never pretend it sent."""
    from phoenix_audit_agent.notifier import report_mail
    from phoenix_audit_agent.notifier.email import EmailSendResult

    async def fake(record: RunRecord, *, to: str) -> EmailSendResult:
        return EmailSendResult(sent=False, to=to, error="RateLimitError: slow down")

    monkeypatch.setattr(report_mail, "send_report_email", fake)
    await _seed()
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 502
    assert "RateLimitError" in r.json()["detail"]


async def test_download_failure_502(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.notifier import report_mail

    async def fake(record: RunRecord, *, to: str) -> Any:
        raise RuntimeError("gcs unavailable")

    monkeypatch.setattr(report_mail, "send_report_email", fake)
    await _seed()
    r = await client.post(f"/runs/{RUN_ID}/email")
    assert r.status_code == 502
