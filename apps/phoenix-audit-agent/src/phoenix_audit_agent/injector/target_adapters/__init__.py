"""Target-adapter layer — framework-agnostic call surface (ADR-002).

The five Pydantic schemas + the abstract base defined in ``base`` are frozen.
Concrete tier implementations land in sibling modules; see ADR-002 +
``docs/sprint-status.yaml`` for the current set.
"""

from phoenix_audit_agent.injector.target_adapters.adk_adapter import ADKAdapter
from phoenix_audit_agent.injector.target_adapters.base import (
    AdapterFingerprint,
    AdapterInvocation,
    AdapterResult,
    AdapterTier,
    TargetAdapter,
    TargetSpec,
)
from phoenix_audit_agent.injector.target_adapters.crewai_adapter import CrewAIAdapter
from phoenix_audit_agent.injector.target_adapters.http_blackbox_adapter import HTTPBlackboxAdapter
from phoenix_audit_agent.injector.target_adapters.langchain_adapter import LangChainAdapter
from phoenix_audit_agent.injector.target_adapters.openai_sdk_adapter import OpenAISDKAdapter

__all__ = [
    "ADKAdapter",
    "AdapterFingerprint",
    "AdapterInvocation",
    "AdapterResult",
    "AdapterTier",
    "CrewAIAdapter",
    "HTTPBlackboxAdapter",
    "LangChainAdapter",
    "OpenAISDKAdapter",
    "TargetAdapter",
    "TargetSpec",
]
