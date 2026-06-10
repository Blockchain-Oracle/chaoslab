"""persist_run_events — the replay timeline artifact (story-9.11).

Uploads the recorded SSE frame list as reports/{run_id}/events.json so any
finished run can be replayed from wire truth. Containment contract: a GCS
outage returns False (logged), never raises into the audit pipeline.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, cast

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.patcher.markdown_emitter import StorageClient
from phoenix_audit_agent.reporter.emitter import ReportEmitter
from phoenix_audit_agent.reporter.events import persist_run_events


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeBlob:
    def __init__(self, name: str, uploads: list[dict[str, Any]]) -> None:
        self._name = name
        self._uploads = uploads

    def upload_from_string(
        self,
        payload: bytes,
        content_type: str,
        if_generation_match: int | None = None,
    ) -> None:
        self._uploads.append(
            {
                "blob": self._name,
                "payload": payload,
                "content_type": content_type,
                "if_generation_match": if_generation_match,
            }
        )

    def generate_signed_url(self, **_: Any) -> str:
        return f"https://signed.example/{self._name}"


class _FakeBucket:
    def __init__(self, uploads: list[dict[str, Any]]) -> None:
        self._uploads = uploads

    def blob(self, name: str) -> _FakeBlob:
        return _FakeBlob(name, self._uploads)


class _FakeClient:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    def bucket(self, name: str) -> _FakeBucket:
        return _FakeBucket(self.uploads)


class _DownClient:
    def bucket(self, name: str) -> Any:
        raise RuntimeError("gcs unreachable")


_FRAMES = [
    {"t": 0.0, "event": "phase_change", "data": {"phase": "injector", "run_id": "run_eventcase12"}},
    {"t": 1.5, "event": "test_started", "data": {"n": 1, "run_id": "run_eventcase12"}},
    {"t": 9.0, "event": "complete", "data": {"phase": "succeeded", "run_id": "run_eventcase12"}},
]


@pytest.mark.asyncio
async def test_persist_run_events_uploads_timeline_document() -> None:
    client = _FakeClient()
    emitter = ReportEmitter(storage_client=cast(StorageClient, client))

    ok = await persist_run_events(
        "run_eventcase12", _FRAMES, created_at="2026-06-10T00:00:00Z", emitter=emitter
    )

    assert ok is True
    (upload,) = client.uploads
    assert upload["blob"] == "reports/run_eventcase12/events.json"
    assert upload["content_type"] == "application/json"
    # create-only: replays must never silently rewrite an audit's history
    assert upload["if_generation_match"] == 0
    doc = json.loads(upload["payload"])
    assert doc["run_id"] == "run_eventcase12"
    assert doc["created_at"] == "2026-06-10T00:00:00Z"
    assert doc["duration_sec"] == 9.0
    assert doc["frames"] == _FRAMES


@pytest.mark.asyncio
async def test_persist_run_events_outage_returns_false_never_raises() -> None:
    emitter = ReportEmitter(storage_client=cast(StorageClient, _DownClient()))

    ok = await persist_run_events(
        "run_eventcase12", _FRAMES, created_at="2026-06-10T00:00:00Z", emitter=emitter
    )

    assert ok is False


@pytest.mark.asyncio
async def test_persist_run_events_empty_frames_skips_upload() -> None:
    """Zero frames means there is nothing to replay — uploading an empty
    timeline would light the replay affordance on a run with no content."""
    client = _FakeClient()
    emitter = ReportEmitter(storage_client=cast(StorageClient, client))

    ok = await persist_run_events(
        "run_eventcase12", [], created_at="2026-06-10T00:00:00Z", emitter=emitter
    )

    assert ok is False
    assert client.uploads == []
