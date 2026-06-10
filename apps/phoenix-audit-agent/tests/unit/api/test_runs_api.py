"""GET /runs + GET /runs/{id} — the audit-registry read API (story-9.1)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import agents as agent_storage
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import RunRecord

from ..storage.fakes import InMemoryAgentStore, InMemoryRunStore


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
    agent_storage.set_agent_store(InMemoryAgentStore())
    yield
    run_storage.set_run_store(None)
    agent_storage.set_agent_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(
    _env: None, auth_as
) -> None:  # _env first: settings env must exist before auth_as imports main
    """This module's subject is the registry read API, not auth — requests
    arrive pre-authenticated as `user-test` (auth wiring: test_auth_scoping)."""


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


async def test_list_runs_discloses_truncation(client: httpx.AsyncClient) -> None:
    """The store's truncation flag must pass through to the API response —
    silent truncation reads as 'covered everything' when it didn't."""
    store = run_storage.get_run_store()
    original_list_runs = store.list_runs

    async def truncated_list_runs(**kwargs: Any) -> tuple[list[RunRecord], bool]:
        rows, _ = await original_list_runs(**kwargs)
        return rows, True

    store.list_runs = truncated_list_runs  # ty: ignore[invalid-assignment]
    r = await client.get("/runs")
    assert r.status_code == 200
    assert r.json()["truncated"] is True


async def test_list_runs_empty(client: httpx.AsyncClient) -> None:
    r = await client.get("/runs")
    assert r.status_code == 200
    assert r.json() == {"runs": [], "truncated": False}


async def test_list_runs_newest_first_with_fields(client: httpx.AsyncClient) -> None:
    store = run_storage.get_run_store()
    await store.create(_record("run_111111111111", created_at="2026-06-10T01:00:00Z"))
    await store.create(
        _record(
            "run_222222222222",
            created_at="2026-06-10T02:00:00Z",
            source="scheduled",
            phase="succeeded",
            passed=6,
            failed=0,
        )
    )

    r = await client.get("/runs")
    rows = r.json()["runs"]
    assert [x["run_id"] for x in rows] == ["run_222222222222", "run_111111111111"]
    top = rows[0]
    assert top["source"] == "scheduled"
    assert top["passed"] == 6
    assert top["phase"] == "succeeded"
    assert top["target_url"] == "https://target.example"


async def test_list_runs_filters(client: httpx.AsyncClient) -> None:
    store = run_storage.get_run_store()
    await store.create(_record("run_111111111111", created_at="2026-06-10T01:00:00Z"))
    await store.create(
        _record("run_222222222222", created_at="2026-06-10T02:00:00Z", source="scheduled")
    )

    r = await client.get("/runs?source=scheduled")
    assert [x["run_id"] for x in r.json()["runs"]] == ["run_222222222222"]


async def test_get_run_unknown_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/runs/run_doesnotexist")
    assert r.status_code == 404


async def test_get_run_resigns_artifact_urls(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stored URLs would expire — the detail endpoint signs FRESH urls from
    the deterministic object paths, only for artifacts that exist."""
    from phoenix_audit_agent.api import runs as runs_api

    signed: list[str] = []

    async def fake_sign(blob_name: str) -> str:
        signed.append(blob_name)
        return f"https://storage.googleapis.com/signed/{blob_name}"

    monkeypatch.setattr(runs_api, "sign_blob_url", fake_sign)

    store = run_storage.get_run_store()
    await store.create(
        _record(
            "run_333333333333",
            created_at="2026-06-10T03:00:00Z",
            phase="succeeded",
            report_available=True,
            recipe_id="recipe_deadbeefcafe",
        )
    )

    r = await client.get("/runs/run_333333333333")
    body = r.json()
    assert body["run"]["run_id"] == "run_333333333333"
    urls = body["artifact_urls"]
    assert urls["report.pdf"].endswith("reports/run_333333333333/report.pdf")
    assert urls["signature.json"].endswith("reports/run_333333333333/signature.json")
    assert urls["recipe.md"].endswith("recipe_deadbeefcafe.md")
    assert "reports/run_333333333333/report.json" in str(urls["report.json"])


async def test_get_run_without_artifacts_has_no_urls(client: httpx.AsyncClient) -> None:
    store = run_storage.get_run_store()
    await store.create(_record("run_444444444444", created_at="2026-06-10T04:00:00Z"))

    r = await client.get("/runs/run_444444444444")
    assert r.json()["artifact_urls"] == {}
    assert r.json()["artifact_url_errors"] == {}


async def test_sign_failure_disclosed_distinct_from_absent(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A signing outage must be DISTINGUISHABLE from 'artifact does not exist'
    — never a silently absent key (CLAUDE.md pattern #4)."""
    from phoenix_audit_agent.api import runs as runs_api

    async def failing_sign(blob_name: str) -> str:
        if blob_name.endswith("recipe_deadbeefcafe.md"):
            raise RuntimeError("sign outage")
        return f"https://storage.googleapis.com/signed/{blob_name}"

    monkeypatch.setattr(runs_api, "sign_blob_url", failing_sign)

    store = run_storage.get_run_store()
    await store.create(
        _record(
            "run_555555555555",
            created_at="2026-06-10T05:00:00Z",
            report_available=True,
            recipe_id="recipe_deadbeefcafe",
        )
    )

    r = await client.get("/runs/run_555555555555")
    body = r.json()
    assert "report.pdf" in body["artifact_urls"]
    assert "recipe.md" not in body["artifact_urls"]
    assert body["artifact_url_errors"] == {"recipe.md": "RuntimeError"}


async def test_completion_with_unknown_field_is_rejected() -> None:
    """extra='ignore' on read would silently drop a typo'd finalize key —
    RunCompletion (extra='forbid') makes the typo a constructor error
    (containment turns it into a DISCLOSED persistence_failed)."""
    from pydantic import ValidationError

    from phoenix_audit_agent.storage.models import RunCompletion

    payload: dict[str, Any] = {
        "run_id": "run_666666666666",
        "target_url": "https://target.example",
        "created_at": "2026-06-10T01:00:00Z",
        "phase": "succeeded",
        "report_avaliable": True,  # the typo IS the test
    }
    with pytest.raises(ValidationError, match="report_avaliable"):
        RunCompletion(**payload)


async def test_list_runs_rejects_nonpositive_limit(client: httpx.AsyncClient) -> None:
    """limit=-5 would slice rows[:-5] and silently drop the NEWEST runs."""
    r = await client.get("/runs?limit=-5")
    assert r.status_code == 422
    r = await client.get("/runs?limit=0")
    assert r.status_code == 422
