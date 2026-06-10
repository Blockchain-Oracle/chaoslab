"""Single-span retrieval over the real arize-phoenix-client 2.x API.

The client exposes only ``spans.get_spans(project_identifier=..., trace_ids=...)``
— there is NO ``get_span``. Every consumer that needs one span (Judge rubrics,
the honored-header check) goes through :func:`fetch_span`, which queries the
span's trace and selects the matching span, normalizing the dict-shaped
``v1.Span`` into an attribute-accessible :class:`FetchedSpan`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Generous page size: a single agent trace is dozens of spans, not thousands.
_TRACE_SPAN_LIMIT = 1000
_TRACE_ID_HEX_LEN = 32


class SpanNotFoundError(LookupError):
    """The requested span was not present in its trace's span list."""

    def __init__(self, *, span_id: str, trace_id: str, project_identifier: str) -> None:
        self.span_id = span_id
        self.trace_id = trace_id
        self.project_identifier = project_identifier
        super().__init__(
            f"span {span_id!r} not found in trace {trace_id!r} "
            f"(project {project_identifier!r}) — the target's Phoenix project "
            "has no such span; verdict evidence is unavailable"
        )


def _ts_ns(value: Any) -> int:
    if not value or not isinstance(value, str):
        return 0
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1_000_000_000)
    except ValueError:
        return 0


@dataclass(frozen=True)
class FetchedSpan:
    """v1.Span normalized for rubric consumption (attribute access + ns times)."""

    span_id: str
    trace_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0


def _normalize(raw: dict[str, Any]) -> FetchedSpan:
    context = raw.get("context") or {}
    return FetchedSpan(
        span_id=str(context.get("span_id", "")),
        trace_id=str(context.get("trace_id", "")),
        attributes=dict(raw.get("attributes") or {}),
        start_time_ns=_ts_ns(raw.get("start_time")),
        end_time_ns=_ts_ns(raw.get("end_time")),
    )


def _context_span_id(raw: dict[str, Any]) -> str:
    return str((raw.get("context") or {}).get("span_id", ""))


async def fetch_span(
    phoenix: Any,
    *,
    span_id: str,
    trace_id: str,
    project_identifier: str,
) -> FetchedSpan:
    """Fetch one span by id from its trace, or raise :class:`SpanNotFoundError`.

    A 32-hex ``span_id`` is the Injector's trace-indexed form — it resolves to
    the trace's ROOT span (no parent) rather than an exact id match.
    """
    spans: list[dict[str, Any]] = await phoenix.spans.get_spans(
        project_identifier=project_identifier,
        trace_ids=[trace_id],
        limit=_TRACE_SPAN_LIMIT,
    )
    if len(span_id) == _TRACE_ID_HEX_LEN:
        for raw in spans:
            if raw.get("parent_id") in (None, ""):
                return _normalize(raw)
    else:
        for raw in spans:
            if _context_span_id(raw) == span_id:
                return _normalize(raw)
    raise SpanNotFoundError(
        span_id=span_id, trace_id=trace_id, project_identifier=project_identifier
    )


__all__ = ["FetchedSpan", "SpanNotFoundError", "fetch_span"]
