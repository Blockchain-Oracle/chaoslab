"""ADK A2A server for the target customer-support agent.

Wraps `root_agent` via `to_a2a()` so Phoenix Audit can call this agent over
the wire (A2A protocol v1.0) instead of in-process. The A2A wire is what
gives us the "fault isolation per ADR-002" claim — when an adversarial test
crashes this target subprocess, Phoenix Audit's orchestrator stays alive.

The exposed ASGI app (`a2a_app`) automatically registers the canonical A2A
endpoints, including `/.well-known/agent-card.json`. Skill discovery is
populated from `root_agent.tools` — see Notes in story-2.2 for the override
path if auto-discovery diverges.

Local run:    uv run target-agent           # binds $PORT or 8001
Cloud Run:    Dockerfile sets PORT=8080; Cloud Run injects it at runtime.
"""

from __future__ import annotations

import os

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from target_agent.agent import root_agent

# Default port mirrors the local-dev convention in PRD demo moment +
# architecture/03-multi-agent-patterns.md §9.C. Cloud Run overrides via $PORT.
_DEFAULT_PORT = 8001

# to_a2a() returns a Starlette ASGI app. Phoenix Audit's RemoteA2aAgent
# client speaks to this directly via AgentCard.from_url(...).
a2a_app = to_a2a(root_agent, port=_DEFAULT_PORT)


def main() -> None:
    """Console-script entry: `uv run target-agent`.

    Reads PORT + HOST env vars so Cloud Run + local dev share the same code path.
    """
    port = int(os.environ.get("PORT", str(_DEFAULT_PORT)))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 — Cloud Run requires 0.0.0.0
    uvicorn.run(a2a_app, host=host, port=port)


if __name__ == "__main__":
    main()
