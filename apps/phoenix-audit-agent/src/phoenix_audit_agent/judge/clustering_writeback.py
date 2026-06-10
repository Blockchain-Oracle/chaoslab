"""Phoenix annotation writeback for the LLM-as-clusterer output."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

from phoenix_audit_agent.errors import PhoenixAuditError
from phoenix_audit_agent.judge.rubrics._base import PhoenixClient

if TYPE_CHECKING:
    from phoenix_audit_agent.judge._models import FailedSpan
    from phoenix_audit_agent.judge.clustering import FailureClusterSet

logger = logging.getLogger(__name__)


class AnnotationWritebackError(PhoenixAuditError, RuntimeError):
    """Phoenix rejected the annotation batch — audit may be partially written."""

    def __init__(
        self,
        cluster_set: FailureClusterSet,
        attempted_count: int,
        cause: BaseException,
    ) -> None:
        self.cluster_set = cluster_set
        self.attempted_count = attempted_count
        super().__init__(
            f"Phoenix rejected {attempted_count} phoenix_audit_failure_cluster "
            f"annotations: {cause!r}"
        )


class _AnnotationResult(BaseModel):
    label: str
    score: float
    explanation: str


# TODO(post-S6.4): swap to phoenix.client.resources.spans.SpanAnnotationData
# once construction ergonomics permit; Phoenix's SDK builds it positionally.
class _SpanAnnotation(BaseModel):
    """Duck-types phoenix.client SpanAnnotationData."""

    name: str
    span_id: str
    annotator_kind: str
    result: _AnnotationResult
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_annotations(
    cluster_set: FailureClusterSet,
    failures_by_span_id: dict[str, FailedSpan],
) -> list[_SpanAnnotation]:
    return [
        _SpanAnnotation(
            name="phoenix_audit_failure_cluster",
            span_id=span_id,
            annotator_kind="LLM",
            result=_AnnotationResult(
                label=cluster.cluster_id,
                # Pass through the rubric's actual severity so the
                # Resilience Curve can surface "marginal vs catastrophic"
                # rather than collapsing every failure to 0.0.
                score=failures_by_span_id[span_id].eval_score.score,
                explanation=cluster.root_cause,
            ),
            metadata={"fault_classes": list(cluster.fault_classes)},
        )
        for cluster in cluster_set.clusters
        for span_id in cluster.span_ids
    ]


async def write_annotations(
    client: PhoenixClient,
    cluster_set: FailureClusterSet,
    failures_by_span_id: dict[str, FailedSpan],
) -> None:
    annotations = build_annotations(cluster_set, failures_by_span_id)
    # PhoenixClient Protocol is intentionally narrow; AsyncClient.spans
    # also exposes `log_span_annotations` (architecture/02 §4.4).
    try:
        await cast(Any, client.spans).log_span_annotations(span_annotations=annotations)
    except Exception as exc:
        logger.exception(
            "phoenix_audit_failure_cluster writeback failed",
            extra={
                "attempted_count": len(annotations),
                "cluster_ids": [c.cluster_id for c in cluster_set.clusters],
            },
        )
        raise AnnotationWritebackError(
            cluster_set=cluster_set,
            attempted_count=len(annotations),
            cause=exc,
        ) from exc


__all__ = ["AnnotationWritebackError", "write_annotations"]
