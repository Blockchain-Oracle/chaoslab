"""Judge sub-agent — LLM-as-judge rubrics + failure clustering (Epic 6)."""

from chaoslab_agent.judge._models import FailedSpan
from chaoslab_agent.judge.agent import JUDGE_NAME, build_judge_agent
from chaoslab_agent.judge.clustering import (
    ClusteringError,
    FailureCluster,
    FailureClusterSet,
    run_clustering,
)

__all__ = [
    "JUDGE_NAME",
    "ClusteringError",
    "FailedSpan",
    "FailureCluster",
    "FailureClusterSet",
    "build_judge_agent",
    "run_clustering",
]
