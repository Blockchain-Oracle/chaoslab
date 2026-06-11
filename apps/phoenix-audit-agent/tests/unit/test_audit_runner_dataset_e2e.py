"""Story-9.15 — end-to-end wiring tests after the review-fleet found that
`dataset_snapshot_fields` and `upsert_regression_set` were defined but
never called in production.

These tests drive `drive_audit` with `dataset_id` set and assert the
RunRecord finalizes with the snapshot fields populated, and that
failing-probe rows land in the regression set.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.rubrics import EvalScore

from .storage.fakes import (
    FakePhoenixDatasetClient,
    InMemoryDatasetIndexStore,
    InMemoryRunStore,
)
from .test_audit_runner import SPAN_OK_FAIL, _attack_result, _FakeInjector, wired  # noqa: F401


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Same env wiring as test_audit_runner_sessions."""
    from phoenix_audit_agent.storage import runs as run_storage

    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.fixture
def index_store() -> Iterator[InMemoryDatasetIndexStore]:
    from phoenix_audit_agent.storage import datasets as dataset_storage

    store = InMemoryDatasetIndexStore()
    dataset_storage.set_dataset_index_store(store)
    yield store
    dataset_storage.set_dataset_index_store(None)


@pytest.fixture
def phoenix_client() -> Iterator[FakePhoenixDatasetClient]:
    from phoenix_audit_agent.api import datasets as datasets_api

    client = FakePhoenixDatasetClient()
    datasets_api.set_phoenix_client(client)
    yield client
    datasets_api.set_phoenix_client(None)


async def _seed_battery(
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
    *,
    slug: str,
    name: str,
) -> None:
    from phoenix_audit_agent.storage.models import DatasetIndex

    created = await phoenix_client.create(
        name=name,
        examples=[
            {
                "case_id": "x-1",
                "fault_class": "prompt_injection",
                "prompt": "p",
                "expected": "e",
                "source": "test",
            }
        ],
        description=None,
        source_url="https://example.test/source",
    )
    await index_store.upsert(
        DatasetIndex(
            dataset_id=slug,
            phoenix_dataset_id=created.phoenix_dataset_id,
            name=name,
            kind="battery",
            owner_uid=None,
            agent_id=None,
            row_count=1,
            source_url="https://example.test/source",
            content_hash="sha256:test",
            created_at="2026-06-11T07:00:00+00:00",
            updated_at="2026-06-11T07:00:00+00:00",
        )
    )


@pytest.mark.asyncio
async def test_drive_audit_with_dataset_id_snapshots_onto_run_record(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """C2 wiring: drive_audit pulls the dataset from the index + Phoenix, calls
    dataset_snapshot_fields, persists the snapshot onto the RunRecord."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    await _seed_battery(
        index_store, phoenix_client, slug="harmbench-v1-sample", name="HarmBench v1 (sample)"
    )

    _FakeInjector.results = [_attack_result(0, "a" * 16, "ok")]
    phases: list[str] = []
    # Pre-create the run record so finalize merges into it.
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage.models import RunRecord

    created = utc_now_iso()
    run_id = "run_e2eds00001"
    await run_storage.create_run_record(
        RunRecord(
            run_id=run_id,
            target_url="https://target.example",
            created_at=created,
            owner_uid="uid_alice",
        )
    )
    await ar.drive_audit(
        run_id=run_id,
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
        created_at=created,
        owner_uid="uid_alice",
        dataset_id="harmbench-v1-sample",
    )

    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.dataset_id == "harmbench-v1-sample"
    assert record.dataset_name == "HarmBench v1 (sample)"
    assert record.dataset_phoenix_id  # whatever the fake minted
    assert record.dataset_version_id  # sentinel "latest" for now
    assert record.dataset_kind == "battery"
    assert record.dataset_source_url == "https://example.test/source"


@pytest.mark.asyncio
async def test_drive_audit_failing_probes_populate_regression_set(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """C2 wiring: agent_id + failures => regression-<agent_id> appears in
    the index store with the failing rows."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    # Force one rubric failure so failing_rows is non-empty.
    async def fake_rubric(inp: Any) -> EvalScore:
        if inp.span_id == SPAN_OK_FAIL:
            return EvalScore(passed=False, score=0.0, reason="injected directive obeyed")
        return EvalScore(passed=True, score=1.0, reason="ok")

    monkeypatch.setattr(ar, "apply_rubric", fake_rubric)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_FAIL, "ok")]
    phases: list[str] = []
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage.models import RunRecord

    created = utc_now_iso()
    run_id = "run_e2eds00002"
    await run_storage.create_run_record(
        RunRecord(
            run_id=run_id,
            target_url="https://target.example",
            created_at=created,
            owner_uid="uid_alice",
            agent_id="agt_meridian001",
        )
    )

    await ar.drive_audit(
        run_id=run_id,
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
        created_at=created,
        owner_uid="uid_alice",
        agent_id="agt_meridian001",
    )

    # The regression dataset was created in the index.
    regression_idx = await index_store.get_by_slug("regression-agt_meridian001")
    assert regression_idx is not None
    assert regression_idx.kind == "regression"
    assert regression_idx.owner_uid == "uid_alice"
    assert regression_idx.agent_id == "agt_meridian001"
    # And the Phoenix side has the row.
    items = await phoenix_client.get_examples(regression_idx.phoenix_dataset_id)
    assert len(items) == 1
    assert items[0].fault_class == "prompt_injection"

    # The run record carries the fake-only marker per silent-failure I5.
    record = await run_storage.get_run_store().get(run_id)
    # Note: regression_overwrite_mode is on RunCompletion (extra=forbid).
    # The RunRecord (extra=ignore) accepts arbitrary extras — but we want the
    # marker available on the registry document. Since RunRecord doesn't
    # carry the field today, the marker survives via Firestore's set(merge=True)
    # and rides on the raw doc dict. For now we just confirm the upsert
    # happened — the marker is verified at the audit_runner_emit helper level.
    assert record is not None


@pytest.mark.asyncio
async def test_drive_audit_no_dataset_id_does_not_snapshot(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Backward-compat: omitting dataset_id leaves all snapshot fields None."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    _FakeInjector.results = [_attack_result(0, "a" * 16, "ok")]
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage.models import RunRecord

    created = utc_now_iso()
    run_id = "run_e2eds00003"
    await run_storage.create_run_record(
        RunRecord(
            run_id=run_id,
            target_url="https://target.example",
            created_at=created,
        )
    )

    await ar.drive_audit(
        run_id=run_id,
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=lambda _p: None,
        created_at=created,
    )

    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.dataset_id is None
    assert record.dataset_name is None


@pytest.mark.asyncio
async def test_drive_audit_dataset_id_for_deleted_slug_falls_back_safely(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """If the dataset was deleted between launch and finalize, the snapshot
    helper logs + returns None — the audit still finalizes cleanly."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    _FakeInjector.results = [_attack_result(0, "a" * 16, "ok")]
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage.models import RunRecord

    created = utc_now_iso()
    run_id = "run_e2eds00004"
    await run_storage.create_run_record(
        RunRecord(
            run_id=run_id,
            target_url="https://target.example",
            created_at=created,
        )
    )

    # No seed — dataset_id points at nothing.
    await ar.drive_audit(
        run_id=run_id,
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=lambda _p: None,
        created_at=created,
        dataset_id="harmbench-v1-sample",  # not in the index
    )

    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    # Snapshot fields remain None — contained failure.
    assert record.dataset_id is None
    assert record.dataset_name is None
