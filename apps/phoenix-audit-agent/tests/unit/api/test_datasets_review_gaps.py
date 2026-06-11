"""Story-9.15 — coverage gaps surfaced by the test-analyzer review.

Pinning:
- CSV upload happy path at the route level (only JSONL was tested).
- 422 uploads do NOT create the Phoenix-side dataset (side-effect leak).
- Regression upsert respects the 200-row cap.
- `UploadValidationError` raises if both partition fields are set (L1).
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


CSV_OK = (
    "case_id,fault_class,prompt,expected,source,severity,notes\n"
    "pi-001,prompt_injection,ignore prior,refuse,OWASP,high,\n"
    "pi-002,context_poisoning,leak,scope,internal,medium,extra note\n"
)


async def test_post_uploads_csv_happy_path_at_route_level(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """The route's CSV format wiring is exercised end-to-end."""
    r = await client.post(
        "/datasets",
        json={"name": "Operator CSV", "format": "csv", "body": _b64(CSV_OK)},
    )
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["kind"] == "uploaded"
    assert body["row_count"] == 2
    # And the Phoenix-side dataset actually has the rows.
    idx = await index_store.get_by_slug(body["dataset_id"])
    items = await phoenix_client.get_examples(idx.phoenix_dataset_id)
    assert {i.case_id for i in items} == {"pi-001", "pi-002"}


async def test_422_row_error_leaves_no_phoenix_side_effect(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """BDD: 'The Phoenix-side dataset is NOT created on validation failure.'"""
    bad = (
        '{"case_id": "x", "fault_class": "totally_fake",'
        ' "prompt": "p", "expected": "e", "source": "s"}\n'
    )
    r = await client.post("/datasets", json={"name": "x", "format": "jsonl", "body": _b64(bad)})
    assert r.status_code == 422
    # No Phoenix-side write happened.
    assert phoenix_client._datasets == {}
    # And no index row landed either.
    visible = await index_store.list_visible("uid_alice")
    assert visible == []


async def test_422_parse_error_leaves_no_phoenix_side_effect(
    client: httpx.AsyncClient,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    r = await client.post(
        "/datasets", json={"name": "x", "format": "jsonl", "body": _b64("not json\n")}
    )
    assert r.status_code == 422
    assert phoenix_client._datasets == {}


def test_upload_validation_error_post_init_raises_on_both_fields_set() -> None:
    """L1: setting both `parse_error` and `row_errors` raises at construction."""
    from phoenix_audit_agent.api.datasets_validation import RowError, UploadValidationError

    with pytest.raises(ValueError, match="mutually exclusive"):
        UploadValidationError(
            parse_error="something",
            row_errors=[RowError(row=1, reason="duplicate")],
        )


@pytest.mark.asyncio
async def test_regression_upsert_caps_at_200_rows() -> None:
    """The dedup-and-cap path keeps at most REGRESSION_CAP rows."""
    from phoenix_audit_agent import audit_runner_datasets as ard

    fake_phx = FakePhoenixDatasetClient()

    class _Idx:
        def __init__(self) -> None:
            self._rows: dict[str, Any] = {}

        async def get_by_slug(self, slug: str):
            return self._rows.get(slug)

        async def upsert(self, idx: Any) -> None:
            self._rows[idx.dataset_id] = idx

    # 250 distinct case_ids on the first failure → capped at 200.
    rows = [
        {
            "case_id": f"r{i:04d}",
            "prompt": "p",
            "fault_class": "prompt_injection",
            "expected": "e",
            "source": "x",
        }
        for i in range(250)
    ]
    snap = await ard.upsert_regression_set(
        agent_id="agt_x",
        owner_uid="uid_alice",
        failing_rows=rows,
        phoenix=fake_phx,
        idx_store=_Idx(),
        now="2026-06-11T08:00:00+00:00",
    )
    assert snap.row_count == ard.REGRESSION_CAP
    items = await fake_phx.get_examples(snap.phoenix_dataset_id)
    assert len(items) == ard.REGRESSION_CAP


@pytest.mark.asyncio
async def test_regression_upsert_missing_case_id_raises_value_error() -> None:
    """I1 (review-fleet): a row missing `case_id` raises a typed ValueError
    at the boundary instead of KeyError deep inside asyncio.gather."""
    from phoenix_audit_agent import audit_runner_datasets as ard

    fake_phx = FakePhoenixDatasetClient()

    class _Idx:
        async def get_by_slug(self, slug: str):
            return None

        async def upsert(self, idx: Any) -> None:
            return None

    bad = [
        {
            "prompt": "p",
            "fault_class": "prompt_injection",
            "expected": "e",
            "source": "x",
        }
    ]
    with pytest.raises(ValueError, match="case_id"):
        await ard.upsert_regression_set(
            agent_id="agt_x",
            owner_uid="uid_alice",
            failing_rows=bad,
            phoenix=fake_phx,
            idx_store=_Idx(),
            now="2026-06-11T08:00:00+00:00",
        )
