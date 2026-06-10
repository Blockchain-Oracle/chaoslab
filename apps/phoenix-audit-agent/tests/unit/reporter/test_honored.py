"""span_honored — three-state header-convention check.

The locked warning's {N} may only count spans actually read and found
lacking; unreadable spans surface as their own disclosure state, and
programmer errors must propagate (a broad catch here once turned a missing
client method into "every target is compliant").
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phoenix_audit_agent.reporter.honored import span_honored

SPAN_ID = "0123456789abcdef"
TRACE_ID = SPAN_ID * 2
PROJECT = "target-agent"


def _v1_span(attributes: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "agent.invoke",
        "context": {"trace_id": TRACE_ID, "span_id": SPAN_ID},
        "span_kind": "AGENT",
        "start_time": "2026-06-10T00:00:00+00:00",
        "end_time": "2026-06-10T00:00:01+00:00",
        "status_code": "OK",
        "attributes": attributes,
    }


class _Phoenix:
    def __init__(self, spans: list[dict[str, Any]] | Exception) -> None:
        outer = self

        class _Spans:
            async def get_spans(self, **kwargs: Any) -> list[dict[str, Any]]:
                if isinstance(outer._spans, Exception):
                    raise outer._spans
                return outer._spans

        self._spans = spans
        self.spans = _Spans()


async def _check(phoenix: _Phoenix) -> str:
    return await span_honored(
        phoenix,
        span_id=SPAN_ID,
        trace_id=TRACE_ID,
        project_identifier=PROJECT,
        run_id="run_test12345",
    )


@pytest.mark.asyncio
async def test_attribute_true_is_honored() -> None:
    phoenix = _Phoenix([_v1_span({"phoenix_audit.honored": True})])
    assert await _check(phoenix) == "honored"


@pytest.mark.asyncio
async def test_attribute_absent_is_missing() -> None:
    phoenix = _Phoenix([_v1_span({})])
    assert await _check(phoenix) == "missing"


@pytest.mark.asyncio
async def test_attribute_string_true_is_missing_not_honored() -> None:
    # Only boolean true counts — a string "true" is not the convention.
    phoenix = _Phoenix([_v1_span({"phoenix_audit.honored": "true"})])
    assert await _check(phoenix) == "missing"


@pytest.mark.asyncio
async def test_span_not_in_trace_is_unreadable() -> None:
    phoenix = _Phoenix([])  # trace exists but the span is gone
    assert await _check(phoenix) == "unreadable"


@pytest.mark.asyncio
async def test_network_failure_is_unreadable() -> None:
    phoenix = _Phoenix(httpx.ConnectError("phoenix unreachable"))
    assert await _check(phoenix) == "unreadable"


@pytest.mark.asyncio
async def test_programmer_error_propagates() -> None:
    """AttributeError (e.g. a renamed client method) must crash the audit,
    never silently mark the target compliant."""

    class _BrokenPhoenix:
        class spans:  # noqa: N801 — namespace stand-in
            pass  # no get_spans at all

    with pytest.raises(AttributeError):
        await span_honored(
            _BrokenPhoenix(),
            span_id=SPAN_ID,
            trace_id=TRACE_ID,
            project_identifier=PROJECT,
            run_id="run_test12345",
        )
