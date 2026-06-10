"""SequentialAgent orchestrator: Injector -> Judge -> Patcher pipeline.

State flows via ADK's `output_key` + `{key}` template substitution
(reference: research/.../architecture/03-multi-agent-patterns.md §3.1). The
SequentialAgent's deterministic execution order is the load-bearing invariant
for trace-as-assertion gates: parent span name + 3 ordered children.

Sub-agents are produced by per-module factories so production can swap
implementations without touching this file. The stubs are real `LlmAgent`
instances backed by real Gemini, not mocks; the `STUB:` prefix inside
instruction strings is the §14 carve-out documented in the story file.

ADR-012: ADK's `SequentialAgent` is the deprecated-but-pinned API per the
google-adk[a2a]>=2.1.0,<3.0.0 constraint. Workflow (the v3 replacement) is
out-of-scope until the upstream major version bump is planned.
"""

from __future__ import annotations

# All `google.adk.*` types flow through the quarantine module per ADR-001 +
# best-practices/03 §3. ADR-012: SequentialAgent is the pinned-deprecated ADK 2.x
# workflow primitive; the v3 Workflow replacement is out of scope.
from phoenix_audit_agent.adk_types import SequentialAgent  # ty: ignore[deprecated]
from phoenix_audit_agent.injector.agent import build_injector_agent
from phoenix_audit_agent.judge.agent import build_judge_agent
from phoenix_audit_agent.patcher.agent import build_patcher_agent

ORCHESTRATOR_NAME = "PhoenixAuditOrchestrator"


def build_orchestrator() -> SequentialAgent:  # ty: ignore[deprecated]
    """Construct the three-stage Phoenix Audit pipeline.

    Returns a fresh `SequentialAgent` instance per call so tests can hold
    independent runners without state leakage. Production callers should
    cache the result at app startup via `functools.lru_cache` or app state.
    """
    return SequentialAgent(  # ty: ignore[deprecated]
        name=ORCHESTRATOR_NAME,
        sub_agents=[
            build_injector_agent(),
            build_judge_agent(),
            build_patcher_agent(),
        ],
    )
