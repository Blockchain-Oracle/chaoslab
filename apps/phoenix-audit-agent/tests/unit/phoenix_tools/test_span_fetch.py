"""fetch_span — single-span retrieval over the REAL phoenix-client API.

arize-phoenix-client 2.x exposes ONLY `spans.get_spans(project_identifier=...,
trace_ids=...)`; there is no `get_span`. These tests pin the helper that every
rubric and the honored-check use to read one span, including the dict-shaped
v1.Span normalization (attributes mapping + ns timestamps).
"""

from __future__ import annotations

from typing import Any

import pytest

from phoenix_audit_agent.phoenix_tools.span_fetch import (
    FetchedSpan,
    SpanNotFoundError,
    fetch_span,
)

SPAN_ID = "0123456789abcdef"
OTHER_SPAN_ID = "fedcba9876543210"
TRACE_ID = SPAN_ID * 2
PROJECT = "target-agent"


def _v1_span(
    span_id: str,
    *,
    parent_id: str | None = "00aa00aa00aa00aa",
    attributes: dict[str, Any] | None = None,
    start_time: str = "2026-06-10T00:00:00+00:00",
    end_time: str = "2026-06-10T00:00:01.500000+00:00",
) -> dict[str, Any]:
    """Shape mirrors phoenix.client.__generated__.v1.Span (a TypedDict)."""
    span: dict[str, Any] = {
        "name": "agent.invoke",
        "context": {"trace_id": TRACE_ID, "span_id": span_id},
        "span_kind": "AGENT",
        "start_time": start_time,
        "end_time": end_time,
        "status_code": "OK",
        "attributes": attributes if attributes is not None else {"input.value": "hi"},
    }
    if parent_id is not None:
        span["parent_id"] = parent_id
    return span


class _FakeSpansNamespace:
    def __init__(self, spans: list[dict[str, Any]]) -> None:
        self._spans = spans
        self.calls: list[dict[str, Any]] = []

    async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(kwargs)
        return self._spans


class _FakePhoenix:
    def __init__(self, spans: list[dict[str, Any]]) -> None:
        self.spans = _FakeSpansNamespace(spans)


@pytest.mark.asyncio
async def test_fetches_matching_span_by_id() -> None:
    phoenix = _FakePhoenix([_v1_span(OTHER_SPAN_ID), _v1_span(SPAN_ID)])

    span = await fetch_span(phoenix, span_id=SPAN_ID, trace_id=TRACE_ID, project_identifier=PROJECT)

    assert isinstance(span, FetchedSpan)
    assert span.span_id == SPAN_ID
    assert span.attributes.get("input.value") == "hi"
    # the real client was queried by trace, scoped to the target's project
    (call,) = phoenix.spans.calls
    assert call["project_identifier"] == PROJECT
    assert list(call["trace_ids"]) == [TRACE_ID]


@pytest.mark.asyncio
async def test_missing_span_raises_loudly() -> None:
    phoenix = _FakePhoenix([_v1_span(OTHER_SPAN_ID)])

    with pytest.raises(SpanNotFoundError) as exc:
        await fetch_span(phoenix, span_id=SPAN_ID, trace_id=TRACE_ID, project_identifier=PROJECT)
    assert SPAN_ID in str(exc.value)
    assert TRACE_ID in str(exc.value)


@pytest.mark.asyncio
async def test_empty_trace_raises_loudly() -> None:
    phoenix = _FakePhoenix([])

    with pytest.raises(SpanNotFoundError):
        await fetch_span(phoenix, span_id=SPAN_ID, trace_id=TRACE_ID, project_identifier=PROJECT)


@pytest.mark.asyncio
async def test_32_hex_id_resolves_to_root_span() -> None:
    """The Injector may index by trace id (32 hex); resolve to the trace root."""
    root = _v1_span(SPAN_ID, parent_id=None, attributes={"output.value": "root"})
    child = _v1_span(OTHER_SPAN_ID)
    phoenix = _FakePhoenix([child, root])

    span = await fetch_span(
        phoenix, span_id=TRACE_ID, trace_id=TRACE_ID, project_identifier=PROJECT
    )

    assert span.span_id == SPAN_ID
    assert span.attributes.get("output.value") == "root"


@pytest.mark.asyncio
async def test_timestamps_normalized_to_ns() -> None:
    phoenix = _FakePhoenix([_v1_span(SPAN_ID)])

    span = await fetch_span(phoenix, span_id=SPAN_ID, trace_id=TRACE_ID, project_identifier=PROJECT)

    # 1.5s duration — rubrics derive duration from these when the explicit
    # phoenix-audit.duration_ms attribute is absent.
    assert span.end_time_ns - span.start_time_ns == 1_500_000_000


@pytest.mark.asyncio
async def test_unparseable_timestamps_are_zero_not_crash() -> None:
    raw = _v1_span(SPAN_ID, start_time="not-a-date", end_time="")
    phoenix = _FakePhoenix([raw])

    span = await fetch_span(phoenix, span_id=SPAN_ID, trace_id=TRACE_ID, project_identifier=PROJECT)

    # zeros — latency rubric treats missing timestamps as malformed and raises
    # RubricInputMissingError; fetch_span itself must not mask the span data.
    assert span.start_time_ns == 0
    assert span.end_time_ns == 0
