"""target_agent — Phoenix Audit's deliberately-naive demo target.

Re-exports `root_agent` for ADK discovery (`adk web`, A2A, etc.).
For the ASGI app, import explicitly:  `from target_agent.server import a2a_app`.

Why not re-export `a2a_app` here: doing so would force every import of
`target_agent.*` to instantiate the full A2A machinery (A2AStarletteApplication,
InMemoryTaskStore, AgentCardBuilder) and emit 4 EXPERIMENTAL warnings per
import — including all S2.1 unit tests that only need `target_agent.tools`.
"""

from target_agent.agent import root_agent

__all__ = ["root_agent"]
