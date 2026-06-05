"""ADK A2A server for the target customer-support agent.

Wraps `root_agent` via `to_a2a()` so Phoenix Audit can call this agent over
the wire (A2A protocol v1.0) instead of in-process. The A2A wire is what
gives us the "fault isolation per ADR-002" claim — when an adversarial test
crashes this target subprocess, Phoenix Audit's orchestrator stays alive.

The exposed ASGI app (`a2a_app`) automatically registers the canonical A2A
endpoints, including `/.well-known/agent-card.json`. Skill discovery is
populated from `root_agent.tools`.

**Import order is load-bearing (per ADR-005):** `setup_observability()` MUST
be called BEFORE the ADK module attribute lookups, or `GoogleADKInstrumentor`
patches an already-imported module set and emitted spans silently disappear.

Local run:    uv run target-agent           # binds $PORT or 8001
Cloud Run:    Dockerfile sets PORT=8080; Cloud Run injects it at runtime.
"""

from __future__ import annotations

import os

# (1) Phoenix instrumentation FIRST (per ADR-005). setup_observability()
# resolves PHOENIX_API_KEY from env or Secret Manager, registers a Phoenix
# tracer provider, and attaches GoogleADKInstrumentor. The returned provider
# is held at module scope to prevent the span processor from being GC'd in
# long-running ASGI apps.
from target_agent.observability import setup_observability

_TRACER_PROVIDER = setup_observability()

# (2) ONLY THEN: ADK imports + uvicorn. The instrumentor must already be
# attached before any consumer holds references to ADK modules.
import uvicorn  # noqa: E402 — must come after setup_observability()
from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402

from target_agent.agent import root_agent  # noqa: E402

# Default port mirrors architecture/03-multi-agent-patterns.md §9.C.
# Cloud Run overrides via $PORT (typically 8080).
_DEFAULT_PORT = 8001

# to_a2a() returns a Starlette ASGI app. Phoenix Audit's RemoteA2aAgent
# client speaks to this by passing the card URL:
#   RemoteA2aAgent(agent_card='http://target:8001/.well-known/agent-card.json')
# See research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md §2.2.
# Known limitation tracked in issue #22: to_a2a's `port` param hardcodes the
# advertised `card.url` to the constructed value regardless of actual bind.
# S2.4 (Cloud Run deploy) wires a PUBLIC_URL env var to fix this.
a2a_app = to_a2a(root_agent, port=_DEFAULT_PORT)


def main() -> None:
    """Console-script entry: `uv run target-agent`.

    Reads PORT + HOST env vars so Cloud Run + local dev share the same code path.
    """
    port_raw = os.environ.get("PORT", str(_DEFAULT_PORT))
    try:
        port = int(port_raw)
    except ValueError as e:
        msg = f"target-agent: PORT env var must be an integer, got {port_raw!r}"
        raise SystemExit(msg) from e
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 — Cloud Run requires 0.0.0.0
    uvicorn.run(a2a_app, host=host, port=port)


if __name__ == "__main__":
    main()
