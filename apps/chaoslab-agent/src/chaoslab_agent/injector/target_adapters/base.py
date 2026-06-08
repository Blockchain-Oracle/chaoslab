"""TargetAdapter contract — framework-agnostic surface every adapter implements.

This module is FROZEN per ADR-002. The five Pydantic schemas + the ABC define
the call shape that Tier 1 (ADK), Tier 2 (LangChain / CrewAI / OpenAI Agents
SDK), and Tier 3 (HTTP black-box) adapters all conform to. Changing this
contract without an ADR amendment breaks every downstream adapter implementation
plus the Injector sub-agent that consumes them (see ADR-002 + the current DAG
in docs/sprint-status.yaml for the live dependency list).

The module must NOT import google.adk.* — ADK lives in adk_adapter.py.
Importing this base must work in a process with zero ADK installed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


class AdapterTier(StrEnum):
    """Which adapter tier the target maps to.

    Tier 1: native ADK (richest trace fidelity).
    Tier 2: framework-aware (LangChain / CrewAI / OpenAI Agents SDK).
    Tier 3: HTTP black-box (no framework — fingerprinted behaviorally).

    DRIFT GUARD: this enum is the canonical implementation of ADR-002's tier
    taxonomy. test_adapter_tier_matches_adr_002 in test_base.py asserts the
    value set against a hardcoded literal; any new tier must update both files
    in the same PR.
    """

    TIER1_ADK = "tier1_adk"
    TIER2_LANGCHAIN = "tier2_langchain"
    TIER2_CREWAI = "tier2_crewai"
    TIER2_OPENAI_SDK = "tier2_openai_sdk"
    TIER3_HTTP_BLACKBOX = "tier3_http_blackbox"


class TargetSpec(BaseModel):
    """Connection descriptor for a target agent.

    ``auth`` carries credentials and is typed as ``dict[str, SecretStr]`` so the
    structlog ``_mask_secrets`` processor (apps/chaoslab-agent/.../observability.py)
    redacts each value via its ``SecretStr`` isinstance branch. ``str(secret)``,
    ``repr(secret)``, and ``model_dump_json(spec)`` all render as ``'**********'``
    by pydantic default; ``model_dump()`` returns ``SecretStr`` instances rather
    than raw strings, so a caller that JSON-serializes the dict downstream
    cannot accidentally surface the value either.

    The ``json_schema_extra={"sensitive": ["auth"]}`` marker is a forward
    reference for structural scrubbing once observability gains metadata-driven
    redaction; it is not load-bearing today (observability keys off kwarg-name
    substrings + the ``SecretStr`` isinstance check, neither of which reads this
    marker).
    """

    model_config = ConfigDict(json_schema_extra={"sensitive": ["auth"]})

    tier: AdapterTier
    url: HttpUrl
    agent_card: dict[str, Any] | None = None
    framework: str | None = None
    auth: dict[str, SecretStr] | None = None
    timeout_s: float = Field(default=30.0, ge=0.1, le=300.0)


class AdapterInvocation(BaseModel):
    """One prompt sent to the target, with optional fault descriptor.

    ``fault_config`` is left as a free dict here; Epic 5 will introduce typed
    fault descriptors (F1-F4) and a serializer that fills this field.
    """

    prompt: str = Field(min_length=1)
    fault_config: dict[str, Any] | None = None
    session_id: str | None = None


class AdapterResult(BaseModel):
    """Outcome of one ``invoke()`` call.

    Failure convention: adapters MUST raise on transport / protocol / framework
    errors. The ``error`` field is reserved for soft-failure semantics in
    Epic 5+ (e.g. a fault deliberately caused the target to misbehave but the
    transport completed) and is ``None`` for every clean-success and every
    raised-exception path. Concurrently populating ``response`` and ``error``
    is permitted only in the soft-failure case.

    ``span_ids`` link to spans recorded during this invoke. Tier 1/2 capture
    the target's own framework spans. Tier 3 (HTTP black-box) captures the
    adapter's outer wrapper span only — the opaque target produces no
    auditor-observable spans (story 3.6 wires the wrapper-span ID injection).
    """

    response: str
    span_ids: list[str] = Field(default_factory=list)
    duration_ms: float = Field(ge=0.0)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterFingerprint(BaseModel):
    """Discovery + behavioral metadata about the target.

    ``discovery_path`` records which probe from context/05 §13 succeeded
    (well-known agent card / OpenAPI / raw HTTP). ``behavioral_signals`` is
    populated by Tier 3 fingerprinting (system-prompt extraction, style
    classifier, inter-token timing — wired by the HTTP black-box adapter).
    """

    tier: AdapterTier
    framework: str | None = None
    agent_card: dict[str, Any] | None = None
    discovery_path: str | None = None
    behavioral_signals: dict[str, Any] | None = None


class TargetAdapter(ABC):
    """Abstract base for every target adapter — Tier 1/2/3 subclass this."""

    def __init__(self, spec: TargetSpec) -> None:
        self.spec = spec

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection / fetch metadata. Idempotent."""

    @abstractmethod
    async def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        """Send one prompt + optional fault config; capture response + span IDs."""

    @abstractmethod
    async def fingerprint(self) -> AdapterFingerprint:
        """Return discovery + behavioral metadata about the target."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Release connections, clients, sockets."""
