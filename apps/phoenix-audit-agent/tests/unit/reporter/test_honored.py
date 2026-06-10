"""span_honored — header-convention check over the PREFETCHED trace.

The locked warning's {N} may only count root spans actually read and found
lacking; a trace without a readable root surfaces as its own "unreadable"
disclosure state. Fetch-layer failures are mapped to "unreadable" by the
caller (judge_phase) since the single-fetch refactor — covered in
tests/unit/test_judge_phase_evidence.py.
"""

from __future__ import annotations

from typing import Any

from phoenix_audit_agent.phoenix_tools.span_fetch import FetchedSpan
from phoenix_audit_agent.reporter.honored import span_honored

SPAN_ID = "0123456789abcdef"
TRACE_ID = SPAN_ID * 2


def _root(attributes: dict[str, Any]) -> FetchedSpan:
    return FetchedSpan(span_id=SPAN_ID, trace_id=TRACE_ID, parent_id="", attributes=attributes)


def _child(attributes: dict[str, Any]) -> FetchedSpan:
    return FetchedSpan(
        span_id="ffffeeeeddddcccc", trace_id=TRACE_ID, parent_id=SPAN_ID, attributes=attributes
    )


def _check(spans: list[FetchedSpan]) -> str:
    return span_honored(spans, trace_id=TRACE_ID, run_id="run_test12345")


def test_attribute_true_on_root_is_honored() -> None:
    assert _check([_root({"phoenix_audit.honored": True})]) == "honored"


def test_attribute_absent_is_missing() -> None:
    assert _check([_root({})]) == "missing"


def test_attribute_string_true_is_missing_not_honored() -> None:
    # Only boolean true counts — a string "true" is not the convention.
    assert _check([_root({"phoenix_audit.honored": "true"})]) == "missing"


def test_attribute_on_child_only_is_missing() -> None:
    # The convention is response-span (root) level; a child carrying it does
    # not prove the response honored the header.
    assert _check([_root({}), _child({"phoenix_audit.honored": True})]) == "missing"


def test_empty_trace_is_unreadable() -> None:
    assert _check([]) == "unreadable"


def test_trace_without_root_span_is_unreadable() -> None:
    assert _check([_child({"phoenix_audit.honored": True})]) == "unreadable"
