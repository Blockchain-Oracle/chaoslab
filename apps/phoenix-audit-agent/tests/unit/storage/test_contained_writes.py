"""Contained-write helpers — outage bounding + disclosure semantics."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from phoenix_audit_agent.storage import runs as run_storage
from phoenix_audit_agent.storage.models import RunCompletion, RunRecord


class _HangingStore:
    """Store whose writes never return — simulates a Firestore outage."""

    async def create(self, record: RunRecord) -> None:
        await asyncio.Event().wait()

    async def finalize(self, run_id: str, completion: RunCompletion) -> None:
        await asyncio.Event().wait()

    async def list_runs(self, **kw: Any) -> list[RunRecord]:
        return []

    async def get(self, run_id: str) -> RunRecord | None:
        return None


@pytest.fixture(autouse=True)
def _hanging_store(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(run_storage, "_WRITE_TIMEOUT_SEC", 0.05)
    run_storage.set_run_store(_HangingStore())
    yield
    run_storage.set_run_store(None)


@pytest.mark.asyncio
async def test_create_times_out_contained_and_fast() -> None:
    """Without wait_for, a hung Firestore write blocks POST /run for the
    client's full default deadline (~60s). Must return False promptly."""
    record = RunRecord(
        run_id="run_timeouttest1", target_url="https://t.example", created_at="2026-06-10T01:00:00Z"
    )
    start = time.monotonic()
    assert await run_storage.create_run_record(record) is False
    assert time.monotonic() - start < 2.0


@pytest.mark.asyncio
async def test_finalize_times_out_contained_and_fast() -> None:
    completion = RunCompletion(
        run_id="run_timeouttest1",
        target_url="https://t.example",
        created_at="2026-06-10T01:00:00Z",
        phase="failed",
    )
    start = time.monotonic()
    assert await run_storage.persist_run_completion("run_timeouttest1", completion) is False
    assert time.monotonic() - start < 2.0
