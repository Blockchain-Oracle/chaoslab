"""Patcher.estimated_resilience_improvement heuristic invariants."""

from __future__ import annotations

from typing import Literal

import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.clustering import FailureClusterSet
from phoenix_audit_agent.patcher.agent import estimate_resilience_improvement
from phoenix_audit_agent.patcher.recipe import (
    FailureCluster,
    PromptPatch,
    ToolValidationDiff,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _cluster_set(n: int) -> FailureClusterSet:
    return FailureClusterSet(
        clusters=[
            FailureCluster(
                cluster_id=f"cluster_{i:08x}",
                root_cause=f"r{i}",
                failure_count=1,
                span_ids=[f"{i:016x}"],
                fault_classes=["malformed_tool_output"],
            )
            for i in range(n)
        ],
        total_failures=n,
    )


def _patch(
    section: Literal["system_prompt", "tool_description", "few_shot_example"] = "system_prompt",
) -> PromptPatch:
    return PromptPatch(section=section, operation="insert", after="x")


def _diff() -> ToolValidationDiff:
    return ToolValidationDiff(
        tool_name="lookup_order",
        operation="add_input_validator",
        code_patch="--- a\n+++ b\n@@ ...",
    )


def test_estimate_bounded_above_by_one() -> None:
    cs = _cluster_set(1)
    score = estimate_resilience_improvement(cs, [_patch()] * 20, [_diff()] * 20)
    assert 0.0 <= score <= 1.0


def test_estimate_bounded_below_by_zero() -> None:
    cs = _cluster_set(3)
    score = estimate_resilience_improvement(cs, [], [])
    assert score == 0.0


def test_estimate_increases_with_patch_count_until_capped() -> None:
    cs = _cluster_set(3)
    low = estimate_resilience_improvement(cs, [_patch()], [])
    mid = estimate_resilience_improvement(cs, [_patch(), _patch()], [_diff()])
    high = estimate_resilience_improvement(
        cs,
        [
            _patch("system_prompt"),
            _patch("tool_description"),
            _patch("few_shot_example"),
        ],
        [_diff(), _diff()],
    )
    assert low < mid <= high
    assert high <= 1.0


def test_estimate_deterministic_for_same_input() -> None:
    cs = _cluster_set(2)
    patches = [_patch(), _patch("tool_description")]
    diffs = [_diff()]
    first = estimate_resilience_improvement(cs, patches, diffs)
    second = estimate_resilience_improvement(cs, patches, diffs)
    assert first == second


def test_estimate_rounded_to_three_decimal_places() -> None:
    # The heuristic returns a float with stable precision so frontend
    # rendering ("46.7%") doesn't show 1.6e-16-style noise.
    cs = _cluster_set(4)
    score = estimate_resilience_improvement(cs, [_patch()] * 3, [_diff()])
    rounded = round(score, 3)
    assert score == rounded
