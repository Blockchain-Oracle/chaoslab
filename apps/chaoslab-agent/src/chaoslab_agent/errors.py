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


class ChaosLabError(Exception):
    """Root of the Phoenix Audit domain exception hierarchy."""


class PhoenixExperimentError(ChaosLabError):
    """Raised when `run_phoenix_experiment` fails — wraps SDK / HTTP errors."""


class PhoenixAnnotationError(ChaosLabError):
    """Raised when `write_phoenix_annotation` fails."""
