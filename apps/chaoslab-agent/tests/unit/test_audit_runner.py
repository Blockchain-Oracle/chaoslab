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

    class _FakeSpans:
        async def get_span(self, span_id: str) -> Any:  # pragma: no cover
            raise NotImplementedError

    class _FakePhoenix:
        spans = _FakeSpans()

    monkeypatch.setattr(ar, "Injector", _FakeInjector)
    monkeypatch.setattr(ar, "apply_rubric", fake_apply_rubric)
    monkeypatch.setattr(ar, "run_clustering", fake_run_clustering)
    monkeypatch.setattr(ar, "Patcher", _FakePatcher)
    monkeypatch.setattr(ar, "MarkdownEmitter", _FakeMarkdownEmitter)
    monkeypatch.setattr(ar, "make_phoenix_client", _FakePhoenix)

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

    # verdicts: rubric pass / rubric fail / transport fail
    verdicts = [p for n, p in wired.frames if n == "test_verdict"]
    assert [v["verdict"] for v in verdicts] == ["pass", "fail", "fail"]
    assert verdicts[2]["transport_error"] is True

    # clusterer sees ONLY the rubric failure — never the transport failure
    (clustered,) = wired.clusterer_calls
    assert [f.span_id for f in clustered] == [SPAN_OK_FAIL]

    recipe_payload = wired.first("recipe")
    assert recipe_payload["recipe_id"] == "recipe_deadbeefcafe"
    assert recipe_payload["markdown_url"].startswith("https://")

    complete = wired.first("complete")
    assert complete["passed"] == 1
    assert complete["failed"] == 2

    assert phases == ["injector", "judge", "patcher", "succeeded"]


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
