"""POST /runs/{run_id}/clusters/{cluster_id}/review — the officer review
layer (story-9.21).

The review persists on the RUN RECORD first (the durable, signed-artifact-
adjacent trail); the Phoenix human annotation is contained and its outcome
DISCLOSED in the response — a Phoenix outage never loses a review and never
pretends the annotation landed.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.storage.models import ClusterReview, ReviewVerdict, RunCompletion
from phoenix_audit_agent.storage.runs import get_run_store, persist_run_completion

_log = structlog.get_logger(__name__)

router = APIRouter()


async def annotate_officer_verdict(
    *, span_id: str, verdict: str, note: str | None, cluster_id: str
) -> bool:
    """Write the HUMAN annotation onto the cluster's exemplar span (module
    attribute = test seam). Returns False on any failure — contained; the
    caller discloses the outcome instead of failing the review."""
    from phoenix_audit_agent.phoenix_tools.write_annotation import write_span_annotation

    try:
        await write_span_annotation(
            span_id,
            1.0 if verdict == "confirmed" else 0.0,
            note or f"officer verdict: {verdict}",
            cluster_id=cluster_id,
            annotator="human",
            label=verdict,
        )
    except Exception:
        _log.error(
            "officer_annotation_failed", span_id=span_id, cluster_id=cluster_id, exc_info=True
        )
        return False
    return True


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: ReviewVerdict
    note: str | None = Field(default=None, max_length=500)


class ReviewResponse(BaseModel):
    review: ClusterReview
    # False => the review IS saved but the Phoenix annotation did not land —
    # the UI can offer a retry; nothing pretends (CLAUDE.md pattern #4).
    phoenix_annotated: bool


@router.post("/runs/{run_id}/clusters/{cluster_id}/review", response_model=ReviewResponse)
async def review_cluster(
    run_id: str,
    cluster_id: str,
    payload: ReviewRequest,
    user: Annotated[AuthedUser, Depends(require_user)],
) -> ReviewResponse:
    record = await get_run_store().get(run_id)
    # Foreign-owned reads as not-found — a 403 would CONFIRM the id exists.
    if record is None or record.owner_uid not in (None, user.uid):
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")
    if record.owner_uid is None:
        raise HTTPException(status_code=422, detail="sample runs cannot be reviewed")
    span_id = record.cluster_spans.get(cluster_id)
    if span_id is None:
        raise HTTPException(status_code=422, detail=f"cluster_id not on this run: {cluster_id}")
    if not user.email:
        raise HTTPException(
            status_code=422, detail="signed-in account has no email address on its token"
        )

    review = ClusterReview(
        verdict=payload.verdict,
        note=payload.note,
        reviewer_email=user.email,
        reviewed_at=utc_now_iso(),
    )
    # Read-modify-write of the whole dict: per-run review traffic is single-
    # officer; the merge path is the same contained write-through finalize uses.
    reviews = {**record.cluster_reviews, cluster_id: review}
    persisted = await persist_run_completion(
        run_id,
        RunCompletion(
            run_id=record.run_id,
            target_url=record.target_url,
            created_at=record.created_at,
            phase=record.phase,
            cluster_reviews=reviews,
        ),
    )
    if not persisted:
        raise HTTPException(status_code=502, detail="review could not be persisted — retry")

    annotated = await annotate_officer_verdict(
        span_id=span_id, verdict=payload.verdict, note=payload.note, cluster_id=cluster_id
    )
    return ReviewResponse(review=review, phoenix_annotated=annotated)


__all__ = ["annotate_officer_verdict", "router"]
