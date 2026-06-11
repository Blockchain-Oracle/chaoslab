"""POST /runs/{run_id}/gitlab-mr — review-first MR filing (story-9.17 slice 3).

The emitter mechanics live behind module seams (`download_recipe`,
`emit_recipe_mr`); this module pins the HTTP contract: ownership, sample
exclusion, connection gating, idempotency, persistence disclosure.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage import profiles as profile_storage
from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import RunRecord

from ..storage.fakes import InMemoryProfileStore, InMemoryRunStore

RUN_ID = "run_abc123def456"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "GITLAB_", "RESEND_", "PUBLIC_", "FIREBASE_", "GCS_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    profile_storage.set_profile_store(InMemoryProfileStore())
    yield
    run_storage.set_run_store(None)
    profile_storage.set_profile_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Callable[..., None]) -> None:
    auth_as(uid="user-a", email="a@example.com")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def connected(monkeypatch: pytest.MonkeyPatch) -> None:
    from phoenix_audit_agent.api import runs_mr

    async def fake_token(uid: str) -> str:
        assert uid == "user-a"
        return "glat-user"

    monkeypatch.setattr(runs_mr.gitlab_oauth, "get_valid_access_token", fake_token)


@pytest.fixture
def recipe_available(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from phoenix_audit_agent.api import runs_mr

    calls: dict[str, Any] = {}

    async def fake_download(recipe_id: str) -> object:
        calls["downloaded"] = recipe_id
        return object()  # opaque recipe sentinel — the emitter seam receives it

    async def fake_emit(recipe: object, *, project_id: str, oauth_token: str) -> str:
        calls["emit"] = {"recipe": recipe, "project_id": project_id, "oauth_token": oauth_token}
        return "https://gitlab.com/abu/agents/-/merge_requests/7"

    monkeypatch.setattr(runs_mr, "download_recipe", fake_download)
    monkeypatch.setattr(runs_mr, "emit_recipe_mr", fake_emit)
    return calls


async def _seed(**kw: Any) -> RunRecord:
    defaults: dict[str, Any] = {
        "target_url": "https://target.example",
        "created_at": "2026-06-11T10:00:00Z",
        "phase": "succeeded",
        "recipe_id": "recipe_abc123def456",
        "owner_uid": "user-a",
    }
    defaults.update(kw)
    record = RunRecord(run_id=RUN_ID, **defaults)
    await run_storage.get_run_store().create(record)
    return record


async def _post(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(f"/runs/{RUN_ID}/gitlab-mr", json={"project_id": 7})


async def test_files_mr_with_user_token_and_persists_url(
    client: httpx.AsyncClient, connected: None, recipe_available: dict[str, Any]
) -> None:
    await _seed()
    r = await _post(client)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "mr_url": "https://gitlab.com/abu/agents/-/merge_requests/7",
        "persisted": True,
    }
    assert recipe_available["downloaded"] == "recipe_abc123def456"
    assert recipe_available["emit"]["project_id"] == "7"
    assert recipe_available["emit"]["oauth_token"] == "glat-user"
    record = await run_storage.get_run_store().get(RUN_ID)
    assert record is not None
    assert record.mr_url == "https://gitlab.com/abu/agents/-/merge_requests/7"


async def test_foreign_run_404(
    client: httpx.AsyncClient, connected: None, recipe_available: dict[str, Any]
) -> None:
    await _seed(owner_uid="user-b")
    r = await _post(client)
    assert r.status_code == 404
    assert "emit" not in recipe_available


async def test_sample_run_not_filable_422(
    client: httpx.AsyncClient, connected: None, recipe_available: dict[str, Any]
) -> None:
    """A judge exploring shared specimens must not file MRs from them."""
    await _seed(owner_uid=None)
    r = await _post(client)
    assert r.status_code == 422
    assert "emit" not in recipe_available


async def test_not_connected_409(
    client: httpx.AsyncClient, recipe_available: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import runs_mr
    from phoenix_audit_agent.integrations.gitlab_oauth import NotConnectedError

    async def fake_token(uid: str) -> str:
        raise NotConnectedError("no GitLab connection — connect in settings")

    monkeypatch.setattr(runs_mr.gitlab_oauth, "get_valid_access_token", fake_token)
    await _seed()
    r = await _post(client)
    assert r.status_code == 409
    assert "connect" in r.json()["detail"].lower()


async def test_no_recipe_409(
    client: httpx.AsyncClient, connected: None, recipe_available: dict[str, Any]
) -> None:
    await _seed(recipe_id=None)
    r = await _post(client)
    assert r.status_code == 409


async def test_already_filed_409_with_existing_url(
    client: httpx.AsyncClient, connected: None, recipe_available: dict[str, Any]
) -> None:
    """Idempotency: never a duplicate MR; the existing URL rides the detail."""
    await _seed(mr_url="https://gitlab.com/abu/agents/-/merge_requests/3")
    r = await _post(client)
    assert r.status_code == 409
    assert "merge_requests/3" in r.json()["detail"]
    assert "emit" not in recipe_available


async def test_recipe_artifact_unavailable_409(
    client: httpx.AsyncClient, connected: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-9.17 runs have no {recipe_id}.json sidecar — honest 409, not a 500."""
    from phoenix_audit_agent.api import runs_mr

    async def fake_download(recipe_id: str) -> object | None:
        return None

    monkeypatch.setattr(runs_mr, "download_recipe", fake_download)
    await _seed()
    r = await _post(client)
    assert r.status_code == 409
    assert "artifact" in r.json()["detail"]


async def test_emitter_failure_502_nothing_persisted(
    client: httpx.AsyncClient, connected: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import runs_mr
    from phoenix_audit_agent.patcher.gitlab_emitter import GitLabEmitterError

    async def fake_download(recipe_id: str) -> object:
        return object()

    async def fake_emit(recipe: object, *, project_id: str, oauth_token: str) -> str:
        raise GitLabEmitterError("GitLab MR creation failed (branch=x): boom")

    monkeypatch.setattr(runs_mr, "download_recipe", fake_download)
    monkeypatch.setattr(runs_mr, "emit_recipe_mr", fake_emit)
    await _seed()
    r = await _post(client)
    assert r.status_code == 502
    record = await run_storage.get_run_store().get(RUN_ID)
    assert record is not None
    assert record.mr_url is None
