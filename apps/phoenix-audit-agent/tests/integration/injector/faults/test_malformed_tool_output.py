"""Trace-as-assertion tests for F1 MalformedToolOutputFault.

The spec (story-5.2 BDD lines 49-66) calls for verifying that each
malformation mode produces a TOOL span with the expected
``phoenix_audit.fault.type`` / ``phoenix_audit.fault.mode`` attributes plus the
mode-specific payload corruption.

These tests exercise the callback contract directly against a real ADK
``FunctionTool`` + a real OpenTelemetry ``InMemorySpanExporter`` — they do
NOT drive Gemini, so they run without ``@pytest.mark.online`` cost.
The Injector sub-agent (Epic 5.7) will exercise the full LLM-driven path
once that lands; F1's behavior is in the callback itself, and verifying
the callback's span side-effects is the load-bearing contract.
"""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span

from phoenix_audit_agent.adk_types import FunctionTool, ToolContext
from phoenix_audit_agent.injector.faults import MalformedToolOutputFault

pytestmark = pytest.mark.integration


def _lookup_order(order_id: str) -> dict[str, Any]:
    """Tool body matching the target-agent lookup_order schema (status/items/total)."""
    return {"status": "shipped", "items": [{"name": "widget", "qty": 2}], "total": 19.99}


_LOOKUP_ORDER_TOOL = FunctionTool(func=_lookup_order)


# OTEL allows the global TracerProvider to be set only once per process. A
# per-test fixture that calls trace.set_tracer_provider would silently no-op
# after the first test (and a warning floods the logs). The module-scope
# provider + a per-test exporter.clear() gives us the same isolation without
# fighting OTEL's once-only constraint. Production code (structlog +
# arize-phoenix-otel) sets its own provider at startup; tests must NOT
# clobber it. We acquire the tracer FROM our provider directly rather than
# via the global, so production tracing is undisturbed.
_TEST_EXPORTER = InMemorySpanExporter()
_TEST_PROVIDER = TracerProvider()
_TEST_PROVIDER.add_span_processor(SimpleSpanProcessor(_TEST_EXPORTER))
_TEST_TRACER = _TEST_PROVIDER.get_tracer("phoenix-audit.test.injector.faults")


@pytest.fixture(autouse=True)
def exporter() -> InMemorySpanExporter:
    """Autouse so tests that don't request the fixture also start clean
    (test-analyzer B2 — without this, regression tests inherit stale spans)."""
    _TEST_EXPORTER.clear()
    return _TEST_EXPORTER


async def _invoke_callback(
    fault: MalformedToolOutputFault,
    *,
    tool: FunctionTool = _LOOKUP_ORDER_TOOL,
    args: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, Span]:
    """Run the fault's callback inside a TOOL span on the test tracer.

    The callback in src/ reads ``trace.get_current_span()`` which resolves to
    whatever span is current in the OTEL context — binding via the test
    tracer's ``start_as_current_span`` delivers the finished span to our
    exporter without disturbing the global provider.
    """
    callback = fault.as_callback()
    with _TEST_TRACER.start_as_current_span("test.tool.call") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        try:
            result = await callback(tool, args or {"order_id": "12345"}, cast(ToolContext, None))
        except RuntimeError:
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.record_exception(RuntimeError("F1: injected"))
            raise
    return result, span


def _last_tool_span(exporter: InMemorySpanExporter) -> ReadableSpan:
    spans = [
        s
        for s in exporter.get_finished_spans()
        if s.attributes is not None and s.attributes.get("openinference.span.kind") == "TOOL"
    ]
    assert spans, "no TOOL spans recorded"
    return spans[-1]


async def test_invalid_json_mode_sets_span_attrs_and_returns_unparseable_payload(
    exporter: InMemorySpanExporter,
) -> None:
    fault = MalformedToolOutputFault(mode="invalid_json", target_tool_name="_lookup_order")
    result, _ = await _invoke_callback(fault)
    assert result is not None
    payload = result["_phoenix_audit_malformed_payload"]
    with pytest.raises(json.JSONDecodeError):
        json.loads(payload)

    span = _last_tool_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("phoenix_audit.fault.type") == "malformed_tool_output"
    assert span.attributes.get("phoenix_audit.fault.mode") == "invalid_json"


