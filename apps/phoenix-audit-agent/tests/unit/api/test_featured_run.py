"""GET /featured-run — the public sample-replay source (story-9.11).

The landing page's /replay showcase plays a REAL seeded audit. This endpoint
is deliberately unauthenticated and returns ONLY ownerless sample runs
(owner_uid is None) that finished with a persisted replay timeline —
an owned run must never leak through it.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import RunRecord

from ..storage.fakes import InMemoryRunStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _signing(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.api import runs as runs_api

    async def fake_sign(blob_name: str) -> str:
        return f"https://storage.googleapis.com/signed/{blob_name}"

    monkeypatch.setattr(runs_api, "sign_blob_url", fake_sign)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _record(run_id: str, *, created_at: str, **kw: Any) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        target_url="https://target.example",
        created_at=created_at,
        **kw,
    )


async def test_featured_run_is_newest_ownerless_replayable(client: httpx.AsyncClient) -> None:
    store = run_storage.get_run_store()
    # Owned + replayable — must NEVER surface on the public endpoint.
    await store.create(
        _record(
            "run_owneduser111",
            created_at="2026-06-10T09:00:00Z",
            phase="succeeded",
            events_available=True,
            owner_uid="user-someone",
        )
    )
    # Ownerless but no replay timeline — nothing to play.
    await store.create(
        _record(
            "run_noevents1111",
            created_at="2026-06-10T08:00:00Z",
            phase="succeeded",
        )
    )
    # Ownerless, still running — not finished, not featured.
    await store.create(
        _record("run_running11111", created_at="2026-06-10T07:30:00Z", phase="judge")
    )
    # Two ownerless replayable sample runs — newest wins.
    await store.create(
        _record(
            "run_sampleolder1",
            created_at="2026-06-10T05:00:00Z",
            phase="succeeded",
            events_available=True,
            report_available=True,
        )
    )
    await store.create(
        _record(
            "run_samplenewer1",
            created_at="2026-06-10T06:00:00Z",
            phase="succeeded",
            events_available=True,
            report_available=True,
        )
    )

    r = await client.get("/featured-run")  # NO auth header — public by design
    assert r.status_code == 200
    body = r.json()
    assert body["run"]["run_id"] == "run_samplenewer1"
    assert body["run"]["owner_uid"] is None
    assert body["artifact_urls"]["events.json"].endswith("reports/run_samplenewer1/events.json")
    assert body["artifact_urls"]["report.pdf"].endswith("reports/run_samplenewer1/report.pdf")


async def test_featured_run_404_when_no_sample_exists(client: httpx.AsyncClient) -> None:
    store = run_storage.get_run_store()
    # Only an OWNED replayable run exists — public endpoint must 404, not leak.
    await store.create(
        _record(
            "run_owneduser222",
            created_at="2026-06-10T09:00:00Z",
            phase="succeeded",
            events_available=True,
            owner_uid="user-someone",
        )
    )

    r = await client.get("/featured-run")
    assert r.status_code == 404
