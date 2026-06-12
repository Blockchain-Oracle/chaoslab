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

from typing import Any, cast

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
async def test_run_injector_emits_origin_dataset_for_dataset_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Locks the ship-it-real row-interleave contract: when `dataset_slug` is
    set, the dataset's rows are actually invoked against the target, each
    emitting `origin=f"dataset:{slug}"` on its SSE frames. The synthetic
    battery probes still tag `origin="battery"` so the chamber UI can label
    the two phases distinctly (story-9.15 → ship-it-real 2026-06-12)."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.api import datasets as api_datasets
    from phoenix_audit_agent.injector.agent import AttackResult
    from phoenix_audit_agent.injector.target_adapters.base import AdapterResult
    from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem
    from phoenix_audit_agent.storage.models import DatasetIndex

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

    class _StubAdapter:
        def __init__(self, target_url: str = "") -> None:
            self.invocations: list[Any] = []

        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

        async def invoke(self, inv: Any) -> AdapterResult:
            self.invocations.append(inv)
            trace_id = f"d{len(self.invocations):031x}"
            return AdapterResult(
                response="ok",
                span_ids=[f"d{len(self.invocations):015x}"],
                duration_ms=12.0,
                metadata={"trace_id": trace_id},
            )

    stub_adapter = _StubAdapter()

    class _StubIdxStore:
        async def get_by_slug(self, slug: str) -> Any:
            assert slug == "harmbench-v1-sample"
            return DatasetIndex(
                dataset_id=slug,
                phoenix_dataset_id="phx_ds_harmbench",
                name="HarmBench v1 (sample)",
                kind="battery",
                row_count=2,
                content_hash="sha256:x",
                created_at="2026-06-11T07:00:00+00:00",
                updated_at="2026-06-11T07:00:00+00:00",
            )

    class _StubPhoenixClient:
        async def get_examples(self, phx_id: str) -> list[FlatDatasetItem]:
            assert phx_id == "phx_ds_harmbench"
            return [
                FlatDatasetItem(
                    case_id="hb-001",
                    prompt="Test prompt 1 — adversarial.",
                    fault_class="prompt_injection",
                    expected="refuse",
                    source="HarmBench",
                ),
                FlatDatasetItem(
                    case_id="hb-002",
                    prompt="Test prompt 2 — also adversarial.",
                    fault_class="context_poisoning",
                    expected="refuse",
                    source="HarmBench",
                ),
            ]

    from phoenix_audit_agent.storage import datasets as storage_datasets

    def _get_stub_adapter(url: str) -> Any:
        return stub_adapter

    def _get_stub_idx_store() -> Any:
        return _StubIdxStore()

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    # The dataset-row phase uses the build_adapter audit_runner.py passes to
    # run_dataset_rows — monkeypatching once covers both paths.
    monkeypatch.setattr(ar, "build_adapter", _get_stub_adapter)
    monkeypatch.setattr(storage_datasets, "get_dataset_index_store", _get_stub_idx_store)
    api_datasets.set_phoenix_client(cast(Any, _StubPhoenixClient()))
    try:
        state = await ar._run_injector(
            run_id="run_test12345678",
            target_url="https://target.example",
            runs_per_fault=1,
            prompt="p",
            emit=emit,
            dataset_slug="harmbench-v1-sample",
        )
    finally:
        api_datasets.set_phoenix_client(None)

    started = [p for e, p in frames if e == "test_started"]
    completed = [p for e, p in frames if e == "test_completed"]
    # 1 synthetic + 2 dataset rows.
    assert len(started) == 3
    assert len(completed) == 3
    # First is battery (the synthetic injector's probe).
    assert started[0]["origin"] == "battery"
    # The next two are dataset:slug.
    assert started[1]["origin"] == "dataset:harmbench-v1-sample"
    assert started[2]["origin"] == "dataset:harmbench-v1-sample"
    # case_id + source ride along on the dataset frames for traceability.
    assert started[1]["case_id"] == "hb-001"
    assert started[1]["source"] == "HarmBench"
    assert started[1]["fault_class"] == "prompt_injection"
    assert started[2]["case_id"] == "hb-002"
    assert started[2]["fault_class"] == "context_poisoning"
    # The state carries all 3 results, in order.
    assert len(state.attack_results) == 3
    assert state.attack_results[1].attack_payload == "Test prompt 1 — adversarial."
    assert state.attack_results[2].attack_payload == "Test prompt 2 — also adversarial."
    # The adapter was invoked once per dataset row.
    assert len(stub_adapter.invocations) == 2


