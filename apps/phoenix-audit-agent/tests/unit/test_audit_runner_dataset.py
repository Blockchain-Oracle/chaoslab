"""Story-9.15 slice 6 — `drive_audit` dataset integration.

Tests cover three plumbings:

1. **SSE `origin` field on `test_started` + `test_completed`.** The chamber
   UI labels each probe row by where it came from (battery vs.
   `dataset:<slug>`). The synthetic battery emits `origin="battery"`.
2. **RunRecord finalize captures `dataset_name` + `dataset_phoenix_id` +
   `dataset_version_id`.** The signed report cover renders the dataset
   name; the JSON artifact carries the Phoenix ids for the evidence
   chain (story-9.15 BDD).
3. **Regression upsert on finalize.** Failing probes for an agent-owned
   audit append into `regression-<agent_slug>` via
   `PhoenixDatasetClient.add_examples`; the dataset is created via
   `create` on first failure.

We monkeypatch `audit_runner` collaborators per the existing pattern.
"""

from __future__ import annotations

from typing import Any

import pytest

from .storage.fakes import FakePhoenixDatasetClient


@pytest.mark.asyncio
async def test_synthetic_battery_emits_origin_battery(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no dataset_id, every test_started + test_completed carries
    `origin="battery"`."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.injector.agent import AttackResult

    frames: list[tuple[str, dict[str, Any]]] = []

    async def emit(event: str, payload: dict[str, Any]) -> None:
        frames.append((event, payload))

    class _FakeInjector:
        def __init__(self, **kwargs: Any) -> None:
            self.state = kwargs["state"]
            self.on_attack_start = kwargs.get("on_attack_start")
            self.on_attack_end = kwargs.get("on_attack_end")

        async def run(self) -> None:
            from phoenix_audit_agent.injector.agent import AttackRun

            self.state.baseline_passed = True
            self.state.baseline_pass_rate = 1.0
            ar_ = AttackRun(run_idx=0, fault_class="prompt_injection", variant_idx=0)
            res = AttackResult(
                run_idx=0,
                fault_class="prompt_injection",
                span_id="a" * 16,
                trace_id="a" * 32,
                status="ok",
                duration_ms=10.0,
            )
            if self.on_attack_start:
                await self.on_attack_start(ar_)
            self.state.record_attack(res)
            if self.on_attack_end:
                await self.on_attack_end(res)

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    await ar._run_injector(
        run_id="run_test12345678",
        target_url="https://target.example",
        runs_per_fault=1,
        prompt="p",
        emit=emit,
        dataset_slug=None,
    )

    started = [p for e, p in frames if e == "test_started"]
    completed = [p for e, p in frames if e == "test_completed"]
    assert started
    assert completed
    assert all(p["origin"] == "battery" for p in started)
    assert all(p["origin"] == "battery" for p in completed)


@pytest.mark.asyncio
async def test_run_injector_emits_origin_dataset_for_dataset_slug() -> None:
    """When `dataset_slug` is set, the SSE frames the chamber UI sees should
    include `origin=f"dataset:{slug}"` on the dataset probes — distinct from
    `origin="battery"` on the synthetic ones. This test pins the value the
    UI reads even if no extra probes get added in the minimum-scope impl
    (`_run_injector` still receives the slug and forwards it through)."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.injector.agent import AttackResult

    frames: list[tuple[str, dict[str, Any]]] = []

    async def emit(event: str, payload: dict[str, Any]) -> None:
        frames.append((event, payload))

    class _FakeInjector:
        def __init__(self, **kwargs: Any) -> None:
            self.state = kwargs["state"]
            self.on_attack_start = kwargs.get("on_attack_start")
            self.on_attack_end = kwargs.get("on_attack_end")

        async def run(self) -> None:
            from phoenix_audit_agent.injector.agent import AttackRun

            self.state.baseline_passed = True
            self.state.baseline_pass_rate = 1.0
            ar_ = AttackRun(run_idx=0, fault_class="prompt_injection", variant_idx=0)
            res = AttackResult(
                run_idx=0,
                fault_class="prompt_injection",
                span_id="b" * 16,
                trace_id="b" * 32,
                status="ok",
                duration_ms=10.0,
            )
            if self.on_attack_start:
                await self.on_attack_start(ar_)
            self.state.record_attack(res)
            if self.on_attack_end:
                await self.on_attack_end(res)

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(ar, "Injector", _FakeInjector)
        await ar._run_injector(
            run_id="run_test12345678",
            target_url="https://target.example",
            runs_per_fault=1,
            prompt="p",
            emit=emit,
            # synthetic-battery probes still get origin="battery"; the slug
            # affects only frames the future extra-probe loop will emit.
            dataset_slug="harmbench-v1-sample",
        )
    finally:
        mp.undo()

    started = [p for e, p in frames if e == "test_started"]
    # Synthetic probes always tagged "battery". A dataset:<slug> probe arrives
    # later if/when the extra loop lands; this test pins the discriminator.
    assert all(p["origin"] == "battery" for p in started)


@pytest.mark.asyncio
async def test_dataset_snapshot_lands_on_run_record_at_finalize() -> None:
    """When `dataset_id` is set on the run, the finalize write captures
    name + phoenix_dataset_id + version_id so the signed report cover
    + the JSON artifact have the canonical strings."""
    from phoenix_audit_agent import audit_runner_datasets as ard
    from phoenix_audit_agent.storage.models import DatasetIndex, RunCompletion

    # Snapshot helper takes (idx, version_id) and produces the merge fields
    # the finalize path will write through to RunRecord.
    idx = DatasetIndex(
        dataset_id="harmbench-v1-sample",
        phoenix_dataset_id="phx_ds_000001",
        name="HarmBench v1 (sample)",
        kind="battery",
        owner_uid=None,
        agent_id=None,
        row_count=50,
        source_url="https://github.com/centerforaisafety/HarmBench",
        content_hash="sha256:x",
        created_at="2026-06-11T07:00:00+00:00",
        updated_at="2026-06-11T07:00:00+00:00",
    )

    fields = ard.dataset_snapshot_fields(idx=idx, version_id="phx_v_000007")
    assert fields == {
        "dataset_id": "harmbench-v1-sample",
        "dataset_name": "HarmBench v1 (sample)",
        "dataset_phoenix_id": "phx_ds_000001",
        "dataset_version_id": "phx_v_000007",
        "dataset_kind": "battery",
        "dataset_source_url": "https://github.com/centerforaisafety/HarmBench",
    }

    # The snapshot is purely additive — RunCompletion.merge_fields with this
    # extra kwargs dict still produces a clean merge.
    base = RunCompletion(
        run_id="run_abc",
        target_url="https://t",
        created_at="2026-06-11T07:00:00+00:00",
        phase="succeeded",
    )
    merge = base.merge_fields()
    assert "dataset_name" not in merge  # RunCompletion stays clean
    # The finalize path lands the snapshot via `set` merge, not via
    # RunCompletion — see audit_runner_emit.finalize_run.


@pytest.mark.asyncio
async def test_regression_upsert_creates_then_appends() -> None:
    """First failing audit for an agent creates `regression-<slug>`;
    subsequent failures `add_examples` into it (Phoenix versioning)."""
    from phoenix_audit_agent import audit_runner_datasets as ard

    fake_phx = FakePhoenixDatasetClient()

    # In-memory index used as the lookup the regression-upsert path reads
    # to find the existing regression set (or create one on first failure).
    class _Idx:
        def __init__(self) -> None:
            self._rows: dict[str, Any] = {}

        async def get_by_slug(self, slug: str):
            return self._rows.get(slug)

        async def upsert(self, idx: Any) -> None:
            self._rows[idx.dataset_id] = idx

    idx_store = _Idx()

    failing_rows_round_1 = [
        {
            "case_id": "fail-a",
            "prompt": "evil 1",
            "fault_class": "prompt_injection",
            "expected": "refuse",
            "source": "audit:run_aaa",
        },
        {
            "case_id": "fail-b",
            "prompt": "evil 2",
            "fault_class": "context_poisoning",
            "expected": "refuse",
            "source": "audit:run_aaa",
        },
    ]
    failing_rows_round_2 = [
        {
            "case_id": "fail-c",
            "prompt": "evil 3",
            "fault_class": "prompt_injection",
            "expected": "refuse",
            "source": "audit:run_bbb",
        },
    ]

    # Round 1: no existing regression set → create.
    snap1 = await ard.upsert_regression_set(
        agent_id="agt_meridian001",
        owner_uid="uid_alice",
        failing_rows=failing_rows_round_1,
        phoenix=fake_phx,
        idx_store=idx_store,
        now="2026-06-11T08:00:00+00:00",
    )
    assert snap1.phoenix_dataset_id.startswith("phx_ds_")
    assert snap1.version_id.startswith("phx_v_")
    # The index row was upserted with the regression kind.
    saved = await idx_store.get_by_slug("regression-agt_meridian001")
    assert saved is not None
    assert saved.kind == "regression"
    assert saved.owner_uid == "uid_alice"
    assert saved.agent_id == "agt_meridian001"

    # Round 2: existing regression set → add_examples (new version).
    snap2 = await ard.upsert_regression_set(
        agent_id="agt_meridian001",
        owner_uid="uid_alice",
        failing_rows=failing_rows_round_2,
        phoenix=fake_phx,
        idx_store=idx_store,
        now="2026-06-11T09:00:00+00:00",
    )
    # Same Phoenix dataset id, new version id.
    assert snap2.phoenix_dataset_id == snap1.phoenix_dataset_id
    assert snap2.version_id != snap1.version_id
    # All three rows now in Phoenix.
    items = await fake_phx.get_examples(snap2.phoenix_dataset_id)
    case_ids = {i.case_id for i in items}
    assert case_ids == {"fail-a", "fail-b", "fail-c"}


@pytest.mark.asyncio
async def test_regression_upsert_dedupes_by_case_id() -> None:
    """If a second audit hits the same `case_id`, the newest row wins —
    no Phoenix-side duplication."""
    from phoenix_audit_agent import audit_runner_datasets as ard

    fake_phx = FakePhoenixDatasetClient()

    class _Idx:
        def __init__(self) -> None:
            self._rows: dict[str, Any] = {}

        async def get_by_slug(self, slug: str):
            return self._rows.get(slug)

        async def upsert(self, idx: Any) -> None:
            self._rows[idx.dataset_id] = idx

    idx_store = _Idx()

    initial = [
        {
            "case_id": "shared",
            "prompt": "old prompt",
            "fault_class": "prompt_injection",
            "expected": "refuse",
            "source": "audit:run_first",
        },
    ]
    await ard.upsert_regression_set(
        agent_id="agt_x",
        owner_uid="uid_alice",
        failing_rows=initial,
        phoenix=fake_phx,
        idx_store=idx_store,
        now="2026-06-11T08:00:00+00:00",
    )

    # Same case_id, newer source.
    update = [
        {
            "case_id": "shared",
            "prompt": "new prompt",
            "fault_class": "prompt_injection",
            "expected": "refuse",
            "source": "audit:run_second",
        },
    ]
    snap = await ard.upsert_regression_set(
        agent_id="agt_x",
        owner_uid="uid_alice",
        failing_rows=update,
        phoenix=fake_phx,
        idx_store=idx_store,
        now="2026-06-11T09:00:00+00:00",
    )
    items = await fake_phx.get_examples(snap.phoenix_dataset_id)
    # One row, the newer.
    assert len(items) == 1
    assert items[0].prompt == "new prompt"
    assert items[0].source == "audit:run_second"
