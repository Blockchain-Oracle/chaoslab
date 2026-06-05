"""target_agent — Phoenix Audit's deliberately-naive demo target.

Re-exports `root_agent` for ADK discovery (`adk web`, A2A, etc.) and
`a2a_app` for ASGI hosting (`uv run target-agent`, Cloud Run).
"""

from target_agent.agent import root_agent
from target_agent.server import a2a_app

__all__ = ["a2a_app", "root_agent"]
