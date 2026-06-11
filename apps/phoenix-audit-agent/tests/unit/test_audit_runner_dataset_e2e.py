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
    # H-NEW-2: the real Phoenix version_id from the SDK Dataset.version_id
    # rides through. The fake mints `phx_v_NNNNNN` so the snapshot pins
    # an actual evidence-chain identifier, not the old "latest" sentinel.
    assert record.dataset_version_id is not None
    assert record.dataset_version_id.startswith("phx_v_")
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

    # H-NEW-1 (review-fleet pass 2): the marker must survive read-back via
    # `RunRecord.model_validate` — it's declared on `RunRecord` now so a
    # signed-report renderer reading via the model sees it.
    from phoenix_audit_agent.audit_runner_emit import REGRESSION_OVERWRITE_NEWEST_WINS

    record = await run_storage.get_run_store().get(run_id)
    assert record is not None
    assert record.regression_overwrite_mode == REGRESSION_OVERWRITE_NEWEST_WINS


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


@pytest.mark.asyncio
async def test_drive_audit_second_run_appends_to_existing_regression_set(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Finding C (review-fleet pass 2): the SECOND audit against the same
    agent exercises the `_append_regression_examples` path, not `_create_`.
    The regression-set keeps the agent's failure history across audits."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    async def fake_rubric(inp: Any) -> EvalScore:
        if inp.span_id == SPAN_OK_FAIL:
            return EvalScore(passed=False, score=0.0, reason="bad")
        return EvalScore(passed=True, score=1.0, reason="ok")

    monkeypatch.setattr(ar, "apply_rubric", fake_rubric)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_FAIL, "ok")]

    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage.models import RunRecord

    async def _one_run(run_id: str) -> None:
        await run_storage.create_run_record(
            RunRecord(
                run_id=run_id,
                target_url="https://target.example",
                created_at=utc_now_iso(),
                owner_uid="uid_alice",
                agent_id="agt_repeat001",
            )
        )
        await ar.drive_audit(
            run_id=run_id,
            target_url="https://target.example",
            runs_per_fault=1,
            emit=wired.emit,
            set_phase=lambda _p: None,
            created_at=utc_now_iso(),
            owner_uid="uid_alice",
            agent_id="agt_repeat001",
        )

    await _one_run("run_first00001")
    first_idx = await index_store.get_by_slug("regression-agt_repeat001")
    assert first_idx is not None
    first_phx_id = first_idx.phoenix_dataset_id
    first_record = await run_storage.get_run_store().get("run_first00001")
    assert first_record is not None
    first_version = first_record.dataset_version_id  # only set on dataset_id runs;
    # for regression-only audits the run record's dataset_version_id is None.
    # We instead read the version_id off the fake's _latest_version map.
    version_after_first = phoenix_client._latest_version[first_phx_id]

    # Second audit reuses the existing regression set (same Phoenix dataset
    # id; new version_id after the append). The `_append_regression_examples`
    # branch is what carries us here — first run hit `_create_`.
    await _one_run("run_second0001")
    second_idx = await index_store.get_by_slug("regression-agt_repeat001")
    assert second_idx is not None
    assert second_idx.phoenix_dataset_id == first_phx_id
    assert second_idx.updated_at >= first_idx.updated_at
    # Test-analyzer round-3 (6): pin that Phoenix versioning actually
    # advanced — a bug where `_append_regression_examples` silently
    # reused the v1 version_id would still produce equal updated_at.
    version_after_second = phoenix_client._latest_version[first_phx_id]
    assert version_after_second != version_after_first
    assert first_version is None  # regression-only audits don't snapshot
    # Same probe failing twice -> same case_id digest -> dedup to 1 row.
    items = await phoenix_client.get_examples(first_phx_id)
    assert len(items) == 1, [i.case_id for i in items]


