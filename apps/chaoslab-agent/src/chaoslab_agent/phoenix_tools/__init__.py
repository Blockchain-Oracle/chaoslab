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
from chaoslab_agent.phoenix_tools.write_annotation import (
    AnnotationResult,
    phoenix_write_annotation_tool,
    write_span_annotation,
)

__all__ = [
    "AnnotationResult",
    "ExperimentResult",
    "phoenix_run_experiment_tool",
    "phoenix_write_annotation_tool",
    "run_phoenix_experiment",
    "write_span_annotation",
]
