"""LLM-as-clusterer over failed spans + Phoenix annotation writeback.

JUDGE_LLM is locked to ``gemini-3.5-flash`` (ADR-007). The clusterer
groups 1-72 failed `FailedSpan` records into 1-5 root-cause `FailureCluster`s
and writes one ``chaoslab_failure_cluster`` annotation back per span via
Phoenix's `log_span_annotations` API.
"""

from __future__ import annotations

import json
import secrets
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge._models import FailedSpan
from chaoslab_agent.judge.clustering_prompt import CLUSTER_PROMPT, RETRY_PROMPT
from chaoslab_agent.judge.rubrics._base import FaultClass, PhoenixClient
from chaoslab_agent.judge.rubrics._llm import get_judge_llm

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FailureCluster(BaseModel):
    """One root-cause cluster the LLM groups failures into."""

    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(pattern=r"^cluster_[a-z0-9]{8}$")
    root_cause: str = Field(min_length=1)
    failure_count: int = Field(ge=1)
    span_ids: list[str] = Field(min_length=1)
    fault_classes: list[FaultClass] = Field(min_length=1)

    @model_validator(mode="after")
    def _count_matches_span_ids(self) -> FailureCluster:
        if self.failure_count != len(self.span_ids):
            msg = f"failure_count={self.failure_count} but len(span_ids)={len(self.span_ids)}"
            raise ValueError(msg)
        return self


