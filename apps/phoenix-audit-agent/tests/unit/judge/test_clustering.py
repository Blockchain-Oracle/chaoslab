"""Schema + run_clustering tests for the LLM-as-clusterer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge._models import FailedSpan
from phoenix_audit_agent.judge.clustering import (
    CLUSTER_PROMPT,
    ClusteringError,
    FailureCluster,
    FailureClusterSet,
    new_cluster_id,
    run_clustering,
)
from phoenix_audit_agent.judge.rubrics._base import (
    EvalScore,
    FaultClass,
    PhoenixClient,
    _SpansNamespace,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _score(passed: bool = False) -> EvalScore:
    return EvalScore(
        passed=passed,
        score=0.0 if not passed else 1.0,
        reason="agent confabulated when tool returned garbage",
    )


def _failures(n: int = 15) -> list[FailedSpan]:
    fault_cycle: list[FaultClass] = (
        ["malformed_tool_output"] * 5
        + ["prompt_injection"] * 4
        + ["context_poisoning"] * 4
        + ["latency_spike"] * 2
    )
    return [
        FailedSpan(
            span_id=f"{i:016x}",
            fault_class=fault_cycle[i],
            eval_score=_score(),
            trace_excerpt=f"input #{i} → output #{i}",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# FailureCluster schema
# ---------------------------------------------------------------------------


def test_failure_cluster_accepts_valid_shape() -> None:
    c = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=5,
        span_ids=["s1", "s2", "s3", "s4", "s5"],
        fault_classes=["malformed_tool_output"],
    )
    assert c.failure_count == 5
    assert len(c.span_ids) == 5


def test_failure_cluster_rejects_invalid_cluster_id() -> None:
    with pytest.raises(ValidationError):
        FailureCluster(
            cluster_id="invalid_id",
            root_cause="x",
            failure_count=1,
            span_ids=["s1"],
            fault_classes=["malformed_tool_output"],
        )


def test_failure_cluster_rejects_uppercase_cluster_id() -> None:
    with pytest.raises(ValidationError):
        FailureCluster(
            cluster_id="cluster_A3F7B2C1",
            root_cause="x",
            failure_count=1,
            span_ids=["s1"],
            fault_classes=["malformed_tool_output"],
        )


def test_failure_cluster_rejects_zero_failure_count() -> None:
    with pytest.raises(ValidationError):
        FailureCluster(
            cluster_id="cluster_a3f7b2c1",
            root_cause="x",
            failure_count=0,
            span_ids=[],
            fault_classes=["malformed_tool_output"],
        )


def test_failure_cluster_rejects_unknown_fault_class() -> None:
    with pytest.raises(ValidationError):
        FailureCluster(
            cluster_id="cluster_a3f7b2c1",
            root_cause="x",
            failure_count=1,
            span_ids=["s1"],
            fault_classes=["unknown_class"],  # ty: ignore[invalid-argument-type]
        )


def test_failure_cluster_rejects_count_span_ids_mismatch() -> None:
    with pytest.raises(ValidationError, match="failure_count"):
        FailureCluster(
            cluster_id="cluster_a3f7b2c1",
            root_cause="x",
            failure_count=3,
            span_ids=["s1", "s2"],
            fault_classes=["malformed_tool_output"],
        )


def test_new_cluster_id_matches_pattern() -> None:
    cid = new_cluster_id()
    assert len(cid) == len("cluster_") + 8
    assert cid.startswith("cluster_")
    # Re-validate via the pydantic field's regex by round-tripping.
    FailureCluster(
        cluster_id=cid,
        root_cause="x",
        failure_count=1,
        span_ids=["s1"],
        fault_classes=["malformed_tool_output"],
    )


# ---------------------------------------------------------------------------
# FailureClusterSet partition invariant
# ---------------------------------------------------------------------------


def test_failure_cluster_set_accepts_partition() -> None:
    s = FailureClusterSet(
        clusters=[
            FailureCluster(
                cluster_id="cluster_aaaaaaaa",
                root_cause="r1",
                failure_count=2,
                span_ids=["s1", "s2"],
                fault_classes=["malformed_tool_output"],
            ),
            FailureCluster(
                cluster_id="cluster_bbbbbbbb",
                root_cause="r2",
                failure_count=1,
                span_ids=["s3"],
                fault_classes=["prompt_injection"],
            ),
        ],
        total_failures=3,
    )
    assert s.clusterer_model == "gemini-3.5-flash"


def test_failure_cluster_set_rejects_duplicate_span_id_across_clusters() -> None:
    with pytest.raises(ValidationError, match="multiple clusters"):
        FailureClusterSet(
            clusters=[
                FailureCluster(
                    cluster_id="cluster_aaaaaaaa",
                    root_cause="r1",
                    failure_count=1,
                    span_ids=["s1"],
                    fault_classes=["malformed_tool_output"],
                ),
                FailureCluster(
                    cluster_id="cluster_bbbbbbbb",
                    root_cause="r2",
                    failure_count=1,
                    span_ids=["s1"],
                    fault_classes=["prompt_injection"],
                ),
            ],
            total_failures=2,
        )


def test_failure_cluster_set_rejects_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="sum to total_failures"):
        FailureClusterSet(
            clusters=[
                FailureCluster(
                    cluster_id="cluster_aaaaaaaa",
                    root_cause="r1",
                    failure_count=2,
                    span_ids=["s1", "s2"],
                    fault_classes=["malformed_tool_output"],
                ),
            ],
            total_failures=5,
        )


def test_failure_cluster_set_caps_at_five_clusters() -> None:
    clusters = [
        FailureCluster(
            cluster_id=f"cluster_{i:08x}",
            root_cause=f"r{i}",
            failure_count=1,
            span_ids=[f"s{i}"],
            fault_classes=["malformed_tool_output"],
        )
        for i in range(6)
    ]
    with pytest.raises(ValidationError):
        FailureClusterSet(clusters=clusters, total_failures=6)


def test_failure_cluster_set_rejects_empty_clusters() -> None:
    with pytest.raises(ValidationError):
        FailureClusterSet(clusters=[], total_failures=0)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------


def test_cluster_prompt_carries_required_placeholders() -> None:
    # Template uses {n_failures} and {failures_json}; the schema example
    # block uses doubled braces so str.format only interpolates the two
    # named fields the runtime fills in.
    assert "{n_failures}" in CLUSTER_PROMPT
    assert "{failures_json}" in CLUSTER_PROMPT
    assert "Group these failures into 1-5 distinct CLUSTERS" in CLUSTER_PROMPT
    assert "PhoenixAudit" in CLUSTER_PROMPT


def test_cluster_prompt_formats_without_keyerror() -> None:
    # Doubled braces in the schema example must survive str.format so we
    # don't accidentally try to interpolate the JSON example keys.
    rendered = CLUSTER_PROMPT.format(n_failures=15, failures_json="[]")
    assert "15" in rendered
    assert '"cluster_id"' in rendered


# ---------------------------------------------------------------------------
# run_clustering — Gemini boundary stubbed via the clusterer factory
# ---------------------------------------------------------------------------


@dataclass
class _FakeSpan:
    attributes: dict[str, Any] = field(default_factory=dict)


class _RecordingSpans(_SpansNamespace):
    def __init__(self) -> None:
        self.annotations: list[list[Any]] = []

    async def get_span(self, span_id: str) -> Any:
        raise NotImplementedError

    async def log_span_annotations(self, *, span_annotations: list[Any]) -> None:
        self.annotations.append(list(span_annotations))


class _RecordingClient(PhoenixClient):
    spans: _SpansNamespace

    def __init__(self) -> None:
        self.spans = _RecordingSpans()


def _valid_partition_json(failures: list[FailedSpan]) -> str:
    half = len(failures) // 2
    a, b = failures[:half], failures[half:]
    return json.dumps(
        {
            "clusters": [
                {
                    "cluster_id": "cluster_aaaaaaaa",
                    "root_cause": "no tool-output schema validation",
                    "failure_count": len(a),
                    "span_ids": [s.span_id for s in a],
                    "fault_classes": sorted({s.fault_class for s in a}),
                },
                {
                    "cluster_id": "cluster_bbbbbbbb",
                    "root_cause": "treats retrieved context as authoritative",
                    "failure_count": len(b),
                    "span_ids": [s.span_id for s in b],
                    "fault_classes": sorted({s.fault_class for s in b}),
                },
            ]
        }
    )


class _StubClusterer:
    """Stand-in for the Gemini round-trip — returns a scripted JSON body."""

    def __init__(self, responses: list[str]) -> None:
        self._queue = list(responses)
        self.calls: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._queue.pop(0)


async def test_run_clustering_returns_valid_partition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(10)
    stub = _StubClusterer([_valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    result = await run_clustering(failures, phoenix_client=_RecordingClient())
    assert isinstance(result, FailureClusterSet)
    assert 1 <= len(result.clusters) <= 5
    assert result.total_failures == 10
    all_ids = {sid for cluster in result.clusters for sid in cluster.span_ids}
    assert all_ids == {s.span_id for s in failures}


async def test_run_clustering_retries_on_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(4)
    stub = _StubClusterer(["not-json-at-all", _valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    result = await run_clustering(failures, phoenix_client=_RecordingClient())
    assert isinstance(result, FailureClusterSet)
    # First call was the initial prompt; second was the corrective re-prompt.
    assert len(stub.calls) == 2
    assert "previous output was not valid JSON" in stub.calls[1]


async def test_run_clustering_raises_after_retry_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(4)
    stub = _StubClusterer(["bad", "still bad", "and again"])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="malformed JSON"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_run_clustering_raises_on_zero_clusters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    stub = _StubClusterer([json.dumps({"clusters": []})])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_run_clustering_raises_when_cluster_count_exceeds_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(6)
    over_max = {
        "clusters": [
            {
                "cluster_id": f"cluster_{i:08x}",
                "root_cause": f"r{i}",
                "failure_count": 1,
                "span_ids": [failures[i].span_id],
                "fault_classes": [failures[i].fault_class],
            }
            for i in range(6)
        ]
    }
    stub = _StubClusterer([json.dumps(over_max)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="MAX_CLUSTERS"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_run_clustering_clusterer_model_is_locked_to_flash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(4)
    stub = _StubClusterer([_valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    result = await run_clustering(failures, phoenix_client=_RecordingClient())
    assert result.clusterer_model == "gemini-3.5-flash"


# ---------------------------------------------------------------------------
# Rubric payload contract (round-2)
# ---------------------------------------------------------------------------


async def test_run_clustering_payload_carries_all_five_rubric_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(4)
    stub = _StubClusterer([_valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    await run_clustering(failures, phoenix_client=_RecordingClient())
    rendered_prompt = stub.calls[0]
    # The failures JSON is embedded between <failures> tags by the prompt.
    payload_start = rendered_prompt.index("<failures>") + len("<failures>")
    payload_end = rendered_prompt.index("</failures>")
    payload = json.loads(rendered_prompt[payload_start:payload_end])
    assert len(payload) == len(failures)
    for entry, source in zip(payload, failures, strict=True):
        assert entry["span_id"] == source.span_id
        assert entry["fault_class"] == source.fault_class
        assert entry["verdict"] == "FAIL"
        assert entry["judge_reason"] == source.eval_score.reason
        assert entry["trace_excerpt"] == source.trace_excerpt


# ---------------------------------------------------------------------------
# Boundary + semantic-non-retriable + ADR-007 (round-2)
# ---------------------------------------------------------------------------


async def test_exactly_five_clusters_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    failures = _failures(5)
    body = {
        "clusters": [
            {
                "cluster_id": f"cluster_{i:08x}",
                "root_cause": f"r{i}",
                "failure_count": 1,
                "span_ids": [failures[i].span_id],
                "fault_classes": [failures[i].fault_class],
            }
            for i in range(5)
        ]
    }
    stub = _StubClusterer([json.dumps(body)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    result = await run_clustering(failures, phoenix_client=_RecordingClient())
    assert len(result.clusters) == 5


async def test_empty_failures_raises_immediately() -> None:
    with pytest.raises(ClusteringError, match="empty failure set"):
        await run_clustering([], phoenix_client=_RecordingClient())


async def test_adr_007_runtime_guard_rejects_wrong_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(
        c,
        "get_settings",
        lambda: type("S", (), {"JUDGE_LLM": "claude-3-haiku", "MAX_CLUSTERS": 5})(),  # noqa: PLW0108
    )
    with pytest.raises(ClusteringError, match="ADR-007"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_adr_007_runtime_guard_accepts_flash_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Settings is locked but the runtime guard uses startswith so a future
    # `gemini-3.5-flash-002` revision works without code change.
    failures = _failures(2)
    stub = _StubClusterer([_valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    monkeypatch.setattr(
        c,
        "get_settings",
        lambda: type("S", (), {"JUDGE_LLM": "gemini-3.5-flash-002", "MAX_CLUSTERS": 5})(),  # noqa: PLW0108
    )
    result = await run_clustering(failures, phoenix_client=_RecordingClient())
    assert isinstance(result, FailureClusterSet)


async def test_duplicate_span_id_in_failures_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    f = _failures(1)[0]
    with pytest.raises(ClusteringError, match="duplicate span_id"):
        await run_clustering([f, f], phoenix_client=_RecordingClient())


async def test_hallucinated_span_id_in_partition_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(3)
    body = {
        "clusters": [
            {
                "cluster_id": "cluster_aaaaaaaa",
                "root_cause": "r",
                "failure_count": 3,
                # Replace one real span_id with a hallucinated one.
                "span_ids": [failures[0].span_id, failures[1].span_id, "f" * 16],
                "fault_classes": ["malformed_tool_output"],
            }
        ]
    }
    stub = _StubClusterer([json.dumps(body)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="span_ids do not match"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_non_dict_json_body_raises_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    stub = _StubClusterer([json.dumps(["not", "a", "dict"])])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="non-dict"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_missing_clusters_key_raises_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    stub = _StubClusterer([json.dumps({"oops": []})])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="missing required 'clusters' key"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_semantic_violation_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    bad = json.dumps({"clusters": []})
    stub = _StubClusterer([bad, _valid_partition_json(failures)])
    import phoenix_audit_agent.judge.clustering as c

    monkeypatch.setattr(c, "_call_clusterer", stub)
    with pytest.raises(ClusteringError, match="no clusters"):
        await run_clustering(failures, phoenix_client=_RecordingClient())
    assert len(stub.calls) == 1  # NOT retried


# ---------------------------------------------------------------------------
# Frozen + cluster_id uniqueness (round-2)
# ---------------------------------------------------------------------------


def test_failure_cluster_set_is_frozen() -> None:
    s = FailureClusterSet(
        clusters=[
            FailureCluster(
                cluster_id="cluster_aaaaaaaa",
                root_cause="r",
                failure_count=1,
                span_ids=["s1"],
                fault_classes=["malformed_tool_output"],
            )
        ],
        total_failures=1,
    )
    with pytest.raises(ValidationError):
        s.total_failures = 99  # type: ignore[misc]


def test_failure_cluster_set_rejects_duplicate_cluster_ids() -> None:
    with pytest.raises(ValidationError, match="cluster_id"):
        FailureClusterSet(
            clusters=[
                FailureCluster(
                    cluster_id="cluster_aaaaaaaa",
                    root_cause="r1",
                    failure_count=1,
                    span_ids=["s1"],
                    fault_classes=["malformed_tool_output"],
                ),
                FailureCluster(
                    cluster_id="cluster_aaaaaaaa",
                    root_cause="r2",
                    failure_count=1,
                    span_ids=["s2"],
                    fault_classes=["prompt_injection"],
                ),
            ],
            total_failures=2,
        )


def test_failure_cluster_immutable_attribute_set_fails() -> None:
    c = FailureCluster(
        cluster_id="cluster_aaaaaaaa",
        root_cause="r",
        failure_count=1,
        span_ids=["s1"],
        fault_classes=["malformed_tool_output"],
    )
    with pytest.raises(ValidationError):
        c.failure_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Typed Gemini exceptions + empty response (round-2)
# ---------------------------------------------------------------------------


async def test_non_retriable_gemini_exception_raises_clustering_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    import phoenix_audit_agent.judge.clustering as c

    class _BoomLLM:
        async def async_generate_text(self, *, prompt: str, temperature: float) -> str:
            raise RuntimeError("Quota exhausted")

    monkeypatch.setattr(c, "get_judge_llm", lambda: _BoomLLM())  # noqa: PLW0108
    # Don't monkeypatch _call_clusterer — we want the real path to surface.
    with pytest.raises(ClusteringError, match="non-retriable"):
        await run_clustering(failures, phoenix_client=_RecordingClient())


async def test_empty_gemini_response_raises_clustering_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failures = _failures(2)
    import phoenix_audit_agent.judge.clustering as c

    class _EmptyLLM:
        async def async_generate_text(self, *, prompt: str, temperature: float) -> str:
            return ""

    monkeypatch.setattr(c, "get_judge_llm", lambda: _EmptyLLM())  # noqa: PLW0108
    with pytest.raises(ClusteringError, match="empty response"):
        await run_clustering(failures, phoenix_client=_RecordingClient())
