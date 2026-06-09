"""Domain exception hierarchy for chaoslab-agent.

All Phoenix Audit errors derive from `ChaosLabError` so callers can catch the base
class for the project's known-failure surface without accidentally absorbing
unrelated runtime exceptions. Sub-classes are intentionally narrow (one per
external integration) so the orchestrator's logs name the failing system.

Per ADR-005: error messages must NEVER include secret material (API keys,
tokens). Use `raise ... from underlying` to preserve the traceback while
keeping the wrapper's own message sanitized; the chained exception may include
SDK-side detail and is best-effort scrubbed at the call site.
"""

from __future__ import annotations

from typing import Any


class ChaosLabError(Exception):
    """Root of the Phoenix Audit domain exception hierarchy."""


class PhoenixExperimentError(ChaosLabError):
    """Raised when `run_phoenix_experiment` fails — wraps SDK / HTTP errors."""


class PhoenixAnnotationError(ChaosLabError):
    """Raised when `write_phoenix_annotation` fails."""


class AdapterError(ChaosLabError):
    """Base class for every target-adapter failure (Tier 1/2/3)."""


class AdapterConnectionError(AdapterError):
    """Raised when an adapter cannot establish a transport to the target.

    Examples: TCP reset, DNS failure, TLS handshake error, connection timeout.
    The wrapper's own message names the target URL but never the auth payload.
    """


class AdapterDiscoveryError(AdapterError):
    """Raised when the target exists but does not expose the expected metadata.

    Examples: 404 on `/.well-known/agent-card.json`, malformed AgentCard JSON,
    missing required AgentCard fields. Distinct from `AdapterConnectionError`
    so callers can degrade to Tier 3 (HTTP black-box) on discovery failure
    while still failing fast on transport failure.
    """


class BaselineAbortError(ChaosLabError):
    """Raised by `BaselineCheck.validate()` when the target's pre-flight pass
    rate is below the configured threshold.

    The Chaos Toolkit steady-state-hypothesis gate (architecture/01 §7 Move 5):
    if the target is already broken pre-injection, the resilience signal from
    a fault-injection run is meaningless — abort the entire chaos run loud.

    Carries the structured ``BaselineResult`` so the orchestrator can include
    the full snapshot in the regulator-facing audit report without parsing
    the message string. ``result`` is typed ``Any`` here to avoid the
    circular import with ``injector.preflight``; concrete type is
    ``chaoslab_agent.injector.preflight.BaselineResult``.
    """

    def __init__(self, message: str, *, result: Any | None = None) -> None:
        super().__init__(message)
        self.result = result
