"""Target-adapter layer — framework-agnostic call surface (ADR-002).

The five Pydantic schemas + the abstract base defined in ``base`` are frozen.
Concrete tier implementations land in sibling modules; see ADR-002 +
``docs/sprint-status.yaml`` for the current set.
"""

from chaoslab_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)

__all__ = [
    "AdapterFingerprint",
    "AdapterInvocation",
    "AdapterResult",
    "AdapterTier",
    "TargetAdapter",
    "TargetSpec",
]
