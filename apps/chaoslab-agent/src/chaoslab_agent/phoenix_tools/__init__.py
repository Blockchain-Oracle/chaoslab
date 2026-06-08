"""Custom ADK FunctionTool wrappers around Phoenix SDK calls.

Phoenix MCP intentionally does NOT expose `experiments.run_experiment` or
`spans.log_span_annotations` (per ADR-005). This package wraps both via
`phoenix.client.AsyncClient` so the Judge / Patcher sub-agents can call them
through the ADK tool interface.
"""

from chaoslab_agent.phoenix_tools.run_experiment import (
    ExperimentResult,
    phoenix_run_experiment_tool,
    run_phoenix_experiment,
)

__all__ = [
    "ExperimentResult",
    "phoenix_run_experiment_tool",
    "run_phoenix_experiment",
]
