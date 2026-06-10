"""LLM-as-clusterer over failed spans with Phoenix annotation writeback."""

from __future__ import annotations

import json
import logging
import secrets
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge._models import FailedSpan
from phoenix_audit_agent.judge.clustering_prompt import CLUSTER_PROMPT, RETRY_PROMPT
from phoenix_audit_agent.judge.clustering_writeback import (
    AnnotationWritebackError,
    write_annotations,
)
from phoenix_audit_agent.judge.rubrics._base import FaultClass, PhoenixClient
from phoenix_audit_agent.judge.rubrics._llm import get_judge_llm

logger = logging.getLogger(__name__)

# Truncate raw clusterer payloads in logs so a 5MB Gemini response can't
# blow up the log shipper but a debugger still has the head of the body.
_RAW_LOG_LIMIT = 500

# String prefix the runtime guard accepts. The Literal on
# FailureClusterSet.clusterer_model is tighter (exact match); the prefix
# check exists only to surface a useful error before pydantic does.
_JUDGE_MODEL_PREFIX = "gemini-3.5-flash"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FailureCluster(BaseModel):
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
    # Frozen so a caller can't bypass the partition invariant by mutating
    # `.clusters` post-construction (the list itself is still mutable in
    # Python; the frozen flag blocks Pydantic-managed reassignment).
    model_config = ConfigDict(frozen=True)

    clusters: list[FailureCluster] = Field(min_length=1, max_length=5)
    total_failures: int = Field(ge=1)
    clusterer_model: Literal["gemini-3.5-flash"] = "gemini-3.5-flash"

    @model_validator(mode="after")
    def _mutually_exclusive_partition(self) -> FailureClusterSet:
        seen_spans: set[str] = set()
        seen_cluster_ids: set[str] = set()
        for c in self.clusters:
            if c.cluster_id in seen_cluster_ids:
                msg = f"cluster_id {c.cluster_id} appears more than once"
                raise ValueError(msg)
            seen_cluster_ids.add(c.cluster_id)
            for sid in c.span_ids:
                if sid in seen_spans:
                    msg = f"span_id {sid} assigned to multiple clusters"
                    raise ValueError(msg)
                seen_spans.add(sid)
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
    # Module-level so tests can monkeypatch the Gemini boundary without
    # touching the lazy LLM singleton. Vertex AI raises typed Google API
    # exceptions on quota/safety/auth; bubble them as ClusteringError so
    # the retry loop doesn't waste tokens re-prompting an exhausted quota.
    llm = get_judge_llm()
    try:
        response = await llm.async_generate_text(prompt=prompt, temperature=0.1)
    except Exception as exc:
        if _is_retriable_decode_failure(exc):
            raise
        msg = f"Gemini call failed (non-retriable): {type(exc).__name__}: {exc}"
        raise ClusteringError(msg) from exc
    if not response or not str(response).strip():
        msg = "Gemini returned an empty response (likely safety-block or quota)"
        raise ClusteringError(msg)
    return str(response)


