"""F4: LatencySpikeFault — inject asyncio.sleep + httpx timeout shim.

Architectural inspiration from deepankarm/agent-chaos (Apache-2.0, pinned in
NOTICE); no source code is copied. Implemented natively against ADK 2.1.0's
before_tool_callback + httpx 0.28's AsyncBaseTransport per
docs/architecture.md ADR-006 (amended 2026-06-03) + architecture/04 §8.2.

Two injection surfaces, one fault class (architecture/04 §3.4):

- ``as_callback()`` returns an ADK ``before_tool_callback`` that sleeps for
  ``delay_ms`` before the real tool runs (TOOL span duration extends by the
  configured delay).
- ``httpx_transport()`` returns an ``httpx.AsyncBaseTransport`` subclass
  that injects ``request.extensions["timeout"]`` per call so the target's
  outbound HTTP runs against a tightened timeout — the Injector sub-agent
  (S5.7) wires this when the target is HTTP-shaped.

The canonical demo configuration is ``delay_ms=30000, timeout_ms=10000``:
the sleep exceeds the timeout, httpx raises ``ReadTimeout`` mid-call, ADK
records the TOOL span with ``status_code=ERROR`` plus an exception event —
the textbook network fault per OWASP LLM04 + MS#9.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from typing import Any, Literal

import httpx
from opentelemetry import trace
from pydantic import BaseModel, Field

from chaoslab_agent.adk_types import BaseTool, ToolContext

_FAULT_TYPE = "latency_spike"
_MAX_MS = 120_000
_RAND_BUCKET = 1_000_000


class LatencySpikeFault(BaseModel):
    """Inject asyncio.sleep before tool calls and tighten httpx timeout (F4)."""

    delay_ms: int = Field(ge=0, le=_MAX_MS)
    timeout_ms: int = Field(ge=0, le=_MAX_MS)
    target_tool_name: str | None = None
    rate: float = Field(default=1.0, ge=0.0, le=1.0)

    def as_callback(
        self,
    ) -> Callable[[BaseTool, dict[str, Any], ToolContext], Awaitable[None]]:
        return _make_callback(self)

    def httpx_transport(self) -> httpx.AsyncBaseTransport:
        return _TimeoutShimTransport(self.timeout_ms / 1000.0)


def _make_callback(
    fault: LatencySpikeFault,
) -> Callable[[BaseTool, dict[str, Any], ToolContext], Awaitable[None]]:
    async def callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> None:
        if fault.target_tool_name is not None and tool.name != fault.target_tool_name:
            return
        if fault.rate < 1.0 and secrets.randbelow(_RAND_BUCKET) / _RAND_BUCKET >= fault.rate:
            return
        span = trace.get_current_span()
        span.set_attribute("chaoslab.fault.type", _FAULT_TYPE)
        span.set_attribute("chaoslab.fault.delay_ms", fault.delay_ms)
        span.set_attribute("chaoslab.fault.timeout_ms", fault.timeout_ms)
        await asyncio.sleep(fault.delay_ms / 1000.0)
        # injected=True records that the fault completed (sleep returned)
        # — the trace contract for F1/F2/F3 carries the same boolean so the
        # Judge can read a uniform "did this fault land" signal.
        span.set_attribute("chaoslab.fault.injected", True)

    return callback


class _TimeoutShimTransport(httpx.AsyncBaseTransport):
    """Tightens per-phase httpx timeouts to a single seconds value.

    The shim wraps a normal ``httpx.AsyncHTTPTransport`` instance; rebind
    ``self._base`` for tests that want to observe ``request.extensions``
    without hitting the network.
    """

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._base: httpx.AsyncBaseTransport = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        request.extensions = {
            **request.extensions,
            "timeout": {
                "connect": self._timeout.connect,
                "read": self._timeout.read,
                "write": self._timeout.write,
                "pool": self._timeout.pool,
            },
        }
        return await self._base.handle_async_request(request)


__all__: list[Literal["LatencySpikeFault"]] = ["LatencySpikeFault"]