@pytest.mark.asyncio
async def test_run_injector_dataset_phase_failure_does_not_abort_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure inside the dataset-row phase (Phoenix outage, missing index,
    adapter connect crash) MUST NOT abort the audit — the synthetic battery
    already produced real verdicts. Contains to a structured log line and
    returns the state with the synthetic probes intact."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.api import datasets as api_datasets
    from phoenix_audit_agent.injector.agent import AttackResult
    from phoenix_audit_agent.storage import datasets as storage_datasets

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

    class _BoomIdxStore:
        async def get_by_slug(self, slug: str) -> Any:
            raise RuntimeError("firestore down")

    def _get_boom_idx_store() -> Any:
        return _BoomIdxStore()

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    monkeypatch.setattr(storage_datasets, "get_dataset_index_store", _get_boom_idx_store)
    api_datasets.set_phoenix_client(None)

    state = await ar._run_injector(
        run_id="run_test12345678",
        target_url="https://target.example",
        runs_per_fault=1,
        prompt="p",
        emit=emit,
        dataset_slug="some-slug",
    )

    # Synthetic probe still there; no dataset probes appended.
    assert len(state.attack_results) == 1
    assert state.attack_results[0].fault_class == "prompt_injection"
    started = [p for e, p in frames if e == "test_started"]
    assert len(started) == 1
    assert started[0]["origin"] == "battery"


def _make_fake_injector_with_one_battery_probe() -> type:
    """Shared fixture-builder for the dataset-phase failure-path tests."""
    from phoenix_audit_agent.injector.agent import AttackResult, AttackRun

    class _FakeInjector:
        def __init__(self, **kwargs: Any) -> None:
            self.state = kwargs["state"]
            self.on_attack_start = kwargs.get("on_attack_start")
            self.on_attack_end = kwargs.get("on_attack_end")

        async def run(self) -> None:
            self.state.baseline_passed = True
            self.state.baseline_pass_rate = 1.0
            ar_ = AttackRun(run_idx=0, fault_class="prompt_injection", variant_idx=0)
            res = AttackResult(
                run_idx=0,
                fault_class="prompt_injection",
                span_id="c" * 16,
                trace_id="c" * 32,
                status="ok",
                duration_ms=10.0,
            )
            if self.on_attack_start:
                await self.on_attack_start(ar_)
            self.state.record_attack(res)
            if self.on_attack_end:
                await self.on_attack_end(res)

    return _FakeInjector


@pytest.mark.asyncio
async def test_dataset_phase_get_examples_failure_contained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR #129 TQR med#1 — branch coverage for the Phoenix get_examples
    failure path. Synthetic probes stay intact; no dataset:* frames emit."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.api import datasets as api_datasets
    from phoenix_audit_agent.storage import datasets as storage_datasets
    from phoenix_audit_agent.storage.models import DatasetIndex

    frames: list[tuple[str, dict[str, Any]]] = []

    async def emit(event: str, payload: dict[str, Any]) -> None:
        frames.append((event, payload))

    class _StubIdxStore:
        async def get_by_slug(self, slug: str) -> Any:
            return DatasetIndex(
                dataset_id=slug,
                phoenix_dataset_id="phx_ds_unreachable",
                name="x",
                kind="battery",
                row_count=1,
                content_hash="sha256:x",
                created_at="2026-06-11T07:00:00+00:00",
                updated_at="2026-06-11T07:00:00+00:00",
            )

    class _BoomPhoenixClient:
        async def get_examples(self, phx_id: str) -> Any:
            raise RuntimeError("phoenix 5xx")

    def _get_stub_idx_store() -> Any:
        return _StubIdxStore()

    monkeypatch.setattr(ar, "Injector", _make_fake_injector_with_one_battery_probe())
    monkeypatch.setattr(storage_datasets, "get_dataset_index_store", _get_stub_idx_store)
    api_datasets.set_phoenix_client(cast(Any, _BoomPhoenixClient()))
    try:
        state = await ar._run_injector(
            run_id="run_xyz",
            target_url="https://target.example",
            runs_per_fault=1,
            prompt="p",
            emit=emit,
            dataset_slug="some-slug",
        )
    finally:
        api_datasets.set_phoenix_client(None)

    assert len(state.attack_results) == 1
    started = [p for e, p in frames if e == "test_started"]
    assert len(started) == 1
    assert started[0]["origin"] == "battery"
    assert all(not p.get("origin", "").startswith("dataset:") for _e, p in frames)