async def test_missing_required_field_mode_omits_total(
    exporter: InMemorySpanExporter,
) -> None:
    fault = MalformedToolOutputFault(
        mode="missing_required_field", target_tool_name="_lookup_order"
    )
    result, _ = await _invoke_callback(fault)
    assert result is not None
    # lookup_order schema has total; the malformation omits it.
    assert "total" not in result
    assert "status" in result  # other fields preserved

    span = _last_tool_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("phoenix_audit.fault.mode") == "missing_required_field"


async def test_type_mismatch_mode_swaps_field_types(
    exporter: InMemorySpanExporter,
) -> None:
    fault = MalformedToolOutputFault(mode="type_mismatch", target_tool_name="_lookup_order")
    result, _ = await _invoke_callback(fault)
    assert result is not None
    assert isinstance(result["status"], int)  # schema says str
    assert isinstance(result["items"], str)  # schema says list
    assert isinstance(result["total"], str)  # schema says float

    span = _last_tool_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("phoenix_audit.fault.mode") == "type_mismatch"


async def test_exception_mode_raises_runtime_error_and_records_event(
    exporter: InMemorySpanExporter,
) -> None:
    fault = MalformedToolOutputFault(mode="exception", target_tool_name="_lookup_order")
    expected = r"F1: injected malformed tool output \(mode=exception\)"
    with pytest.raises(RuntimeError, match=expected):
        await _invoke_callback(fault)

    span = _last_tool_span(exporter)
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.events, "expected an exception event on the TOOL span"
    exc_event = next((e for e in span.events if e.name == "exception"), None)
    assert exc_event is not None
    assert exc_event.attributes is not None
    assert exc_event.attributes.get("exception.type")


async def test_target_tool_name_mismatch_lets_real_tool_run(
    exporter: InMemorySpanExporter,
) -> None:
    """target_tool_name='other' → callback returns None, ADK falls through to real tool."""
    fault = MalformedToolOutputFault(mode="invalid_json", target_tool_name="some_other_tool")
    result, _ = await _invoke_callback(fault)
    assert result is None  # let-real-tool-run signal per ADK callback contract

    # The span exists but should NOT carry the fault attributes when the tool isn't targeted.
    span = _last_tool_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("phoenix_audit.fault.type") is None
    assert span.attributes.get("phoenix_audit.fault.mode") is None


async def test_target_tool_name_none_applies_to_every_tool(
    exporter: InMemorySpanExporter,
) -> None:
    """target_tool_name=None means the fault attacks whatever tool the callback fires on."""
    fault = MalformedToolOutputFault(mode="invalid_json", target_tool_name=None)
    result, _ = await _invoke_callback(fault)
    assert result is not None
    assert "_phoenix_audit_malformed_payload" in result


async def test_rate_zero_short_circuits_every_call(exporter: InMemorySpanExporter) -> None:
    """rate=0.0 → callback always returns None (let real tool run); no fault attrs set."""
    fault = MalformedToolOutputFault(mode="exception", rate=0.0, target_tool_name="_lookup_order")
    result, _ = await _invoke_callback(fault)
    assert result is None
    span = _last_tool_span(exporter)
    assert span.attributes is not None
    assert span.attributes.get("phoenix_audit.fault.type") is None


async def test_callback_accepts_adk_kwarg_invocation_contract() -> None:
    """ADK invokes before_tool_callback with kwargs: tool=, args=, tool_context=.

    See google/adk/flows/llm_flows/functions.py:565,808. Param names must match
    or production would crash with TypeError. Regression guard mirrors F2/F3.
    `callback: Any` because Callable's positional-param structural type
    loses kwarg-by-name invocation info; the param names ARE the runtime
    contract this test exists to lock in.
    """
    fault = MalformedToolOutputFault(mode="invalid_json", target_tool_name="_lookup_order")
    callback: Any = fault.as_callback()
    result = await callback(
        tool=_LOOKUP_ORDER_TOOL,
        args={"order_id": "12345"},
        tool_context=cast(ToolContext, None),
    )
    assert result is not None
    assert "_phoenix_audit_malformed_payload" in result
