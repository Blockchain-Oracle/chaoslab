"""Phoenix annotation writeback after clustering."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge._models import FailedSpan
from phoenix_audit_agent.judge.clustering import run_clustering
from phoenix_audit_agent.judge.rubrics._base import (
    EvalScore,
    PhoenixClient,
    _SpansNamespace,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _failures(n: int) -> list[FailedSpan]:
    return [
        FailedSpan(
            span_id=f"{i:016x}",
            fault_class="malformed_tool_output",
            eval_score=EvalScore(passed=False, score=0.0, reason=f"failure {i}"),
            trace_excerpt=f"trace {i}",
        )
        for i in range(n)
    ]


class _RecordingSpans(_SpansNamespace):
    def __init__(self) -> None:
        self.batches: list[list[Any]] = []

    async def get_span(self, span_id: str) -> Any:
        raise NotImplementedError

    async def log_span_annotations(self, *, span_annotations: list[Any]) -> None:
        self.batches.append(list(span_annotations))


class _RecordingClient(PhoenixClient):
    spans: _SpansNamespace

    def __init__(self) -> None:
        self.spans = _RecordingSpans()


class _StubClusterer:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.calls = 0

    async def __call__(self, prompt: str) -> str:
        self.calls += 1
        return self._payload


def _scripted_partition(failures: list[FailedSpan], cluster_count: int) -> str:
    """Split failures into N roughly-equal clusters."""
    buckets: list[list[FailedSpan]] = [[] for _ in range(cluster_count)]
    for i, f in enumerate(failures):
        buckets[i % cluster_count].append(f)
    return json.dumps(
        {
            "clusters": [
                {
                    "cluster_id": f"cluster_{i:08x}",
                    "root_cause": f"root cause #{i}",
                    "failure_count": len(b),
                    "span_ids": [f.span_id for f in b],
                    "fault_classes": sorted({f.fault_class for f in b}),
                }
                for i, b in enumerate(buckets)
                if b
            ]
        }
    )


async def test_annotation_writeback_emits_one_entry_per_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(15)
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=3))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    await run_clustering(failures, phoenix_client=client)

    # Exactly one batch posted, containing 15 entries (one per failed span).
    assert len(cast(_RecordingSpans, client.spans).batches) == 1
    assert len(cast(_RecordingSpans, client.spans).batches[0]) == 15
    # Each entry must carry the phoenix-audit annotation name and an LLM annotator.
    for entry in cast(_RecordingSpans, client.spans).batches[0]:
        assert entry.name == "phoenix_audit_failure_cluster"
        assert entry.annotator_kind == "LLM"
        assert entry.result.label.startswith("cluster_")


async def test_annotation_writeback_assigns_correct_cluster_per_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(6)
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=2))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    result = await run_clustering(failures, phoenix_client=client)

    expected_label: dict[str, str] = {}
    for cluster in result.clusters:
        for sid in cluster.span_ids:
            expected_label[sid] = cluster.cluster_id

    posted = {
        entry.span_id: entry.result.label
        for entry in cast(_RecordingSpans, client.spans).batches[0]
    }
    assert posted == expected_label


async def test_annotation_writeback_skipped_on_clusterer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(4)
    stub = _StubClusterer("not json")
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    from phoenix_audit_agent.judge.clustering import ClusteringError

    with pytest.raises(ClusteringError):
        await run_clustering(failures, phoenix_client=client)
    # Half-written annotations would corrupt the audit report; the
    # writeback must NOT fire when clustering fails.
    assert cast(_RecordingSpans, client.spans).batches == []


# ---------------------------------------------------------------------------
# Annotation entry detail asserts (round-2)
# ---------------------------------------------------------------------------


async def test_annotation_writeback_score_passes_through_eval_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Build heterogeneous severities so collapsing them all to 0.0 would
    # be detectable.
    failures = [
        FailedSpan(
            span_id=f"{i:016x}",
            fault_class="malformed_tool_output",
            eval_score=EvalScore(passed=False, score=0.42 + 0.1 * i, reason=f"f{i}"),
            trace_excerpt=f"trace {i}",
        )
        for i in range(3)
    ]
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=1))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    await run_clustering(failures, phoenix_client=client)
    scores = {
        entry.span_id: entry.result.score
        for entry in cast(_RecordingSpans, client.spans).batches[0]
    }
    assert scores == {f.span_id: f.eval_score.score for f in failures}


async def test_annotation_explanation_carries_cluster_root_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(3)
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=1))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    result = await run_clustering(failures, phoenix_client=client)
    explanations = {
        entry.result.explanation for entry in cast(_RecordingSpans, client.spans).batches[0]
    }
    assert explanations == {c.root_cause for c in result.clusters}


async def test_annotation_metadata_carries_fault_classes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(3)
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=1))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    client = _RecordingClient()
    await run_clustering(failures, phoenix_client=client)
    for entry in cast(_RecordingSpans, client.spans).batches[0]:
        assert "fault_classes" in entry.metadata
        assert isinstance(entry.metadata["fault_classes"], list)


async def test_annotation_writeback_failure_raises_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from phoenix_audit_agent.judge.clustering import AnnotationWritebackError

    failures = _failures(3)
    stub = _StubClusterer(_scripted_partition(failures, cluster_count=1))
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)

    class _RejectingSpans(_SpansNamespace):
        async def get_span(self, span_id: str) -> Any:
            raise NotImplementedError

        async def log_span_annotations(self, *, span_annotations: list[Any]) -> None:
            raise RuntimeError("Phoenix 503")

    class _RejectingClient(PhoenixClient):
        spans: _SpansNamespace

        def __init__(self) -> None:
            self.spans = _RejectingSpans()

    with pytest.raises(AnnotationWritebackError) as exc:
        await run_clustering(failures, phoenix_client=_RejectingClient())
    assert exc.value.attempted_count == len(failures)
    assert exc.value.cluster_set.total_failures == len(failures)
