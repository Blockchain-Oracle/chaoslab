"""F1: MalformedToolOutputFault — corrupt tool output via ADK before_tool_callback.

Architectural inspiration from deepankarm/agent-chaos (Apache-2.0, pinned in
NOTICE); no source code is copied. Implemented natively against ADK 2.1.0's
callback system per docs/architecture.md ADR-006 (amended 2026-06-03) +
architecture/04 §8.2. ADK before_tool_callback short-circuits the real tool
when it returns non-None; for ``mode=exception`` the callback sets the
current TOOL span's status to ERROR + records the exception event before
raising, so the trace-as-assertion contract holds regardless of whether ADK
auto-records exceptions raised from before_tool_callback (per audit A13,
that auto-recording is documented as undefined behavior).
"""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from opentelemetry import trace
from pydantic import BaseModel, Field

from phoenix_audit_agent.adk_types import BaseTool, ToolContext

MalformationMode = Literal["invalid_json", "missing_required_field", "type_mismatch", "exception"]
_FAULT_TYPE = "malformed_tool_output"

# Single source for the mode->payload mapping — shared by the in-process
# callback below AND the remote-delivery descriptor (descriptors.py), so the
# two paths can never drift. `exception` carries None: callers raise instead.
MODE_PAYLOADS: dict[str, dict[str, Any] | None] = {
    "invalid_json": {
        # ADK before_tool_callback returns Optional[dict] per audit A13;
        # wrap the truncated string so the dict-contract holds while the
        # downstream agent still observes a non-JSON-parseable payload.
        "_phoenix_audit_malformed_payload": (
            '{"order_id": "12345", "items": [{"name": "widget", "qty": 2'
        ),
        "_phoenix_audit_payload_type": "invalid_json",
    },
    # `total` key omitted from the lookup_order schema {status, items, total}.
    "missing_required_field": {"status": "shipped", "items": [{"name": "widget", "qty": 2}]},
    "type_mismatch": {"status": 200, "items": "three widgets", "total": "ten"},
    "exception": None,
}


def _make_callback(
    fault: MalformedToolOutputFault,
) -> Callable[[BaseTool, dict[str, Any], ToolContext], Awaitable[dict[str, Any] | None]]:
    """Build an ADK before_tool_callback bound to this fault config."""

    async def callback(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> dict[str, Any] | None:
        if fault.target_tool_name is not None and tool.name != fault.target_tool_name:
            return None
        if fault.rate < 1.0 and secrets.randbelow(1_000_000) / 1_000_000 >= fault.rate:
            return None
        span = trace.get_current_span()
        span.set_attribute("phoenix_audit.fault.type", _FAULT_TYPE)
        span.set_attribute("phoenix_audit.fault.mode", fault.mode)
        if fault.mode != "exception":
            return MODE_PAYLOADS[fault.mode]
        # mode == "exception" — record status + event on the current span
        # before raising. Story-5.2 Notes say ADK's auto-recording of
        # exceptions raised from before_tool_callback "works empirically but
        # is documented as undefined behavior"; the audit (A13) recommends
        # on_tool_error_callback as future-proof. Defensively recording here
        # makes the trace contract hold even when ADK's auto-recording
        # doesn't fire — keeps the Judge's signal correct on every release.
        exc = RuntimeError("F1: injected malformed tool output (mode=exception)")
        span.set_status(trace.Status(trace.StatusCode.ERROR, "F1 fault injected"))
        span.record_exception(exc)
        raise exc

    return callback


class MalformedToolOutputFault(BaseModel):
    """Inject malformed tool output via ADK ``before_tool_callback`` (F1).

    ``target_tool_name=None`` applies the fault to every tool the agent
    exposes; setting it scopes the fault to one tool by name. ``rate<1.0``
    mixes injected faults with healthy calls (defer to Epic 5.7).
    """

    mode: MalformationMode
    rate: float = Field(default=1.0, ge=0.0, le=1.0)
    target_tool_name: str | None = None

    def as_callback(
        self,
    ) -> Callable[[BaseTool, dict[str, Any], ToolContext], Awaitable[dict[str, Any] | None]]:
        return _make_callback(self)
