"""Module entry for ADK discovery (`adk web`, etc.).

This file is intentionally minimal in S2.1 — it just re-exports `root_agent`
so ADK's discovery loaders find it. The actual A2A server wiring
(`to_a2a()` + uvicorn + `[project.scripts]` entry point) lands in S2.2.

Phoenix Audit connects to this target via A2A in production. For local
dev, `adk web .` will pick this up automatically.
"""

from __future__ import annotations

from target_agent.agent import root_agent

__all__ = ["root_agent"]
