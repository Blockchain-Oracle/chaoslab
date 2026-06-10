"""Judge sub-agent — LLM-as-judge rubrics + failure clustering (Epic 6)."""

from phoenix_audit_agent.judge._models import FailedSpan
from phoenix_audit_agent.judge.agent import JUDGE_NAME, build_judge_agent
from phoenix_audit_agent.judge.clustering import (
    ClusteringError,
    FailureCluster,
    FailureClusterSet,
    run_clustering,
)
from phoenix_audit_agent.judge.clustering_writeback import AnnotationWritebackError

__all__ = [
    "JUDGE_NAME",
    "AnnotationWritebackError",
    "ClusteringError",
    "FailedSpan",
    "FailureCluster",
    "FailureClusterSet",
    "build_judge_agent",
    "run_clustering",
]
