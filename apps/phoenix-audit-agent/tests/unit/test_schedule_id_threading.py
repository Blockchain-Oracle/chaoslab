"""schedule_id threading: tick → RunRequest → RunRecord (story-9.5).

The scheduled-summary hook resolves `deliver_email` from the persisted
record's `schedule_id` — these tests pin the thread end-to-end at the
launch boundary.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import ScheduleRecord

from .storage.fakes import InMemoryRunStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_", "RESEND_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Callable[..., None]) -> None:
    """Launch endpoints require a user; auth wiring is test_auth_scoping's subject."""


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def test_run_request_schedule_id_defaults_none() -> None:
    from phoenix_audit_agent.main import RunRequest

    payload = RunRequest(target_url="http://localhost:8001")
    assert payload.schedule_id is None
    linked = RunRequest(target_url="http://localhost:8001", schedule_id="sch_1")
    assert linked.schedule_id == "sch_1"


async def test_tick_launch_persists_schedule_id() -> None:
    from phoenix_audit_agent.main import _launch_scheduled_run

    schedule = ScheduleRecord(
        schedule_id="sch_threaded",
        target_url="https://t.example",
        owner_uid="user-a",
        next_fire_at="2026-06-11T00:00:00+00:00",
        created_at="2026-06-11T00:00:00+00:00",
    )
    run_id = await _launch_scheduled_run(schedule)
    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.schedule_id == "sch_threaded"
    assert record.source == "scheduled"


async def test_manual_run_persists_schedule_id_none(client: httpx.AsyncClient) -> None:
    r = await client.post("/run", json={"target_url": "http://localhost:8001"})
    assert r.status_code == 201, r.text
    record = await run_storage.get_run_store().get(r.json()["run_id"])
    assert record is not None
    assert record.schedule_id is None


async def test_manual_run_rejects_client_supplied_schedule_id(
    client: httpx.AsyncClient,
) -> None:
    """POST /run must not let a caller claim a schedule linkage it doesn't
    have — a forged schedule_id would sit on regulator-visible records."""
    r = await client.post(
        "/run", json={"target_url": "http://localhost:8001", "schedule_id": "sch_forged"}
    )
    assert r.status_code == 422
