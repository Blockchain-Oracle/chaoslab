"""Target-adapter layer — framework-agnostic call surface (ADR-002).

The five Pydantic schemas + the abstract base are frozen. Concrete tier
implementations land in sibling modules per stories 3.2-3.6:
- adk_adapter.py (Tier 1)
- langchain_adapter.py / crewai_adapter.py / openai_sdk_adapter.py (Tier 2)
- http_blackbox_adapter.py (Tier 3)
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
