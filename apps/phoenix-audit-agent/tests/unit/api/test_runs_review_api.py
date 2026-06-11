"""POST /runs/{run_id}/clusters/{cluster_id}/review — the officer review
layer (story-9.21). The review persists on the run record FIRST; the Phoenix
human annotation is contained and its outcome disclosed, never assumed.
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
CLUSTER = "cl_01"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "GITLAB_", "RESEND_", "FIREBASE_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _authed(_env: None, auth_as: Callable[..., None]) -> Callable[..., None]:
    auth_as(uid="user-a", email="officer@corp.example")
    return auth_as


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def annotation_spy(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace the contained Phoenix human-annotation seam; capture calls."""
    from phoenix_audit_agent.api import runs_review

    calls: list[dict[str, Any]] = []

    async def fake(*, span_id: str, verdict: str, note: str | None, cluster_id: str) -> bool:
        calls.append(
            {"span_id": span_id, "verdict": verdict, "note": note, "cluster_id": cluster_id}
        )
        return True

    monkeypatch.setattr(runs_review, "annotate_officer_verdict", fake)
    return calls


async def _seed(**kw: Any) -> RunRecord:
    defaults: dict[str, Any] = {
        "target_url": "https://target.example",
        "created_at": "2026-06-11T10:00:00Z",
        "phase": "succeeded",
        "recipe_id": "recipe_abc123def456",
        "owner_uid": "user-a",
        "cluster_spans": {CLUSTER: "a1b2c3d4e5f60708"},
    }
    defaults.update(kw)
    record = RunRecord(run_id=RUN_ID, **defaults)
    await run_storage.get_run_store().create(record)
    return record


def _post(client: httpx.AsyncClient, **body: Any) -> Any:
    payload = {"verdict": "confirmed", **body}
    return client.post(f"/runs/{RUN_ID}/clusters/{CLUSTER}/review", json=payload)


async def test_review_persists_and_annotates(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    r = await _post(client, note="verified against the trace")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["phoenix_annotated"] is True
    review = body["review"]
    assert review["verdict"] == "confirmed"
    assert review["note"] == "verified against the trace"
    assert review["reviewer_email"] == "officer@corp.example"
    assert review["reviewed_at"]

    record = await run_storage.get_run_store().get(RUN_ID)
    assert record is not None
    assert record.cluster_reviews[CLUSTER].verdict == "confirmed"
    assert annotation_spy == [
        {
            "span_id": "a1b2c3d4e5f60708",
            "verdict": "confirmed",
            "note": "verified against the trace",
            "cluster_id": CLUSTER,
        }
    ]


async def test_review_visible_on_run_detail(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    await _post(client)
    r = await client.get(f"/runs/{RUN_ID}")
    assert r.status_code == 200
    assert r.json()["run"]["cluster_reviews"][CLUSTER]["verdict"] == "confirmed"


async def test_re_review_last_write_wins(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    await _post(client)
    r = await _post(client, verdict="disputed", note="second look")
    assert r.status_code == 200
    record = await run_storage.get_run_store().get(RUN_ID)
    assert record is not None
    assert record.cluster_reviews[CLUSTER].verdict == "disputed"
    assert record.cluster_reviews[CLUSTER].note == "second look"


async def test_phoenix_outage_persists_review_and_discloses(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.api import runs_review

    async def down(*, span_id: str, verdict: str, note: str | None, cluster_id: str) -> bool:
        return False

    monkeypatch.setattr(runs_review, "annotate_officer_verdict", down)
    await _seed()
    r = await _post(client)
    assert r.status_code == 200
    assert r.json()["phoenix_annotated"] is False
    record = await run_storage.get_run_store().get(RUN_ID)
    assert record is not None
    assert CLUSTER in record.cluster_reviews  # the review survived the outage


async def test_unknown_cluster_422(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    r = await client.post(
        f"/runs/{RUN_ID}/clusters/cl_unknown/review", json={"verdict": "confirmed"}
    )
    assert r.status_code == 422
    assert annotation_spy == []


async def test_sample_run_not_reviewable_422(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed(owner_uid=None)
    r = await _post(client)
    assert r.status_code == 422
    assert annotation_spy == []


async def test_foreign_run_404(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed(owner_uid="user-b")
    r = await _post(client)
    assert r.status_code == 404
    assert annotation_spy == []


async def test_invalid_verdict_422(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    r = await _post(client, verdict="maybe")
    assert r.status_code == 422
    assert annotation_spy == []


async def test_note_length_capped(
    client: httpx.AsyncClient, annotation_spy: list[dict[str, Any]]
) -> None:
    await _seed()
    r = await _post(client, note="x" * 501)
    assert r.status_code == 422
    assert annotation_spy == []


# --- deep-link fields on RunDetailResponse ---------------------------------------


async def test_run_detail_carries_phoenix_ui_fields(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PHOENIX_UI_BASE", "https://app.phoenix.arize.com/s/space")
    monkeypatch.setenv("TARGET_PHOENIX_PROJECT", "phoenix-audit")
    get_settings.cache_clear()
    await _seed()
    r = await client.get(f"/runs/{RUN_ID}")
    body = r.json()
    assert body["phoenix_ui_base"] == "https://app.phoenix.arize.com/s/space"
    assert body["phoenix_project"] == "phoenix-audit"


async def test_run_detail_phoenix_fields_null_when_unconfigured(
    client: httpx.AsyncClient,
) -> None:
    await _seed()
    r = await client.get(f"/runs/{RUN_ID}")
    body = r.json()
    assert body["phoenix_ui_base"] is None
    assert body["phoenix_project"] is None
