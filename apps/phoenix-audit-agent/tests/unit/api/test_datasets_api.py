"""Story-9.15 — `/datasets` API routes.

GET (list) + GET (detail) + POST (upload) + DELETE — owner-scoped, auth-gated,
all backed by the in-memory `DatasetIndexStore` + the fake
`PhoenixDatasetClient`. The 422 body shape, 404-vs-403 leak rule, 409
read-only-kind contract, and 503 graceful-degrade path are all pinned here.
"""

from __future__ import annotations

import base64
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest

from phoenix_audit_agent.config import get_settings

from ..storage.fakes import FakePhoenixDatasetClient, InMemoryDatasetIndexStore


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


JSONL_OK = (
    '{"case_id": "pi-001", "fault_class": "prompt_injection",'
    ' "prompt": "ignore prior", "expected": "refuse", "source": "OWASP"}\n'
    '{"case_id": "pi-002", "fault_class": "context_poisoning",'
    ' "prompt": "context leak", "expected": "scope only", "source": "internal"}\n'
)


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


async def test_get_datasets_lists_battery_plus_owned(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    await _seed_index(index_store, slug="harmbench-v1-sample", kind="battery")
    await _seed_index(index_store, slug="ds_alice1", kind="uploaded", owner_uid="uid_alice")
    await _seed_index(index_store, slug="ds_bob1", kind="uploaded", owner_uid="uid_bob")

    r = await client.get("/datasets")
    assert r.status_code == 200
    rows = r.json()["datasets"]
    slugs = {row["dataset_id"] for row in rows}
    assert "harmbench-v1-sample" in slugs
    assert "ds_alice1" in slugs
    assert "ds_bob1" not in slugs
    # Phoenix-side ids must NOT leak on the listing wire.
    for row in rows:
        assert "phoenix_dataset_id" not in row


async def test_get_dataset_detail_returns_items(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    created = await phoenix_client.create(
        name="HarmBench v1 (sample)",
        examples=[
            {
                "case_id": "pi-001",
                "fault_class": "prompt_injection",
                "prompt": "p1",
                "expected": "e1",
                "source": "OWASP",
                "severity": "high",
                "notes": None,
            }
        ],
        description=None,
        source_url=None,
    )
    await _seed_index(
        index_store,
        slug="harmbench-v1-sample",
        kind="battery",
        phoenix_dataset_id=created.phoenix_dataset_id,
        row_count=1,
    )

    r = await client.get("/datasets/harmbench-v1-sample")
    assert r.status_code == 200
    body = r.json()
    assert body["dataset_id"] == "harmbench-v1-sample"
    assert body["kind"] == "battery"
    assert len(body["items"]) == 1
    assert body["items"][0]["case_id"] == "pi-001"


async def test_get_dataset_detail_forbidden_returns_404_not_403(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Foreign upload must surface as 404 — 403 would leak existence."""
    await _seed_index(index_store, slug="ds_bob_private", kind="uploaded", owner_uid="uid_bob")

    r = await client.get("/datasets/ds_bob_private")
    assert r.status_code == 404


async def test_get_dataset_detail_phoenix_outage_returns_503_with_index(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """BDD: '/datasets/<slug> for a Phoenix outage returns 503 with the index
    metadata in the body so the page can render the header.'"""
    created = await phoenix_client.create(
        name="x",
        examples=[
            {
                "case_id": "a",
                "fault_class": "prompt_injection",
                "prompt": "p",
                "expected": "e",
                "source": "s",
            }
        ],
        description=None,
        source_url=None,
    )
    await _seed_index(
        index_store,
        slug="harmbench-v1-sample",
        kind="battery",
        phoenix_dataset_id=created.phoenix_dataset_id,
        row_count=1,
    )
    phoenix_client.outage = True

    r = await client.get("/datasets/harmbench-v1-sample")
    assert r.status_code == 503
    body = r.json()
    assert body["dataset_id"] == "harmbench-v1-sample"
    assert body["kind"] == "battery"
    assert "items" not in body
    assert "reason" in body


async def test_post_uploads_creates_phoenix_dataset_and_index_row(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    r = await client.post(
        "/datasets",
        json={
            "name": "Meridian refusal corpus",
            "format": "jsonl",
            "body": _b64(JSONL_OK),
        },
    )
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["kind"] == "uploaded"
    assert body["row_count"] == 2
    assert body["dataset_id"].startswith("ds_")
    # The Phoenix-side row store actually carries the examples.
    items = await phoenix_client.get_examples(
        (await index_store.get_by_slug(body["dataset_id"])).phoenix_dataset_id
    )
    assert {i.case_id for i in items} == {"pi-001", "pi-002"}


async def test_post_uploads_row_error_returns_422_row_errors(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    bad = (
        '{"case_id": "x", "fault_class": "totally_fake",'
        ' "prompt": "p", "expected": "e", "source": "s"}\n'
    )
    r = await client.post("/datasets", json={"name": "x", "format": "jsonl", "body": _b64(bad)})
    assert r.status_code == 422
    body = r.json()
    assert body["parse_error"] is None
    assert len(body["row_errors"]) == 1
    assert body["row_errors"][0]["row"] == 1


async def test_post_uploads_parse_error_returns_422_parse_error(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    r = await client.post(
        "/datasets",
        json={"name": "x", "format": "jsonl", "body": _b64("not json at all\n")},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["parse_error"] is not None
    assert body["row_errors"] == []


async def test_delete_uploaded_returns_204_and_removes_index(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    await _seed_index(index_store, slug="ds_alice1", kind="uploaded", owner_uid="uid_alice")
    r = await client.delete("/datasets/ds_alice1")
    assert r.status_code == 204
    assert await index_store.get_by_slug("ds_alice1") is None


async def test_delete_battery_returns_409(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    await _seed_index(index_store, slug="harmbench-v1-sample", kind="battery")
    r = await client.delete("/datasets/harmbench-v1-sample")
    assert r.status_code == 409
    assert "battery" in r.json()["detail"]


async def test_delete_regression_returns_409(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    await _seed_index(
        index_store,
        slug="regression-alice-bot",
        kind="regression",
        owner_uid="uid_alice",
        agent_id="agt_a",
    )
    r = await client.delete("/datasets/regression-alice-bot")
    assert r.status_code == 409
    assert "regression" in r.json()["detail"]


async def test_delete_foreign_returns_404_not_403(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    await _seed_index(index_store, slug="ds_bob1", kind="uploaded", owner_uid="uid_bob")
    r = await client.delete("/datasets/ds_bob1")
    # 404 — not 403 — so existence doesn't leak.
    assert r.status_code == 404
