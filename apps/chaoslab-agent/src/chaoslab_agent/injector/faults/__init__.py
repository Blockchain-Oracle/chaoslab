"""Public surface for the Phoenix Audit Injector fault primitives.

Architectural inspiration from ``deepankarm/agent-chaos`` (Apache-2.0); no
source code is copied. The pinned upstream commit is recorded in repo-root
NOTICE (single source of truth). The four MVP fault classes
(``MalformedToolOutputFault``, ``PromptInjectionFault``,
``ContextPoisoningFault``, ``LatencySpikeFault``) are implemented natively
against the Google ADK callback system per docs/architecture.md ADR-006
(amended 2026-06-03) and architecture/04 §8.

Each fault class is re-exported from this package once its module lands.
"""
