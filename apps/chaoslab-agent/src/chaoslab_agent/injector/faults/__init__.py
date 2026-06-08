"""Fault primitives for the Phoenix Audit Injector.

Architectural inspiration from deepankarm/agent-chaos (Apache-2.0, pinned
commit ``32beff46a28ca043e252095e6cc62ffe2010e645``); no source code is
copied (see NOTICE). The four MVP fault classes F1-F4 are implemented
natively against the Google ADK callback system per docs/architecture.md
ADR-006 (amended 2026-06-03) and architecture/04 §8.

This module is intentionally empty pending S5.2-S5.5; re-exports for
``MalformedToolOutputFault`` etc. will land in those stories.
"""
