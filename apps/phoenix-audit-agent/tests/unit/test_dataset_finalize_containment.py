"""Story-9.15 round-3 — contained-failure paths in finalize.

The reviewers flagged that the round-2 catch tuple missed several real
error families (Firestore GoogleAPIError, Pydantic ValidationError on a
corrupt index doc, PhoenixDatasetNotFoundError from TOCTOU). These tests
pin the contained behavior: each error type returns None cleanly and
logs the right event family — never escapes finalize.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_build_dataset_snapshot_swallows_phoenix_notfound() -> None:
    """HIGH-1 + MED-1: TOCTOU — dataset deleted between index lookup and
    version call. `get_current_version_id` raises
    `PhoenixDatasetNotFoundError`; the snapshot returns None so finalize
    falls back to 'synthetic battery' instead of pinning to 'unknown'."""
    from phoenix_audit_agent import audit_runner_datasets as ard
    from phoenix_audit_agent.api import datasets as datasets_api
    from phoenix_audit_agent.phoenix_tools.dataset_client import (
        PhoenixDatasetNotFoundError,
    )
    from phoenix_audit_agent.storage import datasets as dataset_storage
    from phoenix_audit_agent.storage.models import DatasetIndex

    from .storage.fakes import FakePhoenixDatasetClient, InMemoryDatasetIndexStore

    # Wire fakes; seed the index but NOT the Phoenix side.
    idx_store = InMemoryDatasetIndexStore()
    dataset_storage.set_dataset_index_store(idx_store)
    phoenix_client = FakePhoenixDatasetClient()
    datasets_api.set_phoenix_client(phoenix_client)
    try:
        await idx_store.upsert(
            DatasetIndex(
                dataset_id="ghost",
                phoenix_dataset_id="phx_ds_neverexists",
                name="Ghost",
                kind="battery",
                owner_uid=None,
                agent_id=None,
                row_count=0,
                source_url=None,
                content_hash="sha256:test",
                created_at="2026-06-11T07:00:00+00:00",
                updated_at="2026-06-11T07:00:00+00:00",
            )
        )
        # Phoenix returns NotFound — index points at a phantom row.
        with pytest.raises(PhoenixDatasetNotFoundError):
            await phoenix_client.get_current_version_id("phx_ds_neverexists")

        snap = await ard.build_dataset_snapshot(dataset_id="ghost", run_id="run_ghost")
        # Contained: returns None instead of pinning to "unknown".
        assert snap is None
    finally:
        dataset_storage.set_dataset_index_store(None)
        datasets_api.set_phoenix_client(None)


@pytest.mark.asyncio
async def test_build_dataset_snapshot_swallows_pydantic_validation_error() -> None:
    """HIGH-3: a corrupt Firestore `DatasetIndex` doc raises
    `ValidationError` from the store. The snapshot must catch + return
    None so the audit finalizes cleanly."""
    from phoenix_audit_agent import audit_runner_datasets as ard
    from phoenix_audit_agent.storage import datasets as dataset_storage

    class _CorruptStore:
        async def get_by_slug(self, slug: str) -> Any:
            # Mimic FirestoreDatasetIndexStore.get_by_slug on a corrupt doc.
            raise ValidationError.from_exception_data("DatasetIndex", [])

    dataset_storage.set_dataset_index_store(_CorruptStore())  # ty: ignore[invalid-argument-type]
    try:
        snap = await ard.build_dataset_snapshot(dataset_id="corrupt-slug", run_id="run_corrupt")
        assert snap is None
    finally:
        dataset_storage.set_dataset_index_store(None)


@pytest.mark.asyncio
async def test_build_dataset_snapshot_swallows_httpx_error() -> None:
    """The original M-NEW-1 path stays covered."""
    from phoenix_audit_agent import audit_runner_datasets as ard
    from phoenix_audit_agent.storage import datasets as dataset_storage

    class _OutageStore:
        async def get_by_slug(self, slug: str) -> Any:
            raise httpx.ConnectError("Firestore unreachable")

    dataset_storage.set_dataset_index_store(_OutageStore())  # ty: ignore[invalid-argument-type]
    try:
        snap = await ard.build_dataset_snapshot(dataset_id="any-slug", run_id="run_outage")
        assert snap is None
    finally:
        dataset_storage.set_dataset_index_store(None)


@pytest.mark.asyncio
async def test_try_regression_upsert_splits_bridge_drift_from_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MED-2: PhoenixDatasetNotFoundError (bridge drift) and
    PhoenixUnavailableError (outage) log DIFFERENT event names — both
    return None to the finalize path. A regulator reading the audit log
    can distinguish "Phoenix deleted between index reads" from "Phoenix
    is down." """
    from phoenix_audit_agent import audit_runner_datasets as ard
    from phoenix_audit_agent.api import datasets as datasets_api
    from phoenix_audit_agent.phoenix_tools.dataset_client import (
        PhoenixDatasetNotFoundError,
        PhoenixUnavailableError,
    )
    from phoenix_audit_agent.storage import datasets as dataset_storage

    captured: list[str] = []

    def _capture(event: str, **kwargs: Any) -> None:
        captured.append(event)

    monkeypatch.setattr(ard._log, "warning", _capture)

    class _Idx:
        async def get_by_slug(self, slug: str) -> None:
            return None

        async def upsert(self, idx: Any) -> None:
            return None

    class _PhoenixDrift:
        async def create(self, **_kwargs: Any) -> Any:
            raise PhoenixDatasetNotFoundError("phx_drift")

    class _PhoenixOutage:
        async def create(self, **_kwargs: Any) -> Any:
            raise PhoenixUnavailableError("outage")

    rows = [
        {
            "case_id": "a",
            "prompt": "p",
            "fault_class": "prompt_injection",
            "expected": "e",
            "source": "s",
        }
    ]

    # Bridge drift path.
    dataset_storage.set_dataset_index_store(_Idx())  # ty: ignore[invalid-argument-type]
    datasets_api.set_phoenix_client(_PhoenixDrift())  # ty: ignore[invalid-argument-type]
    try:
        result = await ard.try_regression_upsert(
            agent_id="agt_x", owner_uid="uid_a", failing_rows=rows, run_id="run_drift"
        )
        assert result is None
        assert "finalize.regression_bridge_drift" in captured
    finally:
        dataset_storage.set_dataset_index_store(None)
        datasets_api.set_phoenix_client(None)

    captured.clear()

    # Outage path.
    dataset_storage.set_dataset_index_store(_Idx())  # ty: ignore[invalid-argument-type]
    datasets_api.set_phoenix_client(_PhoenixOutage())  # ty: ignore[invalid-argument-type]
    try:
        result = await ard.try_regression_upsert(
            agent_id="agt_x", owner_uid="uid_a", failing_rows=rows, run_id="run_outage"
        )
        assert result is None
        assert "finalize.regression_upsert_failed" in captured
        assert "finalize.regression_bridge_drift" not in captured
    finally:
        dataset_storage.set_dataset_index_store(None)
        datasets_api.set_phoenix_client(None)