@pytest.mark.asyncio
async def test_get_runs_id_surfaces_dataset_snapshot(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
    auth_as,
) -> None:
    """Gap 2 (review-fleet pass 2): the GET /runs/{id} JSON wire response
    carries the dataset block. The signed report cover renderer + the web
    `/run/<id>` page both read via this route — if the FastAPI serializer
    ever dropped the fields, the cover line would silently go blank."""
    import os

    import httpx

    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.storage import runs as run_storage
    from phoenix_audit_agent.storage.models import RunRecord

    # The /runs/{id} route requires auth — wire the global test seam.
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    for k in list(os.environ):
        if k.startswith(("PHOENIX_", "GCS_", "FIREBASE_")):
            monkeypatch.delenv(k, raising=False)
    get_settings.cache_clear()

    auth_as("uid_alice", email="alice@example.com")

    await _seed_battery(
        index_store, phoenix_client, slug="harmbench-v1-sample", name="HarmBench v1 (sample)"
    )
    run_id = "run_runsroute01"
    await run_storage.create_run_record(
        RunRecord(
            run_id=run_id,
            target_url="https://target.example",
            created_at=utc_now_iso(),
            owner_uid="uid_alice",
        )
    )
    _FakeInjector.results = [_attack_result(0, "a" * 16, "ok")]
    await ar.drive_audit(
        run_id=run_id,
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=lambda _p: None,
        created_at=utc_now_iso(),
        owner_uid="uid_alice",
        dataset_id="harmbench-v1-sample",
    )

    from phoenix_audit_agent.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"/runs/{run_id}")
    assert r.status_code == 200, r.text
    run = r.json()["run"]
    assert run["dataset_id"] == "harmbench-v1-sample"
    assert run["dataset_name"] == "HarmBench v1 (sample)"
    assert run["dataset_phoenix_id"]
    assert run["dataset_version_id"].startswith("phx_v_")
    assert run["dataset_kind"] == "battery"
    assert run["dataset_source_url"] == "https://example.test/source"


@pytest.mark.asyncio
async def test_drive_audit_append_path_accumulates_different_case_ids(
    wired,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    index_store: InMemoryDatasetIndexStore,
    phoenix_client: FakePhoenixDatasetClient,
) -> None:
    """Round-4 test-analyzer (5): two audits producing DIFFERENT failures
    accumulate in the regression set. The previous append test only
    exercised the dedup branch — a `_append_regression_examples` bug that
    silently dropped genuinely-new rows would pass that test."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.injector.agent import AttackResult
    from phoenix_audit_agent.storage import runs as run_storage
    from phoenix_audit_agent.storage.models import RunRecord

    async def fake_rubric(inp: Any) -> EvalScore:
        # Every probe fails — both audits.
        return EvalScore(passed=False, score=0.0, reason=inp.span_id[:8])

    monkeypatch.setattr(ar, "apply_rubric", fake_rubric)

    # Audit 1: SPAN_OK_FAIL ("b" * 16)
    async def _run(span_marker: str, run_id: str) -> None:
        _FakeInjector.results = [
            AttackResult(
                run_idx=0,
                fault_class="prompt_injection",
                span_id=span_marker * 16,
                trace_id=span_marker * 32,
                status="ok",
                duration_ms=10.0,
            )
        ]
        await run_storage.create_run_record(
            RunRecord(
                run_id=run_id,
                target_url="https://t.example",
                created_at=utc_now_iso(),
                owner_uid="uid_alice",
                agent_id="agt_accum001",
            )
        )
        await ar.drive_audit(
            run_id=run_id,
            target_url="https://t.example",
            runs_per_fault=1,
            emit=wired.emit,
            set_phase=lambda _p: None,
            created_at=utc_now_iso(),
            owner_uid="uid_alice",
            agent_id="agt_accum001",
        )

    await _run("a", "run_accum00001")
    await _run("c", "run_accum00002")
    # The two trace excerpts the FakeSpans fixture emits differ across
    # span markers (the suite fixture's trace_excerpt prefixes the
    # span_id), so the (fault_class, trace_excerpt) digest differs and
    # we should have TWO distinct case_ids in the regression set.
    regression_idx = await index_store.get_by_slug("regression-agt_accum001")
    assert regression_idx is not None
    items = await phoenix_client.get_examples(regression_idx.phoenix_dataset_id)
    case_ids = {i.case_id for i in items}
    assert len(case_ids) >= 2, sorted(case_ids)