class FailureClusterSet(BaseModel):
    """Validated partition of failed spans into 1-5 clusters."""

    clusters: list[FailureCluster] = Field(min_length=1, max_length=5)
    total_failures: int = Field(ge=1)
    # ADR-007: JUDGE_LLM clusterer is locked to gemini-3.5-flash.
    clusterer_model: Literal["gemini-3.5-flash"] = "gemini-3.5-flash"

    @model_validator(mode="after")
    def _mutually_exclusive_partition(self) -> FailureClusterSet:
        seen: set[str] = set()
        for c in self.clusters:
            for sid in c.span_ids:
                if sid in seen:
                    msg = f"span_id {sid} assigned to multiple clusters"
                    raise ValueError(msg)
                seen.add(sid)
        if sum(c.failure_count for c in self.clusters) != self.total_failures:
            msg = "cluster failure_counts do not sum to total_failures"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ClusteringError(RuntimeError):
    """LLM clusterer produced unrecoverable output (after retries)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def new_cluster_id() -> str:
    """Mint an 8-hex-char cluster id (matches the FailureCluster regex)."""
    return f"cluster_{secrets.token_hex(4)}"


def _failures_payload(failures: list[FailedSpan]) -> str:
    return json.dumps(
        [
            {
                "span_id": f.span_id,
                "fault_class": f.fault_class,
                "verdict": "FAIL",
                "judge_reason": f.eval_score.reason,
                "trace_excerpt": f.trace_excerpt,
            }
            for f in failures
        ]
    )


async def _call_clusterer(prompt: str) -> str:
    """Send the prompt to the JUDGE_LLM (gemini-3.5-flash) and return the
    raw string response.

    Kept as a module-level function so tests can monkeypatch the Gemini
    HTTP boundary without touching `LLM` construction (story-6.1 lazy
    singleton applies here too).
    """
    llm = get_judge_llm()
    # phoenix.evals.LLM.generate_text is the single-prompt convenience that
    # returns the model's raw response body — exactly what the clusterer
    # needs to parse as JSON.
    response = await llm.agenerate_text(prompt=prompt, temperature=0.1)  # ty: ignore[unresolved-attribute]
    return str(response)


# ---------------------------------------------------------------------------
# Annotation writeback
# ---------------------------------------------------------------------------


class _AnnotationResult(BaseModel):
    label: str
    score: float
    explanation: str


class _SpanAnnotation(BaseModel):
    """Mirror of phoenix.client.resources.spans.SpanAnnotationData.

    The Phoenix SDK's BaseModel is constructed positionally; for testability
    + duck-typing we mint a local equivalent and rely on `log_span_annotations`
    accepting any object exposing the same attribute surface.
    """

    name: str
    span_id: str
    annotator_kind: str
    result: _AnnotationResult
    metadata: dict[str, Any] = Field(default_factory=dict)


def _build_annotations(cluster_set: FailureClusterSet) -> list[_SpanAnnotation]:
    return [
        _SpanAnnotation(
            name="chaoslab_failure_cluster",
            span_id=span_id,
            annotator_kind="LLM",
            result=_AnnotationResult(
                label=cluster.cluster_id,
                score=0.0,
                explanation=cluster.root_cause,
            ),
            metadata={"fault_classes": list(cluster.fault_classes)},
        )
        for cluster in cluster_set.clusters
        for span_id in cluster.span_ids
    ]


async def _write_annotations(client: PhoenixClient, cluster_set: FailureClusterSet) -> None:
    annotations = _build_annotations(cluster_set)
    # PhoenixClient's spans Protocol is intentionally narrow; the real
    # AsyncClient.spans namespace also exposes `log_span_annotations`
    # (architecture/02 §4.4). Cast to Any to delegate at the boundary.
    await cast(Any, client.spans).log_span_annotations(span_annotations=annotations)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_clustering(
    failures: list[FailedSpan],
    phoenix_client: PhoenixClient,
    *,
    max_retries: int = 2,
) -> FailureClusterSet:
    """Group failures into 1-5 root-cause clusters and write annotations.

    Raises:
        ClusteringError: if the clusterer's response cannot be parsed and
            validated after ``max_retries`` corrective re-prompts, or the
            cluster count exceeds Settings.MAX_CLUSTERS.
    """
    if not failures:
        msg = "run_clustering called with empty failure set"
        raise ClusteringError(msg)

    settings = get_settings()
    if settings.JUDGE_LLM != "gemini-3.5-flash":
        msg = (
            f"ADR-007 invariant violated: JUDGE_LLM={settings.JUDGE_LLM!r} but "
            "clusterer is locked to 'gemini-3.5-flash'"
        )
        raise ClusteringError(msg)

    failures_json = _failures_payload(failures)
    prompt = CLUSTER_PROMPT.format(n_failures=len(failures), failures_json=failures_json)

    cluster_set = await _attempt_clustering(
        failures=failures,
        initial_prompt=prompt,
        max_retries=max_retries,
        max_clusters=settings.MAX_CLUSTERS,
    )

    await _write_annotations(phoenix_client, cluster_set)
    return cluster_set


async def _attempt_clustering(
    failures: list[FailedSpan],
    initial_prompt: str,
    max_retries: int,
    max_clusters: int,
) -> FailureClusterSet:
    """Drive the JSON-decode retry loop; semantic errors are non-retriable.

    Re-prompting on a parse failure can recover (the LLM emitted prose by
    mistake). Re-prompting on a partition-invariant violation will not —
    the LLM's reasoning was the problem, not its formatting.
    """
    prompt = initial_prompt
    last_decode_err: json.JSONDecodeError | None = None
    for attempt in range(max_retries + 1):
        raw = await _call_clusterer(prompt)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_decode_err = exc
            if attempt == max_retries:
                break
            prompt = f"{RETRY_PROMPT}\n\n{initial_prompt}"
            continue
        try:
            return _validate_body(body, failures=failures, max_clusters=max_clusters)
        except ValueError as exc:
            msg = f"clusterer returned invalid partition: {exc}"
            raise ClusteringError(msg) from exc
    msg = f"clusterer returned malformed JSON after {max_retries} retries"
    raise ClusteringError(msg) from last_decode_err


def _validate_body(
    body: Any,
    *,
    failures: list[FailedSpan],
    max_clusters: int,
) -> FailureClusterSet:
    clusters_raw = body.get("clusters", []) if isinstance(body, dict) else []
    if not clusters_raw:
        msg = "clusterer returned no clusters"
        raise ValueError(msg)
    if len(clusters_raw) > max_clusters:
        msg = (
            f"clusterer returned {len(clusters_raw)} clusters which "
            f"exceeds MAX_CLUSTERS={max_clusters}"
        )
        raise ValueError(msg)
    return FailureClusterSet(
        clusters=[FailureCluster(**c) for c in clusters_raw],
        total_failures=len(failures),
    )


__all__ = [
    "CLUSTER_PROMPT",
    "ClusteringError",
    "FailureCluster",
    "FailureClusterSet",
    "new_cluster_id",
    "run_clustering",
]