@pytest.mark.asyncio
async def test_dataset_phase_adapter_connect_failure_contained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR #129 TQR med#1 — branch coverage for adapter.connect failure.
    Synthetic probes stay intact; no dataset:* frames emit."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.api import datasets as api_datasets
    from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem
    from phoenix_audit_agent.storage import datasets as storage_datasets
    from phoenix_audit_agent.storage.models import DatasetIndex

    frames: list[tuple[str, dict[str, Any]]] = []

    async def emit(event: str, payload: dict[str, Any]) -> None:
        frames.append((event, payload))

    class _StubIdxStore:
        async def get_by_slug(self, slug: str) -> Any:
            return DatasetIndex(
                dataset_id=slug,
                phoenix_dataset_id="phx_ds_x",
                name="x",
                kind="battery",
                row_count=1,
                content_hash="sha256:x",
                created_at="2026-06-11T07:00:00+00:00",
                updated_at="2026-06-11T07:00:00+00:00",
            )

    class _OneRowPhoenixClient:
        async def get_examples(self, phx_id: str) -> list[FlatDatasetItem]:
            return [
                FlatDatasetItem(
                    case_id="x-1",
                    prompt="adversarial",
                    fault_class="prompt_injection",
                    expected="refuse",
                    source="X",
                )
            ]

    class _ConnectBoomAdapter:
        def __init__(self, url: str = "") -> None:
            pass

        async def connect(self) -> None:
            raise RuntimeError("adapter handshake refused")

        async def disconnect(self) -> None:
            pass

    boom_adapter = _ConnectBoomAdapter()

    def _get_boom_adapter(url: str) -> Any:
        return boom_adapter

    def _get_stub_idx_store() -> Any:
        return _StubIdxStore()

    monkeypatch.setattr(ar, "Injector", _make_fake_injector_with_one_battery_probe())
    monkeypatch.setattr(ar, "build_adapter", _get_boom_adapter)
    monkeypatch.setattr(storage_datasets, "get_dataset_index_store", _get_stub_idx_store)
    api_datasets.set_phoenix_client(cast(Any, _OneRowPhoenixClient()))
    try:
        state = await ar._run_injector(
            run_id="run_xyz",
            target_url="https://target.example",
            runs_per_fault=1,
            prompt="p",
            emit=emit,
            dataset_slug="some-slug",
        )
    finally:
        api_datasets.set_phoenix_client(None)

    assert len(state.attack_results) == 1
    started = [p for e, p in frames if e == "test_started"]
    assert len(started) == 1
    assert started[0]["origin"] == "battery"


