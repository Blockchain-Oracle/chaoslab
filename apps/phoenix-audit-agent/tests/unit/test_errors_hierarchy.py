"""errors.py promises every domain error derives from PhoenixAuditError.

The docstring claim ("All Phoenix Audit errors derive from PhoenixAuditError")
must be TRUE — callers at the orchestrator seam rely on `except
PhoenixAuditError` covering the project's known-failure surface.
"""

from __future__ import annotations

import pytest

from phoenix_audit_agent.errors import PhoenixAuditError
from phoenix_audit_agent.judge.clustering import ClusteringError
from phoenix_audit_agent.judge.clustering_writeback import AnnotationWritebackError
from phoenix_audit_agent.judge.rubrics._base import (
    PhoenixEvalEmptyError,
    RubricInputMissingError,
)
from phoenix_audit_agent.patcher._fallback import PatcherEmptyResponseError
from phoenix_audit_agent.patcher._gitlab_mcp_client import GitLabMcpError
from phoenix_audit_agent.patcher._gitlab_rest_client import GitLabRestClientError
from phoenix_audit_agent.patcher.gitlab_emitter import GitLabEmitterError
from phoenix_audit_agent.patcher.markdown_emitter import (
    BucketMissingError,
    BucketProbeError,
    BucketUnreachableError,
    MarkdownEmitterError,
    RecipeAlreadyExistsError,
)

_DOMAIN_ERRORS = [
    ClusteringError,
    AnnotationWritebackError,
    RubricInputMissingError,
    PhoenixEvalEmptyError,
    PatcherEmptyResponseError,
    GitLabMcpError,
    GitLabRestClientError,
    GitLabEmitterError,
    MarkdownEmitterError,
    RecipeAlreadyExistsError,
    BucketProbeError,
    BucketMissingError,
    BucketUnreachableError,
]


@pytest.mark.parametrize("exc", _DOMAIN_ERRORS, ids=lambda e: e.__name__)
def test_derives_from_phoenix_audit_error(exc: type[Exception]) -> None:
    assert issubclass(exc, PhoenixAuditError)


def test_legacy_stdlib_bases_preserved() -> None:
    """Dual-basing keeps existing `except RuntimeError` / `except ValueError`
    call sites working — the rebase must not change catch behavior."""
    assert issubclass(ClusteringError, RuntimeError)
    assert issubclass(MarkdownEmitterError, RuntimeError)
    assert issubclass(RubricInputMissingError, ValueError)
