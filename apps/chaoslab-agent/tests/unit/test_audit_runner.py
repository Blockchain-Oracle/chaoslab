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
`chaoslab_agent.audit_runner` so these tests monkeypatch them with fakes —
no Gemini, no Phoenix, no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

import pytest

from chaoslab_agent.injector.agent import AttackResult, AttackRun, InjectorState
from chaoslab_agent.judge.clustering import FailureCluster, FailureClusterSet
from chaoslab_agent.judge.rubrics import EvalScore
from chaoslab_agent.patcher.recipe import HardeningRecipe

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


@dataclass
class _Emitted:
    frames: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    clusterer_calls: list[list[Any]] = field(default_factory=list)
    report_data: list[Any] = field(default_factory=list)

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
    """Stands in for chaoslab_agent.audit_runner.Injector."""

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
    import chaoslab_agent.audit_runner as ar

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

    async def fake_generate_signed_report(data: Any) -> dict[str, str]:
        emitted.report_data.append(data)
        return {
            "report.pdf": "https://gcs.example/reports/r/report.pdf",
            "report.json": "https://gcs.example/reports/r/report.json",
            "signature.json": "https://gcs.example/reports/r/signature.json",
        }

    class _FakeSpan:
        # No phoenix_audit.honored attribute — the demo target doesn't emit
        # the header-convention ack yet, so honored_missing counts these.
        attributes: ClassVar[dict[str, Any]] = {}

    class _FakeSpans:
        async def get_span(self, span_id: str) -> Any:
            return _FakeSpan()

    class _FakePhoenix:
        spans = _FakeSpans()

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    monkeypatch.setattr(ar, "apply_rubric", fake_apply_rubric)
    monkeypatch.setattr(ar, "run_clustering", fake_run_clustering)
    monkeypatch.setattr(ar, "Patcher", _FakePatcher)
    monkeypatch.setattr(ar, "MarkdownEmitter", _FakeMarkdownEmitter)
    monkeypatch.setattr(ar, "make_phoenix_client", _FakePhoenix)
    monkeypatch.setattr(ar, "generate_signed_report", fake_generate_signed_report)

    return emitted


@pytest.mark.asyncio
async def test_event_order_with_failures(wired: _Emitted) -> None:
    from chaoslab_agent.audit_runner import drive_audit

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
    assert [p.verdict for p in rd.probes] == ["fail", "pass", "fail"] or [
        p.verdict for p in sorted(rd.probes, key=lambda p: p.n)
    ] == ["pass", "fail", "fail"]

    complete = wired.first("complete")
    assert complete["passed"] == 1
    assert complete["failed"] == 2
    assert complete["errored"] == 0
    assert complete["transport_failed"] == 1
    assert complete["report_pdf_url"].endswith("report.pdf")

    assert phases == ["injector", "judge", "patcher", "succeeded"]


@pytest.mark.asyncio
async def test_report_skipped_loudly_when_signing_key_missing(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No signing key => report_skipped event, never a silent unsigned artifact."""
    import chaoslab_agent.audit_runner as ar

    async def no_key(_data: Any) -> None:
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
    import chaoslab_agent.audit_runner as ar

    async def boom(_data: Any) -> None:
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
    import chaoslab_agent.audit_runner as ar

    class _HonoredSpan:
        attributes: ClassVar[dict[str, Any]] = {"phoenix_audit.honored": True}

    class _HonoredSpans:
        async def get_span(self, span_id: str) -> Any:
            return _HonoredSpan()

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
async def test_clean_run_skips_clustering_and_recipe(wired: _Emitted) -> None:
    from chaoslab_agent.audit_runner import drive_audit

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
    from chaoslab_agent.audit_runner import drive_audit

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
async def test_writeback_failure_recovers_valid_cluster_set(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AnnotationWritebackError preserves a VALID clustering — the driver must
    recover it (marked) instead of voiding clustering + patcher + recipe."""
    import chaoslab_agent.audit_runner as ar
    from chaoslab_agent.judge import AnnotationWritebackError

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


async def drive_audit_for_test(wired: _Emitted, phases: list[str]) -> None:
    from chaoslab_agent.audit_runner import drive_audit

    await drive_audit(
        run_id="run_fixturecase1",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
    )