def test_failing_rows_case_id_is_stable_across_runs() -> None:
    """HIGH-2: case_id MUST be stable across audits for cross-audit dedup
    to work. Two runs producing the same (fault_class, trace_excerpt)
    must produce the same case_id — regardless of probe ordering."""
    from phoenix_audit_agent.audit_runner import _failing_rows_from_tally

    class _F:
        def __init__(self, span_id: str, fault_class: str, excerpt: str) -> None:
            self.span_id = span_id
            self.fault_class = fault_class
            self.trace_excerpt = excerpt

    class _Tally:
        def __init__(self, failures: list[_F]) -> None:
            self.failures = failures
            self.report_probes = []  # n no longer used for case_id stability

    excerpt = "agent obeyed the override and returned the secret"
    run_a = _failing_rows_from_tally(
        _Tally([_F("aaa" * 6, "prompt_injection", excerpt)]),
        run_id="run_a",
    )
    run_b = _failing_rows_from_tally(
        _Tally([_F("bbb" * 6, "prompt_injection", excerpt)]),  # DIFFERENT span_id
        run_id="run_b",
    )
    # Same content -> same case_id even though span_ids and run_ids differ.
    assert run_a[0]["case_id"] == run_b[0]["case_id"]
    # And it's prefixed predictably.
    assert run_a[0]["case_id"].startswith("battery-prompt_injection-")
    # Different content -> different case_id.
    other = _failing_rows_from_tally(
        _Tally([_F("ccc" * 6, "prompt_injection", "different excerpt")]),
        run_id="run_c",
    )
    assert other[0]["case_id"] != run_a[0]["case_id"]


def test_get_current_version_id_typed_guard_against_sdk_drift() -> None:
    """LOW: a future SDK shape drift (returning None / int for version_id)
    raises a typed PhoenixUnavailableError at the wrapper boundary
    instead of silently corrupting the downstream Pydantic str field."""
    from phoenix_audit_agent.phoenix_tools.dataset_client import (
        PhoenixDatasetClientImpl,
        PhoenixUnavailableError,
    )

    class _BadDataset:
        version_id = None

    class _BadDatasets:
        async def get_dataset(self, **_kwargs: Any) -> Any:
            return _BadDataset()

    class _BadClient:
        datasets = _BadDatasets()

    impl = PhoenixDatasetClientImpl()
    bad_client = _BadClient()

    def _get_bad_client(_self: Any = None) -> Any:
        return bad_client

    impl._client = _get_bad_client  # ty: ignore[invalid-assignment]

    import asyncio

    with pytest.raises(PhoenixUnavailableError, match="non-string version_id"):
        asyncio.run(impl.get_current_version_id("phx_x"))
