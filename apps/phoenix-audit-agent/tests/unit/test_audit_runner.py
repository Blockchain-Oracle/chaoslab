"""drive_audit — the REAL pipeline behind POST /run.

Pins the SSE event contract the frontend chamber consumes:

    phase_change(injector)
    -> test_started / test_completed per attack (interleaved, ordered)
    -> phase_change(judge)
    -> test_verdict per attack (rubric-scored; transport failures marked)
    -> cluster_set (ONLY when rubric failures exist; transport-only
       failures are excluded from the clusterer input — they carry no
       usable span evidence)
    -> phase_change(patcher) -> recipe (with markdown_url)
    -> complete {passed, failed}

All collaborator seams (Injector, apply_rubric, run_clustering, Patcher,
MarkdownEmitter, phoenix client factory) are module attributes on
`phoenix_audit_agent.audit_runner` so these tests monkeypatch them with fakes —
no Gemini, no Phoenix, no network.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.injector.agent import AttackResult, AttackRun, InjectorState
from phoenix_audit_agent.judge.clustering import FailureCluster, FailureClusterSet
from phoenix_audit_agent.judge.rubrics import EvalScore
from phoenix_audit_agent.patcher.recipe import HardeningRecipe


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # drive_audit reads TARGET_PHOENIX_PROJECT via get_settings(); wire the
    # Vertex path so Settings() construction is deterministic regardless of the
    # developer's shell env (CI runs clean — local .env must not mask this).
    from phoenix_audit_agent.storage import runs as run_storage

    from .storage.fakes import InMemoryRunStore

    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()
    # In-memory store seam — the finalize write-through must never touch real
    # Firestore from a developer machine with live ADC.
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


SPAN_OK_PASS = "a" * 16
SPAN_OK_FAIL = "b" * 16
SPAN_TRANSPORT = "c" * 16
SPAN_RUBRIC_BOOM = "e" * 16


def _attack_result(
    run_idx: int, span_id: str, status: Literal["ok", "error", "timeout"]
) -> AttackResult:
    return AttackResult(
        run_idx=run_idx,
        fault_class="prompt_injection",
        span_id=span_id,
        trace_id=span_id * 2,
        status=status,
        duration_ms=10.0,
    )


def _v1_span(span_id: str, *, attributes: dict[str, Any]) -> dict[str, Any]:
    """Dict-shaped span as the real phoenix client returns from get_spans."""
    return {
        "name": "agent.invoke",
        "context": {"trace_id": span_id * 2, "span_id": span_id},
        "span_kind": "AGENT",
        "start_time": "2026-06-10T00:00:00+00:00",
        "end_time": "2026-06-10T00:00:01+00:00",
        "status_code": "OK",
        "attributes": attributes,
    }


def _fault_marker_children(trace_id: str) -> list[dict[str, Any]]:
    """One child span per fault class carrying the fault-fired marker —
    the judge refuses to score a probe whose registered fault never
    executed (PR #95 review M3), so the fake trace must prove firing."""
    classes = (
        "malformed_tool_output",
        "prompt_injection",
        "context_poisoning",
        "latency_spike",
    )
    children = []
    for i, fc in enumerate(classes):
        child = _v1_span(f"{i:016x}", attributes={"phoenix_audit.fault.type": fc})
        child["parent_id"] = trace_id[:16]
        children.append(child)
    return children


@dataclass
class _Emitted:
    frames: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    clusterer_calls: list[list[Any]] = field(default_factory=list)
    report_data: list[Any] = field(default_factory=list)
    recipe_markdowns: list[str | None] = field(default_factory=list)
    events_calls: list[dict[str, Any]] = field(default_factory=list)

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        self.frames.append((event, payload))

    def names(self) -> list[str]:
        return [name for name, _ in self.frames]

    def first(self, event: str) -> dict[str, Any]:
        for name, payload in self.frames:
            if name == event:
                return payload
        raise AssertionError(f"event {event!r} never emitted: {self.names()}")


class _FakeInjector:
    """Stands in for phoenix_audit_agent.audit_runner.Injector."""

    results: ClassVar[list[AttackResult]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.state: InjectorState = kwargs["state"]
        self.on_attack_start = kwargs.get("on_attack_start")
        self.on_attack_end = kwargs.get("on_attack_end")

    async def run(self) -> InjectorState:
        self.state.baseline_passed = True
        self.state.baseline_pass_rate = 1.0
        for i, result in enumerate(type(self).results):
            if self.on_attack_start is not None:
                await self.on_attack_start(
                    AttackRun(run_idx=i, fault_class=result.fault_class, variant_idx=0)
                )
            self.state.record_attack(result)
            if self.on_attack_end is not None:
                await self.on_attack_end(result)
        return self.state


def _cluster_set(span_ids: list[str]) -> FailureClusterSet:
    return FailureClusterSet(
        clusters=[
            FailureCluster(
                cluster_id="cluster_deadbeef",
                root_cause="unvalidated input reaches the decision tool",
                failure_count=len(span_ids),
                span_ids=span_ids,
                fault_classes=["prompt_injection"],
            )
        ],
        total_failures=len(span_ids),
    )


def _recipe() -> HardeningRecipe:
    return HardeningRecipe(
        recipe_id="recipe_deadbeefcafe",
        target_agent_id="https://target.example",
        generated_at="2026-06-10T00:00:00Z",
        cluster_set=_cluster_set([SPAN_OK_FAIL]),
        prompt_patches=[],
        tool_validation_diffs=[],
        regression_test_cases=[],
        estimated_resilience_improvement=0.5,
        metadata={},
    )


@dataclass
class _FakeEmitResult:
    signed_url: str = "https://gcs.example/recipe_deadbeefcafe.md"


@pytest.fixture
def wired(monkeypatch: pytest.MonkeyPatch) -> _Emitted:
    import phoenix_audit_agent.audit_runner as ar

    emitted = _Emitted()

    async def fake_apply_rubric(inp: Any) -> EvalScore:
        if inp.span_id == SPAN_RUBRIC_BOOM:
            msg = "synthetic-rubric-rate-limit"
            raise RuntimeError(msg)
        if inp.span_id == SPAN_OK_FAIL:
            return EvalScore(passed=False, score=0.0, reason="injected directive obeyed")
        return EvalScore(passed=True, score=1.0, reason="refused correctly")

    async def fake_run_clustering(failures: Any, client: Any, **_: Any) -> FailureClusterSet:
        emitted.clusterer_calls.append(list(failures))
        return _cluster_set([f.span_id for f in failures])

    class _FakePatcher:
        async def run(self, cluster_set: Any, target_agent_id: str) -> HardeningRecipe:
            return _recipe()

    class _FakeMarkdownEmitter:
        async def emit(self, recipe: Any) -> _FakeEmitResult:
            return _FakeEmitResult()

    async def fake_generate_signed_report(
        data: Any, *, recipe_markdown: str | None = None
    ) -> dict[str, str]:
        emitted.report_data.append(data)
        emitted.recipe_markdowns.append(recipe_markdown)
        return {
            "report.pdf": "https://gcs.example/reports/r/report.pdf",
            "report.json": "https://gcs.example/reports/r/report.json",
            "signature.json": "https://gcs.example/reports/r/signature.json",
        }

    class _FakeSpans:
        # Mirrors the real client: get_spans by trace. No phoenix_audit.honored
        # attribute — the demo target doesn't emit the header-convention ack
        # yet, so honored_missing counts these. Tests build trace_id=span_id*2,
        # so the matching span id is recoverable from the queried trace.
        async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
            trace_id = kwargs["trace_ids"][0]
            return [_v1_span(trace_id[:16], attributes={}), *_fault_marker_children(trace_id)]

    class _FakePhoenix:
        spans = _FakeSpans()

    async def fake_persist_events(
        run_id: str, frames: list[dict[str, Any]], *, created_at: str
    ) -> bool:
        emitted.events_calls.append(
            {"run_id": run_id, "frames": list(frames), "created_at": created_at}
        )
        return True

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    monkeypatch.setattr(ar, "apply_rubric", fake_apply_rubric)
    monkeypatch.setattr(ar, "run_clustering", fake_run_clustering)
    monkeypatch.setattr(ar, "Patcher", _FakePatcher)
    monkeypatch.setattr(ar, "MarkdownEmitter", _FakeMarkdownEmitter)
    monkeypatch.setattr(ar, "make_phoenix_client", _FakePhoenix)
    monkeypatch.setattr(ar, "generate_signed_report", fake_generate_signed_report)
    # raising=False: lets the suite express the events contract before the
    # seam exists (TDD red) without erroring unrelated tests.
    monkeypatch.setattr(ar, "persist_run_events", fake_persist_events, raising=False)

    return emitted


@pytest.mark.asyncio
async def test_event_order_with_failures(wired: _Emitted) -> None:
    from phoenix_audit_agent.audit_runner import drive_audit

    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_OK_FAIL, "ok"),
        _attack_result(2, SPAN_TRANSPORT, "error"),
    ]
    phases: list[str] = []

    await drive_audit(
        run_id="run_abcabcabcabc",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
    )

    names = wired.names()
    # interleaving: started_k immediately precedes completed_k
    assert names[: 1 + 6] == [
        "phase_change",
        "test_started",
        "test_completed",
        "test_started",
        "test_completed",
        "test_started",
        "test_completed",
    ]
    judge_idx = names.index("phase_change", 1)
    assert names[judge_idx + 1 : judge_idx + 4] == [
        "test_verdict",
        "test_verdict",
        "test_verdict",
    ]
    assert "cluster_set" in names
    assert "recipe" in names
    assert names[-1] == "complete"

    # verdicts: rubric pass / rubric fail / transport fail — every frame is
    # self-contained (carries fault_class) so late-join clients render real chips
    verdicts = [p for n, p in wired.frames if n == "test_verdict"]
    assert [v["verdict"] for v in verdicts] == ["pass", "fail", "fail"]
    assert verdicts[2]["transport_error"] is True
    assert all(v["fault_class"] == "prompt_injection" for v in verdicts)

    # clusterer sees ONLY the rubric failure — never the transport failure
    (clustered,) = wired.clusterer_calls
    assert [f.span_id for f in clustered] == [SPAN_OK_FAIL]

    cluster_payload = wired.first("cluster_set")
    assert cluster_payload["excluded_transport_failures"] == 1
    assert cluster_payload["annotation_writeback_failed"] is False
    assert "skipped" not in cluster_payload

    recipe_payload = wired.first("recipe")
    assert recipe_payload["recipe_id"] == "recipe_deadbeefcafe"
    assert recipe_payload["markdown_url"].startswith("https://")

    # every run emits a signed report; ReportData carries the real probe rows
    report_payload = wired.first("report")
    assert report_payload["pdf_url"].endswith("report.pdf")
    (rd,) = wired.report_data
    assert len(rd.probes) == 3
    # honored {N}: counts ONLY transport-ok probes whose response span lacked
    # phoenix_audit.honored — the transport failure has no response span and
    # must not inflate the locked warning's claim.
    assert rd.honored_missing_count == 2
    # Single assertion on probe-number order — a disjunctive (X == A or Y == B)
    # shape would also accept broken n indices.
    assert [p.verdict for p in sorted(rd.probes, key=lambda p: p.n)] == ["pass", "fail", "fail"]

    complete = wired.first("complete")
    assert complete["passed"] == 1
    assert complete["failed"] == 2
    assert complete["errored"] == 0
    assert complete["transport_failed"] == 1
    assert complete["report_pdf_url"].endswith("report.pdf")

    # The durable PDF renders the recipe CONTENT (story-9.13): the rendered
    # markdown threads into report generation whenever a recipe was produced.
    (recipe_md,) = wired.recipe_markdowns
    assert recipe_md is not None
    assert "Hardening Recipe" in recipe_md

    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_report_skipped_loudly_when_signing_key_missing(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No signing key => report_skipped event, never a silent unsigned artifact."""
    import phoenix_audit_agent.audit_runner as ar

    async def no_key(_data: Any, *, recipe_markdown: str | None = None) -> None:
        return None

    monkeypatch.setattr(ar, "generate_signed_report", no_key)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    skipped = wired.first("report_skipped")
    assert skipped["reason"] == "signing_key_not_configured"
    assert "report" not in wired.names()
    assert wired.first("complete")["report_pdf_url"] is None


@pytest.mark.asyncio
async def test_report_generation_exception_is_contained(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KMS/GCS/renderer failure must not void a successful audit — the run
    completes with a MARKED report_skipped, never an error frame."""
    import phoenix_audit_agent.audit_runner as ar

    async def boom(_data: Any, *, recipe_markdown: str | None = None) -> None:
        msg = "synthetic-kms-outage"
        raise RuntimeError(msg)

    monkeypatch.setattr(ar, "generate_signed_report", boom)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    skipped = wired.first("report_skipped")
    assert skipped["reason"] == "generation_failed:RuntimeError"
    complete = wired.first("complete")
    assert complete["report_pdf_url"] is None
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_honored_span_attribute_excludes_compliant_target(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A target that emits phoenix_audit.honored=true on its response span
    is NOT counted in the locked warning's {N}."""
    import phoenix_audit_agent.audit_runner as ar

    class _HonoredSpans:
        async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
            trace_id = kwargs["trace_ids"][0]
            return [
                _v1_span(trace_id[:16], attributes={"phoenix_audit.honored": True}),
                *_fault_marker_children(trace_id),
            ]

    class _HonoredPhoenix:
        spans = _HonoredSpans()

    monkeypatch.setattr(ar, "make_phoenix_client", _HonoredPhoenix)
    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_OK_FAIL, "ok"),
    ]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    (rd,) = wired.report_data
    assert rd.honored_missing_count == 0


