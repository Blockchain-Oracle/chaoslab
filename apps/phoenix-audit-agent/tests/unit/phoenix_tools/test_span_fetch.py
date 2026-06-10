"""fetch_trace_spans — trace retrieval over the REAL phoenix-client API.

arize-phoenix-client 2.x exposes ONLY `spans.get_spans(project_identifier=...,
trace_ids=...)`; there is no `get_span`. These tests pin the helper the judge
phase uses to prefetch a probe's whole trace (one round-trip, shared between
the honored-check and the rubric), including the dict-shaped v1.Span
normalization (attributes mapping + parent/root detection + ns timestamps).
"""

from __future__ import annotations

from typing import Any

import pytest

from phoenix_audit_agent.phoenix_tools.span_fetch import (
    FetchedSpan,
    fetch_trace_spans,
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


async def _fetch(phoenix: _FakePhoenix) -> list[FetchedSpan]:
    return await fetch_trace_spans(phoenix, trace_id=TRACE_ID, project_identifier=PROJECT)


@pytest.mark.asyncio
async def test_fetches_every_span_of_the_trace_in_one_call() -> None:
    phoenix = _FakePhoenix([_v1_span(OTHER_SPAN_ID), _v1_span(SPAN_ID)])

    spans = await _fetch(phoenix)

    assert [s.span_id for s in spans] == [OTHER_SPAN_ID, SPAN_ID]
    assert all(isinstance(s, FetchedSpan) for s in spans)
    assert spans[1].attributes.get("input.value") == "hi"
    # the real client was queried by trace, scoped to the target's project
    (call,) = phoenix.spans.calls
    assert call["project_identifier"] == PROJECT
    assert list(call["trace_ids"]) == [TRACE_ID]


@pytest.mark.asyncio
async def test_empty_trace_returns_empty_list_for_caller_disclosure() -> None:
    # judge_phase maps an empty trace to a DISCLOSED error verdict +
    # honored=unreadable; the fetch layer itself stays a plain read.
    assert await _fetch(_FakePhoenix([])) == []


@pytest.mark.asyncio
async def test_root_span_detected_by_absent_parent_id() -> None:
    root = _v1_span(SPAN_ID, parent_id=None, attributes={"output.value": "root"})
    child = _v1_span(OTHER_SPAN_ID)
    spans = await _fetch(_FakePhoenix([child, root]))

    roots = [s for s in spans if s.is_root]
    assert [s.span_id for s in roots] == [SPAN_ID]
    assert roots[0].attributes.get("output.value") == "root"
    assert spans[0].is_root is False


@pytest.mark.asyncio
async def test_timestamps_normalized_to_ns() -> None:
    (span,) = await _fetch(_FakePhoenix([_v1_span(SPAN_ID)]))

    # 1.5s duration — the latency rubric derives server-side duration from
    # these when the auditor's client-side measurement is absent.
    assert span.end_time_ns - span.start_time_ns == 1_500_000_000


@pytest.mark.asyncio
async def test_unparseable_timestamps_are_zero_not_crash() -> None:
    raw = _v1_span(SPAN_ID, start_time="not-a-date", end_time="")
    (span,) = await _fetch(_FakePhoenix([raw]))

    # zeros — the latency rubric treats missing timestamps as malformed and
    # raises RubricInputMissingError; the fetch must not mask the span data.
    assert span.start_time_ns == 0
    assert span.end_time_ns == 0
