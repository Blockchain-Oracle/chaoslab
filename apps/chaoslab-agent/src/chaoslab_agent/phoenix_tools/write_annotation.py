"""ADK FunctionTool wrapper for `phoenix.client.AsyncClient.spans.log_span_annotations`.

ADR-005 keystone tool — Phoenix MCP does NOT expose the span-annotation writeback
endpoint (`architecture/02 §9.6`); Phoenix Audit wraps the Python SDK call so the
Judge sub-agent can durably write its cluster scores back to the original spans.

Body is intentionally short (<=30 significant LOC per ADR-005); validation,
client construction, and secret-scrubbing helpers live above. The `_scrub_secret`
helper is shared with `run_experiment.py` — future Phoenix tools should extract
the shared client + scrub helpers into a `_common.py` module.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Literal, cast

import httpx
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
# test-fixture short ids while rejecting obvious truncations. The regex also
# blocks non-hex characters (a `span_id="!!!!!!!!"` would 404 server-side).
_MIN_SPAN_ID_LEN = 8
_MAX_SPAN_ID_LEN = 32
_SPAN_ID_RE = re.compile(r"^[0-9a-fA-F]{8,32}$")

# Reason cap. Phoenix's OpenAPI doesn't publish a max; ~8KB is the documented
# practical ceiling for sync writes. Above that we fail loud locally instead of
# letting the SDK time out + surface an opaque server error.
_MAX_REASON_LEN = 8192

# ASCII control characters below this codepoint break Postgres' `text` storage
# (Phoenix's backend). \t, \n, \r are whitelisted as printable whitespace.
_PRINTABLE_THRESHOLD = 32


class AnnotationResult(BaseModel):
    """Structured return of `write_span_annotation`.

    Mirrors what's persisted to Phoenix so callers can assert on the write
    without a follow-up GET. `status` is currently always `"ok"` — failures
    raise `PhoenixAnnotationError` instead of returning a non-ok status.
    """

    status: Literal["ok"]
    span_id: str = Field(min_length=_MIN_SPAN_ID_LEN)
    annotation_name: str
    annotation_identifier: str
    score: float = Field(ge=0.0, le=1.0)
    wrote_at: str

    @field_validator("wrote_at")
    @classmethod
    def _wrote_at_iso(cls, v: str) -> str:
        """Shape gate: must parse as RFC-3339 UTC with `Z` suffix + millisecond precision."""
        if not v.endswith("Z") or "T" not in v:
            msg = f"wrote_at must be RFC-3339 UTC with trailing Z, got {v!r}"
            raise ValueError(msg)
        # Strict parse — `datetime.fromisoformat` rejects malformed shapes.
        _dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


def _iso_now() -> str:
    """RFC-3339 UTC with millisecond precision.

    Millisecond resolution (vs. second-only) lets two annotations written in
    the same second still have distinct `wrote_at` values — important when the
    Judge writes multiple cluster scores for the same trace.
    """
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _default_identifier(span_id: str, cluster_id: str, settings: Settings) -> str:
    """Stable, address able identifier for a cluster annotation.

    Phoenix dedups on `(name, span_id, identifier)`. An empty identifier means
    "second write overwrites first" — which silently loses Judge cluster scores
    when more than one cluster targets the same span. The default carries the
    Phoenix Audit version + cluster id so multiple judges coexist.
    """
    return f"chaoslab/{settings.service_version}/{cluster_id or 'default'}/{span_id[:16]}"


def _validate_inputs(span_id: str, score: float, reason: str, annotator: str) -> AnnotatorKind:
    """Pre-flight checks. Fails loud BEFORE any SDK / HTTP call.

    Phoenix's SDK is permissive on bad inputs (it will happily POST a blank
    annotation); fail loud here so the orchestrator surfaces a typed
    PhoenixAnnotationError instead of a server-side 4xx round-trip.
    """
    if not span_id or not _SPAN_ID_RE.fullmatch(span_id):
        raise PhoenixAnnotationError(
            f"span_id must be 8-32 hex chars (OTel SpanID shape), got {span_id!r}"
        )
    import math as _math

    if _math.isnan(score) or not (0.0 <= score <= 1.0):
        raise PhoenixAnnotationError(f"score out of bounds [0,1]: {score!r}")
    if not reason or not reason.strip():
        raise PhoenixAnnotationError("reason must be a non-empty string")
    if "\x00" in reason or any(ord(c) < _PRINTABLE_THRESHOLD and c not in "\t\n\r" for c in reason):
        raise PhoenixAnnotationError(
            "reason contains control characters that would break server-side storage"
        )
    if len(reason) > _MAX_REASON_LEN:
        raise PhoenixAnnotationError(
            f"reason too long: {len(reason)} chars (max {_MAX_REASON_LEN})"
        )
    if annotator not in _ANNOTATOR_KIND:
        raise PhoenixAnnotationError(
            f"unknown annotator: {annotator!r} (allowed={sorted(_ANNOTATOR_KIND)!r})"
        )
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
    identifier: str,
    settings: Settings,
) -> SpanAnnotationData:
    """Construct the SpanAnnotationData payload Phoenix's SDK expects.

    Second-line defense: re-asserts the `annotator_kind` enum + score bounds
    so a future caller that imports `_build_annotation` directly cannot bypass
    `_validate_inputs` to send malformed data to Phoenix.
    """
    if annotator_kind not in ("LLM", "HUMAN", "CODE"):
        raise PhoenixAnnotationError(
            f"_build_annotation: invalid annotator_kind {annotator_kind!r}"
        )
    if not (0.0 <= score <= 1.0):
        raise PhoenixAnnotationError(f"_build_annotation: score out of bounds [0,1]: {score!r}")
    return SpanAnnotationData(
        name=_ANNOTATION_NAME,
        annotator_kind=annotator_kind,
        span_id=span_id,
        result={"label": label, "score": score, "explanation": reason},
        metadata={"chaoslab_version": settings.service_version},
        identifier=identifier,
    )


async def _post_annotation(annotation: SpanAnnotationData, settings: Settings) -> None:
    """Single SDK call site; catch + re-raise with sanitized PhoenixAnnotationError shape."""
    try:
        await _build_client(settings).spans.log_span_annotations(span_annotations=[annotation])
    except PhoenixAnnotationError:
        raise
    except httpx.HTTPStatusError as e:
        raise PhoenixAnnotationError(
            f"annotation write failed: span_id={annotation['span_id']} "
            f"status={e.response.status_code}"
        ) from e
    except Exception as e:
        raise PhoenixAnnotationError(
            f"annotation write failed: span_id={annotation['span_id']} "
            f"cause={type(e).__name__}: {_scrub_secret(str(e), settings)}"
        ) from e


async def write_span_annotation(
    span_id: str,
    score: float,
    reason: str,
    cluster_id: str = "default",
    annotator: AnnotatorLiteral = "chaoslab_judge",
    label: str = "auto",
) -> AnnotationResult:
    """Write a Phoenix span annotation; the Judge's cluster score lands on the original span.

    ADR-005 keystone tool. `cluster_id` participates in the dedup identifier so
    multiple cluster annotations coexist on the same span instead of silently
    overwriting (Phoenix dedups on `(name, span_id, identifier)`).
    """
    settings = get_settings()
    annotator_kind = _validate_inputs(span_id, score, reason, annotator)
    identifier = _default_identifier(span_id, cluster_id, settings)
    annotation = _build_annotation(
        span_id, annotator_kind, label, score, reason, identifier, settings
    )
    await _post_annotation(annotation, settings)
    return AnnotationResult(
        status="ok",
        span_id=span_id,
        annotation_name=_ANNOTATION_NAME,
        annotation_identifier=identifier,
        score=score,
        wrote_at=_iso_now(),
    )


phoenix_write_annotation_tool: FunctionTool = FunctionTool(func=write_span_annotation)