def _is_retriable_decode_failure(exc: BaseException) -> bool:
    # Only JSON-decode failures of the LLM body should drive a re-prompt;
    # everything that escapes the SDK (auth, quota, network) is terminal.
    return isinstance(exc, json.JSONDecodeError)


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
        ClusteringError: malformed JSON after retries, partition invariant
            violation, ADR-007 model mismatch, or a non-retriable Gemini
            exception (quota / safety / auth).
        AnnotationWritebackError: clustering succeeded but Phoenix rejected
            the annotation batch — `attempted_count` and `cluster_set` are
            preserved on the exception so the caller can decide whether to
            retry the writeback alone.
    """
    if not failures:
        msg = "run_clustering called with empty failure set"
        raise ClusteringError(msg)

    settings = get_settings()
    if not settings.JUDGE_LLM.startswith(_JUDGE_MODEL_PREFIX):
        msg = (
            f"ADR-007 invariant violated: JUDGE_LLM={settings.JUDGE_LLM!r} but "
            f"clusterer requires the {_JUDGE_MODEL_PREFIX!r} family"
        )
        raise ClusteringError(msg)

    failures_by_span_id = {f.span_id: f for f in failures}
    if len(failures_by_span_id) != len(failures):
        msg = "duplicate span_id in failures input"
        raise ClusteringError(msg)

    failures_json = _failures_payload(failures)
    prompt = CLUSTER_PROMPT.format(n_failures=len(failures), failures_json=failures_json)

    cluster_set = await _attempt_clustering(
        failures=failures,
        initial_prompt=prompt,
        max_retries=max_retries,
        max_clusters=settings.MAX_CLUSTERS,
    )

    await write_annotations(phoenix_client, cluster_set, failures_by_span_id)
    return cluster_set


async def _attempt_clustering(
    failures: list[FailedSpan],
    initial_prompt: str,
    max_retries: int,
    max_clusters: int,
) -> FailureClusterSet:
    # Re-prompting can recover from a parse failure (LLM emitted prose); it
    # cannot recover from a partition-invariant violation, so semantic
    # errors raise immediately.
    prompt = initial_prompt
    last_decode_err: json.JSONDecodeError | None = None
    last_raw: str = ""
    for attempt in range(max_retries + 1):
        raw = await _call_clusterer(prompt)
        last_raw = raw
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_decode_err = exc
            logger.warning(
                "clusterer emitted non-JSON on attempt %d/%d: %s",
                attempt + 1,
                max_retries + 1,
                raw[:_RAW_LOG_LIMIT],
            )
            if attempt == max_retries:
                break
            prompt = f"{RETRY_PROMPT}\n\n{initial_prompt}"
            continue
        try:
            return _validate_body(body, failures=failures, max_clusters=max_clusters)
        except ValueError as exc:
            logger.warning(
                "clusterer returned invalid partition: %s | raw=%s",
                exc,
                raw[:_RAW_LOG_LIMIT],
            )
            msg = f"clusterer returned invalid partition: {exc}"
            raise ClusteringError(msg) from exc
    logger.error(
        "clusterer exhausted %d retries; last raw payload: %s",
        max_retries,
        last_raw[:_RAW_LOG_LIMIT],
    )
    msg = f"clusterer returned malformed JSON after {max_retries} retries"
    raise ClusteringError(msg) from last_decode_err


def _validate_body(
    body: Any,
    *,
    failures: list[FailedSpan],
    max_clusters: int,
) -> FailureClusterSet:
    if not isinstance(body, dict):
        msg = (
            f"clusterer returned non-dict JSON ({type(body).__name__}); "
            "expected an object with a 'clusters' key"
        )
        raise ValueError(msg)
    if "clusters" not in body:
        msg = "clusterer response missing required 'clusters' key"
        raise ValueError(msg)
    clusters_raw = body["clusters"]
    if not clusters_raw:
        msg = "clusterer returned no clusters"
        raise ValueError(msg)
    if len(clusters_raw) > max_clusters:
        msg = (
            f"clusterer returned {len(clusters_raw)} clusters which "
            f"exceeds MAX_CLUSTERS={max_clusters}"
        )
        raise ValueError(msg)
    cluster_set = FailureClusterSet(
        clusters=[FailureCluster(**c) for c in clusters_raw],
        total_failures=len(failures),
    )
    # The pydantic partition check guarantees mutual exclusion among the
    # span_ids the LLM emitted; it does NOT guarantee those ids match the
    # input set. Without this check, hallucinated/swapped span_ids would
    # silently land in the audit annotations.
    input_spans = {f.span_id for f in failures}
    emitted_spans = {sid for c in cluster_set.clusters for sid in c.span_ids}
    if emitted_spans != input_spans:
        missing = input_spans - emitted_spans
        extra = emitted_spans - input_spans
        msg = (
            f"partition span_ids do not match input; "
            f"missing={sorted(missing)} unexpected={sorted(extra)}"
        )
        raise ValueError(msg)
    return cluster_set


__all__ = [
    "CLUSTER_PROMPT",
    "AnnotationWritebackError",
    "ClusteringError",
    "FailureCluster",
    "FailureClusterSet",
    "new_cluster_id",
    "run_clustering",
]