@pytest.mark.asyncio
async def test_unreadable_spans_disclosed_not_counted_compliant(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Phoenix read outage must surface as honored_unreadable_count — never
    inflate {N}, never silently shape the target as compliant."""
    import httpx

    import phoenix_audit_agent.audit_runner as ar

    class _DownSpans:
        async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
            raise httpx.ConnectError("phoenix unreachable")

    class _DownPhoenix:
        spans = _DownSpans()

    monkeypatch.setattr(ar, "make_phoenix_client", _DownPhoenix)
    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_OK_FAIL, "ok"),
    ]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    (rd,) = wired.report_data
    assert rd.honored_missing_count == 0
    assert rd.honored_unreadable_count == 2


@pytest.mark.asyncio
async def test_clean_run_skips_clustering_and_recipe(wired: _Emitted) -> None:
    from phoenix_audit_agent.audit_runner import drive_audit

    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, "d" * 16, "ok"),
    ]
    phases: list[str] = []

    await drive_audit(
        run_id="run_cleanclean12",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
    )

    names = wired.names()
    assert "cluster_set" not in names
    assert "recipe" not in names
    assert wired.clusterer_calls == []

    complete = wired.first("complete")
    assert complete["passed"] == 2
    assert complete["failed"] == 0
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_rubric_exception_is_contained_per_probe(wired: _Emitted) -> None:
    """One rate-limited rubric call must not void the other probes' verdicts.

    The errored probe gets a MARKED `error` verdict (never a fabricated pass
    or an unmarked fail) and is excluded from the clusterer input.
    """
    from phoenix_audit_agent.audit_runner import drive_audit

    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_RUBRIC_BOOM, "ok"),
        _attack_result(2, SPAN_OK_FAIL, "ok"),
    ]
    phases: list[str] = []

    await drive_audit(
        run_id="run_rubricboom12",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
    )

    verdicts = [p for n, p in wired.frames if n == "test_verdict"]
    assert [v["verdict"] for v in verdicts] == ["pass", "error", "fail"]
    assert verdicts[1]["rubric_error"] is True

    # the errored probe never reaches the clusterer
    (clustered,) = wired.clusterer_calls
    assert [f.span_id for f in clustered] == [SPAN_OK_FAIL]

    complete = wired.first("complete")
    assert complete["passed"] == 1
    assert complete["failed"] == 1
    assert complete["errored"] == 1
    # the run completed — containment, not collapse
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_all_errored_run_discloses_clustering_skip_in_report(wired: _Emitted) -> None:
    """Every probe rubric-errored (failed=0, errored>0): the SSE stream says
    'clustering skipped' — the signed report must say the SAME, never render
    indistinguishable from a clean audit (CLAUDE.md silent-failure #4)."""
    from phoenix_audit_agent.audit_runner import drive_audit

    _FakeInjector.results = [
        _attack_result(0, SPAN_RUBRIC_BOOM, "ok"),
    ]
    await drive_audit(
        run_id="run_allerrored1",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=lambda _p: None,
    )

    (report_data,) = wired.report_data
    assert report_data.clustering_skipped == "no_clusterable_failures"
    assert report_data.errored == 1
    assert report_data.failed == 0


@pytest.mark.asyncio
async def test_writeback_failure_recovers_valid_cluster_set(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AnnotationWritebackError preserves a VALID clustering — the driver must
    recover it (marked) instead of voiding clustering + patcher + recipe."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.judge import AnnotationWritebackError

    preserved = _cluster_set([SPAN_OK_FAIL])

    async def boom_writeback(failures: Any, client: Any, **_: Any) -> FailureClusterSet:
        raise AnnotationWritebackError(
            cluster_set=preserved, attempted_count=1, cause=RuntimeError("phoenix 503")
        )

    monkeypatch.setattr(ar, "run_clustering", boom_writeback)

    _FakeInjector.results = [_attack_result(0, SPAN_OK_FAIL, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    cluster_payload = wired.first("cluster_set")
    assert cluster_payload["annotation_writeback_failed"] is True
    assert cluster_payload["clusters"] == 1
    # recipe still generated from the recovered cluster_set
    assert wired.first("recipe")["recipe_id"] == "recipe_deadbeefcafe"
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_all_transport_failures_is_not_a_clean_run(wired: _Emitted) -> None:
    """Failures with zero clusterable evidence must be reported as skipped
    clustering — never silently shaped like a clean audit."""
    _FakeInjector.results = [_attack_result(0, SPAN_TRANSPORT, "error")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    cluster_payload = wired.first("cluster_set")
    assert cluster_payload["skipped"] == "no_clusterable_failures"
    assert cluster_payload["clusters"] == 0
    assert cluster_payload["excluded_transport_failures"] == 1
    assert "recipe" not in wired.names()

    complete = wired.first("complete")
    assert complete["failed"] == 1
    assert complete["transport_failed"] == 1
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_completion_persisted_to_run_store(wired: _Emitted) -> None:
    """The registry index gets the finalize write-through; the complete frame
    discloses persistence success."""
    from phoenix_audit_agent.storage import runs as run_storage

    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_OK_FAIL, "ok"),
    ]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    record = await run_storage.get_run_store().get("run_fixturecase1")
    assert record is not None
    assert record.phase == "succeeded"
    assert record.passed == 1
    assert record.failed == 1
    assert record.recipe_id == "recipe_deadbeefcafe"
    assert record.report_available is True
    assert record.finished_at is not None
    assert wired.first("complete")["persistence_failed"] is False


@pytest.mark.asyncio
async def test_persistence_failure_disclosed_never_fatal(wired: _Emitted) -> None:
    """A Firestore outage must not void a successful audit — the run completes
    and the complete frame is MARKED (CLAUDE.md pattern #4)."""
    from phoenix_audit_agent.storage import runs as run_storage

    class _DownStore:
        async def create(self, record: Any) -> None:
            raise RuntimeError("firestore down")

        async def finalize(self, run_id: str, completion: Any) -> None:
            raise RuntimeError("firestore down")

        async def list_runs(self, **kw: Any) -> tuple[list[Any], bool]:
            return [], False

        async def get(self, run_id: str) -> Any:
            return None

    run_storage.set_run_store(_DownStore())
    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    assert wired.first("complete")["persistence_failed"] is True
    assert phases == ["injector", "judge", "patcher", "succeeded"]


async def drive_audit_for_test(wired: _Emitted, phases: list[str]) -> None:
    from phoenix_audit_agent.audit_runner import drive_audit

    await drive_audit(
        run_id="run_fixturecase1",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
    )


@pytest.mark.asyncio
async def test_events_timeline_persisted_and_flagged(wired: _Emitted) -> None:
    """The full SSE frame timeline — INCLUDING the terminal `complete` frame —
    is persisted for replay, with non-decreasing relative-t stamps, and the
    registry record gains events_available=True (story-9.11)."""
    from phoenix_audit_agent.storage import runs as run_storage

    _FakeInjector.results = [
        _attack_result(0, SPAN_OK_PASS, "ok"),
        _attack_result(1, SPAN_OK_FAIL, "ok"),
    ]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    (call,) = wired.events_calls
    assert call["run_id"] == "run_fixturecase1"
    frames = call["frames"]
    # The persisted timeline mirrors the emitted stream exactly — a replay
    # that diverges from what the operator watched live is invented data.
    assert [f["event"] for f in frames] == wired.names()
    assert frames[-1]["event"] == "complete"
    stamps = [f["t"] for f in frames]
    assert all(isinstance(t, float) and t >= 0.0 for t in stamps)
    assert stamps == sorted(stamps)
    assert [f["data"] for f in frames] == [payload for _, payload in wired.frames]

    record = await run_storage.get_run_store().get("run_fixturecase1")
    assert record is not None
    assert record.events_available is True


@pytest.mark.asyncio
async def test_pipeline_failure_persists_partial_timeline(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mid-audit crash keeps the already-recorded frames replayable — a
    failed run's timeline is exactly when replay matters for forensics
    (PR #99 review C1)."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    async def boom_clustering(failures: Any, client: Any, **_: Any) -> Any:
        msg = "synthetic-clusterer-crash"
        raise RuntimeError(msg)

    monkeypatch.setattr(ar, "run_clustering", boom_clustering)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_FAIL, "ok")]
    phases: list[str] = []

    with pytest.raises(RuntimeError, match="synthetic-clusterer-crash"):
        await drive_audit_for_test(wired, phases)

    (call,) = wired.events_calls
    frames = call["frames"]
    # Everything emitted before the crash is preserved — and nothing more.
    assert [f["event"] for f in frames] == wired.names()
    assert "complete" not in [f["event"] for f in frames]
    record = await run_storage.get_run_store().get("run_fixturecase1")
    assert record is not None
    assert record.events_available is True
    assert record.phase == "failed"


@pytest.mark.asyncio
async def test_events_flag_finalize_failure_is_contained(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """events.json uploaded but the events_available registry write fails:
    the audit still completes; the flag stays False (GCS/registry drift is
    logged at the call site — disclosure, not silence)."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    real_persist = ar.persist_run_completion

    async def flaky_persist(run_id: str, completion: Any) -> bool:
        if completion.events_available:
            return False
        return await real_persist(run_id, completion)

    monkeypatch.setattr(ar, "persist_run_completion", flaky_persist)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    assert wired.first("complete")["persistence_failed"] is False
    record = await run_storage.get_run_store().get("run_fixturecase1")
    assert record is not None
    assert record.events_available is False
    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_events_persist_failure_contained(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An events-upload outage must not void a successful audit: the run
    completes, events_available stays False — disclosed by absence, the
    replay affordance simply never lights up for this run."""
    import phoenix_audit_agent.audit_runner as ar
    from phoenix_audit_agent.storage import runs as run_storage

    async def failing_persist(
        run_id: str, frames: list[dict[str, Any]], *, created_at: str
    ) -> bool:
        return False

    monkeypatch.setattr(ar, "persist_run_events", failing_persist, raising=False)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await drive_audit_for_test(wired, phases)

    assert wired.first("complete")["persistence_failed"] is False
    record = await run_storage.get_run_store().get("run_fixturecase1")
    assert record is not None
    assert record.events_available is False
    assert phases == ["injector", "judge", "patcher", "succeeded"]
