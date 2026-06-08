"""ADK FunctionTool wrapper for `phoenix.client.AsyncClient.spans.log_span_annotations`.

ADR-005 keystone tool — Phoenix MCP does NOT expose the span-annotation writeback
endpoint (`architecture/02 §9.6`); Phoenix Audit wraps the Python SDK call so the
Judge sub-agent can durably write its cluster scores back to the original spans.

Body is intentionally short (<=30 significant LOC per ADR-005); validation,
client construction, and secret-scrubbing helpers live above. Reuses the
`_scrub_secret` strategy from run_experiment.py: regex pass + literal-key reverse
scrub.
"""

from __future__ import annotations

import time
from typing import Literal, cast

from google.adk.tools import FunctionTool
from phoenix.client import AsyncClient
from phoenix.client.resources.spans import SpanAnnotationData
from pydantic import BaseModel, Field, field_validator

from chaoslab_agent.config import Settings, get_settings
from chaoslab_agent.errors import PhoenixAnnotationError
from chaoslab_agent.phoenix_tools.run_experiment import _derive_base_url, _scrub_secret

# Annotation name is fixed per project — every Phoenix Audit cluster annotation
# carries this name so downstream consumers can filter on it deterministically.
_ANNOTATION_NAME = "chaoslab_cluster"

AnnotatorLiteral = Literal["chaoslab_judge", "human", "code"]
AnnotatorKind = Literal["LLM", "HUMAN", "CODE"]

# Map our caller-facing names to Phoenix's annotator_kind enum. Keeping the
# mapping explicit (vs. .upper()) lets us evolve project-specific labels
# ("chaoslab_judge") without breaking Phoenix's wire contract.
_ANNOTATOR_KIND: dict[AnnotatorLiteral, AnnotatorKind] = {
    "chaoslab_judge": "LLM",
    "human": "HUMAN",
    "code": "CODE",
}

# Phoenix span ids are 16-hex-char OTel SpanIDs by spec; we accept 8+ to allow
# test-fixture short ids while rejecting obvious truncations.
_MIN_SPAN_ID_LEN = 8


class AnnotationResult(BaseModel):
    """Structured output of `write_span_annotation` — what the Judge logs upstream."""

    status: Literal["ok", "skipped"]
    span_id: str = Field(min_length=8)
    annotation_name: str
    score: float = Field(ge=0.0, le=1.0)
    wrote_at: str

    @field_validator("wrote_at")
    @classmethod
    def _wrote_at_iso(cls, v: str) -> str:
        # Lightweight shape gate: 'YYYY-MM-DDTHH:MM:SSZ' suffix. Full RFC-3339
        # parsing is overkill for an internal field.
        if not v.endswith("Z") or "T" not in v:
            msg = f"wrote_at must be RFC-3339 UTC with trailing Z, got {v!r}"
            raise ValueError(msg)
        return v


def _iso_now() -> str:
    """RFC-3339 UTC timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _validate_inputs(span_id: str, score: float, reason: str, annotator: str) -> AnnotatorKind:
    """Pre-flight checks. Fails loud BEFORE any SDK / HTTP call.

    Phoenix's SDK is permissive on bad inputs (it will happily try to write a
    blank annotation); the wrapper rejects empty reasons + unknown annotators
    so the orchestrator gets a clear PhoenixAnnotationError instead of a
    server-side 4xx whose body might contain auth metadata.
    """
    if not span_id or len(span_id) < _MIN_SPAN_ID_LEN:
        raise PhoenixAnnotationError(f"span_id too short: {span_id!r}")
    if not (0.0 <= score <= 1.0):
        raise PhoenixAnnotationError(f"score out of bounds [0,1]: {score!r}")
    if not reason or not reason.strip():
        raise PhoenixAnnotationError("reason must be a non-empty string")
    if annotator not in _ANNOTATOR_KIND:
        raise PhoenixAnnotationError(
            f"unknown annotator: {annotator!r} " f"(allowed={sorted(_ANNOTATOR_KIND)!r})"
        )
    # Cast safe: membership check above narrows `annotator` to the Literal.
    return _ANNOTATOR_KIND[cast(AnnotatorLiteral, annotator)]


def _build_client(settings: Settings) -> AsyncClient:
    """Build an AsyncClient with PHOENIX_API_KEY pulled via SecretStr (no env-implicit lookup)."""
    api_key = settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    return AsyncClient(api_key=api_key, base_url=_derive_base_url(settings))


def _build_annotation(
    span_id: str,
    annotator_kind: AnnotatorKind,
    label: str,
    score: float,
    reason: str,
    settings: Settings,
) -> SpanAnnotationData:
    """Construct the SpanAnnotationData payload Phoenix's SDK expects."""
    return SpanAnnotationData(
        name=_ANNOTATION_NAME,
        annotator_kind=annotator_kind,
        span_id=span_id,
        result={"label": label, "score": score, "explanation": reason},
        metadata={"chaoslab_version": settings.service_version},
        identifier="",
    )


async def write_span_annotation(
    span_id: str,
    score: float,
    reason: str,
    annotator: AnnotatorLiteral = "chaoslab_judge",
    label: str = "auto",
) -> AnnotationResult:
    """Write a Phoenix span annotation; the Judge's cluster score lands on the original span.

    ADR-005 keystone tool. Wraps `AsyncClient.spans.log_span_annotations`. Inputs
    are validated BEFORE any HTTP call; SDK exceptions surface as `PhoenixAnnotationError`
    with secrets scrubbed via the shared `_scrub_secret` helper.
    """
    settings = get_settings()
    annotator_kind = _validate_inputs(span_id, score, reason, annotator)
    annotation = _build_annotation(span_id, annotator_kind, label, score, reason, settings)
    try:
        await _build_client(settings).spans.log_span_annotations(span_annotations=[annotation])
    except PhoenixAnnotationError:
        raise
    except Exception as e:
        raise PhoenixAnnotationError(
            f"annotation write failed: span_id={span_id} "
            f"cause={type(e).__name__}: {_scrub_secret(str(e), settings)}"
        ) from e
    return AnnotationResult(
        status="ok",
        span_id=span_id,
        annotation_name=_ANNOTATION_NAME,
        score=score,
        wrote_at=_iso_now(),
    )


phoenix_write_annotation_tool: FunctionTool = FunctionTool(func=write_span_annotation)
