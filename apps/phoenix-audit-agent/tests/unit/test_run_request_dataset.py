"""Story-9.15 — `RunRequest.dataset_id` field + launch-time visibility.

Slice 5. Tests that lock the wire contract (`RunRequest.dataset_id` is an
optional slug) and the launch-time visibility check (`POST /run` against a
foreign dataset 422s with the BDD-mandated reason — never 403, never silent).

These tests do NOT exercise the full `drive_audit` pipeline — that's the
audit-runner integration coverage in the next slice. They pin just the
request shape + the rejection.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings

from .storage.fakes import FakePhoenixDatasetClient, InMemoryDatasetIndexStore


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(
            ("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_", "FIREBASE_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def index_store(_env: None) -> Iterator[InMemoryDatasetIndexStore]:
    from phoenix_audit_agent.storage import datasets as dataset_storage

    store = InMemoryDatasetIndexStore()
    dataset_storage.set_dataset_index_store(store)
    yield store
    dataset_storage.set_dataset_index_store(None)


@pytest.fixture
def phoenix_client(_env: None) -> Iterator[FakePhoenixDatasetClient]:
    from phoenix_audit_agent.api import datasets as datasets_api

    client = FakePhoenixDatasetClient()
    datasets_api.set_phoenix_client(client)
    yield client
    datasets_api.set_phoenix_client(None)


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as) -> None:
    auth_as("uid_alice", email="alice@example.com")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_index(store: InMemoryDatasetIndexStore, *, slug: str, kind: str, **kwargs: Any):
    from phoenix_audit_agent.storage.models import DatasetIndex

    await store.upsert(
        DatasetIndex(
            dataset_id=slug,
            phoenix_dataset_id=kwargs.get("phoenix_dataset_id", f"phx_ds_{slug}"),
            name=kwargs.get("name", slug),
            kind=kind,  # ty: ignore[invalid-argument-type]
            owner_uid=kwargs.get("owner_uid"),
            agent_id=kwargs.get("agent_id"),
            row_count=kwargs.get("row_count", 0),
            source_url=kwargs.get("source_url"),
            content_hash=kwargs.get("content_hash", "sha256:test"),
            created_at="2026-06-11T07:00:00+00:00",
            updated_at="2026-06-11T07:00:00+00:00",
        )
    )


def test_run_request_accepts_optional_dataset_id() -> None:
    """The wire contract: dataset_id is an optional slug. Default is None
    (a no-dataset audit runs the synthetic battery only)."""
    from phoenix_audit_agent.main import RunRequest

    r1 = RunRequest(target_url="https://target.example")
    assert r1.dataset_id is None

    r2 = RunRequest(target_url="https://target.example", dataset_id="harmbench-v1-sample")
    assert r2.dataset_id == "harmbench-v1-sample"


def test_run_request_rejects_invalid_dataset_slug() -> None:
    """The slug pattern matches `DatasetIndex.dataset_id` so a malformed
    slug 422s at the request boundary, not later."""
    from pydantic import ValidationError

    from phoenix_audit_agent.main import RunRequest

    with pytest.raises(ValidationError, match="dataset_id"):
        RunRequest(target_url="https://target.example", dataset_id="Has Spaces and CAPS")


async def test_post_run_with_visible_dataset_launches(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: Alice runs against a battery dataset → 202."""
    from phoenix_audit_agent import main as main_module

    await _seed_index(index_store, slug="harmbench-v1-sample", kind="battery")

    # Replace the orchestrator so the test doesn't actually drive the audit —
    # we're testing the launch contract, not the pipeline.
    launched: list[str] = []

    async def fake_orchestrator(run_id: str) -> None:
        launched.append(run_id)

    monkeypatch.setattr(main_module, "_drive_orchestrator", fake_orchestrator)

    r = await client.post(
        "/run",
        json={
            "target_url": "https://target.example",
            "dataset_id": "harmbench-v1-sample",
        },
    )
    assert r.status_code == 201, r.json()


async def test_post_run_with_foreign_dataset_422_never_403(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Bob owns the dataset; Alice tries to use it → 422 with the reason
    BDD-mandates. Never 403 (existence leak)."""
    await _seed_index(index_store, slug="ds_bob_private", kind="uploaded", owner_uid="uid_bob")

    r = await client.post(
        "/run",
        json={
            "target_url": "https://target.example",
            "dataset_id": "ds_bob_private",
        },
    )
    assert r.status_code == 422
    body = r.json()
    # Surface the exact BDD reason — the wire contract.
    assert "not found or not accessible" in str(body).lower()


async def test_post_run_with_missing_dataset_422(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Dataset doesn't exist at all → same 422 reason. Indistinguishable
    from 'exists but you can't see it' (existence-leak rule)."""
    r = await client.post(
        "/run",
        json={
            "target_url": "https://target.example",
            "dataset_id": "never-existed-9999",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert "not found or not accessible" in str(body).lower()


async def test_post_run_without_dataset_still_launches(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward compatibility: omitting dataset_id keeps the synthetic-battery
    behavior we already shipped. No regression."""
    from phoenix_audit_agent import main as main_module

    async def fake_orchestrator(run_id: str) -> None:
        return None

    monkeypatch.setattr(main_module, "_drive_orchestrator", fake_orchestrator)

    r = await client.post("/run", json={"target_url": "https://target.example"})
    assert r.status_code == 201
