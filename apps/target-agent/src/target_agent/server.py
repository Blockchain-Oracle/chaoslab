"""ADK A2A server for the target customer-support agent.

Wraps `root_agent` via `to_a2a()` so Phoenix Audit can call this agent over
the wire (A2A protocol v1.0) instead of in-process. The A2A wire is what
gives us the "fault isolation per ADR-002" claim — when an adversarial test
crashes this target subprocess, Phoenix Audit's orchestrator stays alive.

The exposed ASGI app (`a2a_app`) automatically registers the canonical A2A
endpoints, including `/.well-known/agent-card.json`. Skill discovery is
populated from `root_agent.tools`.

**Import order is load-bearing.** OpenInference auto-instrumentors monkey-patch
ADK internals; installing the instrumentor BEFORE any consumer imports the
patched modules is the documented practice. The AST-based check at
`tests/acceptance/test_story_2_3_target_phoenix.sh` enforces this at the
source level. The correct ordering pattern is shown in
`research/.../architecture/02-phoenix-deep-dive.md` §3.4 (Phoenix Cloud + ADK
minimal snippet). Citation history: `audit-notes.md` D4-8.

Local run:    uv run target-agent           # binds $PORT or 8001
Cloud Run:    Dockerfile sets PORT=8080; Cloud Run injects it at runtime.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

# (1) Phoenix instrumentation FIRST. setup_observability() resolves
# PHOENIX_API_KEY (env → Secret Manager), registers a Phoenix tracer
# provider as the OTel global, and attaches GoogleADKInstrumentor. The
# returned provider is held at module scope to prevent the span processor
# from being GC'd in long-running ASGI.
from target_agent.observability import setup_observability

_TRACER_PROVIDER = setup_observability()

# (2) ONLY THEN: ADK imports + uvicorn. The instrumentor's monkey-patching
# is most reliable when installed before any code path that uses the
# patched modules executes.
import uvicorn  # noqa: E402 — must come after setup_observability()
from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402

from target_agent.agent import root_agent  # noqa: E402

# Default port is a Phoenix Audit project choice per
# architecture/03-multi-agent-patterns.md §9.C (which uses 8001 across the
# target-agent examples). The ADK `to_a2a()` default is 8000 — we deliberately
# diverge to leave the lower-numbered port for the orchestrator (Epic 4).
# Cloud Run overrides via $PORT (typically 8080) at runtime.
_DEFAULT_PORT = 8001
_HTTPS_DEFAULT_PORT = 443
_HTTP_DEFAULT_PORT = 80
_SUPPORTED_PUBLIC_URL_SCHEMES = frozenset({"http", "https"})


def _build_a2a_app() -> object:
    """Construct the A2A ASGI app, honoring PUBLIC_URL if set.

    Fix for issue #22 (W1 from PR #18 code-reviewer): `to_a2a(root_agent, port=8001)`
    bakes the advertised agent-card URL as `http://localhost:8001/` regardless
    of where the container actually binds. When deployed on Cloud Run, the
    upstream `RemoteA2aAgent` client fetches the card from
    `https://target-xxx.run.app/.well-known/agent-card.json`, reads `card.url`,
    then dispatches JSON-RPC to `http://localhost:8001/` — unreachable.

    `PUBLIC_URL` overrides the advertised URL with the actual external endpoint.
    S2.4 (this story) adds the READ-side wiring; the Cloud Run deploy workflow
    (S1.6, currently PENDING in sprint-status.yaml) will inject the env var via
    `gcloud run services update --set-env-vars=PUBLIC_URL=<run.app URL>`.
    Local dev keeps the default `localhost:8001` shape so
    `curl localhost:8001/.well-known/...` loopback testing still works.

    Validates the scheme strictly: only `http` and `https` are accepted. A
    silently-coerced `ftp://target.run.app` would make the card advertise an
    unreachable URL and break downstream `RemoteA2aAgent` dispatch — exactly
    the failure mode the H-1 finding flagged.
    """
    public_url = os.environ.get("PUBLIC_URL")
    if not public_url:
        return to_a2a(root_agent, port=_DEFAULT_PORT)

    parsed = urlparse(public_url)
    if parsed.scheme not in _SUPPORTED_PUBLIC_URL_SCHEMES:
        msg = (
            f"target-agent: PUBLIC_URL scheme must be 'http' or 'https', "
            f"got {parsed.scheme!r} (full input: {public_url!r})"
        )
        raise SystemExit(msg)
    if not parsed.hostname:
        msg = (
            f"target-agent: PUBLIC_URL env var must be a parseable URL with a host, "
            f"got {public_url!r}"
        )
        raise SystemExit(msg)
    # urlparse returns None for `.port` if omitted; default by scheme.
    port = parsed.port or (_HTTPS_DEFAULT_PORT if parsed.scheme == "https" else _HTTP_DEFAULT_PORT)
    # to_a2a signature: host, port, protocol — all keyword args. parsed.scheme
    # is guaranteed http/https by the whitelist check above; no fallback needed.
    return to_a2a(
        root_agent,
        host=parsed.hostname,
        port=port,
        protocol=parsed.scheme,
    )


# to_a2a() returns a Starlette ASGI app. Phoenix Audit's RemoteA2aAgent
# client speaks to this by passing the card URL:
#   RemoteA2aAgent(agent_card='https://target-xxx.run.app/.well-known/agent-card.json')
# See research/google-cloud-rapid-agent/architecture/03-multi-agent-patterns.md §2.2.
a2a_app = _build_a2a_app()


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
