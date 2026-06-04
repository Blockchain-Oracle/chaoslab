"""target_agent — Phoenix Audit's deliberately-naive demo target.

Re-exports `root_agent` for ADK discovery (`adk web`, A2A, etc.).
"""

from target_agent.agent import root_agent

__all__ = ["root_agent"]