@pytest.mark.asyncio
async def test_dataset_row_with_unknown_fault_class_skipped_not_coerced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR #129 code-review #2: rows with fault_class outside the four-class
    taxonomy must be skipped with a `test_skipped` SSE event — NOT silently
    coerced to prompt_injection. The signed report's cluster + fault-class
    breakdown stays honest."""
    from phoenix_audit_agent import audit_runner as ar
    from phoenix_audit_agent.api import datasets as api_datasets
    from phoenix_audit_agent.injector.target_adapters.base import AdapterResult
    from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem
    from phoenix_audit_agent.storage import datasets as storage_datasets
    from phoenix_audit_agent.storage.models import DatasetIndex

    frames: list[tuple[str, dict[str, Any]]] = []

    async def emit(event: str, payload: dict[str, Any]) -> None:
        frames.append((event, payload))

    class _StubAdapter:
        def __init__(self, url: str = "") -> None:
            self.invocations = 0

        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

        async def invoke(self, inv: Any) -> AdapterResult:
            self.invocations += 1
            tid = f"d{self.invocations:031x}"
            return AdapterResult(
                response="ok",
                span_ids=[f"d{self.invocations:015x}"],
                duration_ms=10.0,
                metadata={"trace_id": tid},
            )

    stub_adapter = _StubAdapter()

    class _StubIdxStore:
        async def get_by_slug(self, slug: str) -> Any:
            return DatasetIndex(
                dataset_id=slug,
                phoenix_dataset_id="phx_ds_x",
                name="x",
                kind="battery",
                row_count=2,
                content_hash="sha256:x",
                created_at="2026-06-11T07:00:00+00:00",
                updated_at="2026-06-11T07:00:00+00:00",
            )

    class _MixedClassPhoenixClient:
        async def get_examples(self, phx_id: str) -> list[FlatDatasetItem]:
            return [
                FlatDatasetItem(
                    case_id="ok-1",
                    prompt="adversarial 1",
                    fault_class="prompt_injection",  # in taxonomy
                    expected="refuse",
                    source="X",
                ),
                FlatDatasetItem(
                    case_id="bad-1",
                    prompt="adversarial 2",
                    fault_class="harmful_content",  # OUTSIDE taxonomy
                    expected="refuse",
                    source="X",
                ),
            ]

    def _get_stub_adapter(url: str) -> Any:
        return stub_adapter

    def _get_stub_idx_store() -> Any:
        return _StubIdxStore()

    monkeypatch.setattr(ar, "Injector", _make_fake_injector_with_one_battery_probe())
    monkeypatch.setattr(ar, "build_adapter", _get_stub_adapter)
    monkeypatch.setattr(storage_datasets, "get_dataset_index_store", _get_stub_idx_store)
    api_datasets.set_phoenix_client(cast(Any, _MixedClassPhoenixClient()))
    try:
        state = await ar._run_injector(
            run_id="run_xyz",
            target_url="https://target.example",
            runs_per_fault=1,
            prompt="p",
            emit=emit,
            dataset_slug="harmbench",
        )
    finally:
        api_datasets.set_phoenix_client(None)

    # 1 synthetic + 1 in-taxonomy dataset row = 2 attack results.
    # The out-of-taxonomy row gets a `test_skipped` event but no AttackResult.
    assert len(state.attack_results) == 2
    # Adapter was invoked once (for the in-taxonomy row only).
    assert stub_adapter.invocations == 1
    skipped = [p for e, p in frames if e == "test_skipped"]
    assert len(skipped) == 1
    assert skipped[0]["fault_class"] == "harmful_content"
    assert skipped[0]["case_id"] == "bad-1"
    assert "fault_class" in skipped[0]["reason"] or "taxonomy" in skipped[0]["reason"]
    # No fabricated test_completed / test_started for the skipped row.
    started_dataset = [
        p for e, p in frames if e == "test_started" and p.get("origin", "").startswith("dataset:")
    ]
    assert len(started_dataset) == 1
    assert started_dataset[0]["case_id"] == "ok-1"


@pytest.fixture(autouse=True)
def _reset_phoenix_client_after_each_test() -> Any:
    """PR #129 TQR med#3 — autouse fixture that resets the module-global
    Phoenix client holder so a test that forgets the try/finally can't leak
    state into the next test in the file."""
    from phoenix_audit_agent.api import datasets as api_datasets

    yield
    api_datasets.set_phoenix_client(None)


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
