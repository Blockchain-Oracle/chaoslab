"""Trace retrieval over the real arize-phoenix-client 2.x API.

The client exposes only ``spans.get_spans(project_identifier=..., trace_ids=...)``
— there is NO ``get_span``. The judge phase prefetches a probe's whole trace
via :func:`fetch_trace_spans` (one round-trip, shared between the
honored-check and the rubric), normalizing each dict-shaped ``v1.Span`` into
an attribute-accessible :class:`FetchedSpan` with root detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Generous page size: a single agent trace is dozens of spans, not thousands.
_TRACE_SPAN_LIMIT = 1000


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
    parent_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = 0
    end_time_ns: int = 0

    @property
    def is_root(self) -> bool:
        return not self.parent_id


def _normalize(raw: dict[str, Any]) -> FetchedSpan:
    context = raw.get("context") or {}
    return FetchedSpan(
        span_id=str(context.get("span_id", "")),
        trace_id=str(context.get("trace_id", "")),
        parent_id=str(raw.get("parent_id") or ""),
        attributes=dict(raw.get("attributes") or {}),
        start_time_ns=_ts_ns(raw.get("start_time")),
        end_time_ns=_ts_ns(raw.get("end_time")),
    )


async def fetch_trace_spans(
    phoenix: Any,
    *,
    trace_id: str,
    project_identifier: str,
) -> list[FetchedSpan]:
    """Fetch and normalize EVERY span of one trace — one Phoenix round-trip.

    The judge phase shares this single result between the honored-check and
    the rubric (perf: the old shape fetched the same trace twice per probe).
    """
    raw: list[dict[str, Any]] = await phoenix.spans.get_spans(
        project_identifier=project_identifier,
        trace_ids=[trace_id],
        limit=_TRACE_SPAN_LIMIT,
    )
    return [_normalize(r) for r in raw]


__all__ = ["FetchedSpan", "fetch_trace_spans"]
