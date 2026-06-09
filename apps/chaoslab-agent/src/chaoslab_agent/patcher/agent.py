"""Patcher sub-agent — FailureClusterSet → HardeningRecipe."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from chaoslab_agent.adk_types import LlmAgent
from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.judge.rubrics._llm import get_judge_llm
from chaoslab_agent.patcher._prompts import PER_CLUSTER_PATCHER_PROMPT, RETRY_PROMPT
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
    new_recipe_id,
)

logger = logging.getLogger(__name__)

# JUDGE_LLM (ADR-007) is the locked model family.
_JUDGE_MODEL_PREFIX = "gemini-3.5-flash"

# Max retries before falling back to a generic prompt patch so the demo
# completes even when Gemini emits unparseable JSON.
_MAX_RETRIES = 2

# Truncate raw LLM payloads in logs so debug output stays manageable.
_RAW_LOG_LIMIT = 500


# ---------------------------------------------------------------------------
# Existing orchestrator pipeline factory (S4.x) — preserved for the
# SequentialAgent contract; S6.4 adds the standalone Patcher class below.
# ---------------------------------------------------------------------------

PATCHER_NAME = "Patcher"
PATCHER_OUTPUT_KEY = "patcher_result"

_DESCRIPTION = (
    "Generates a HardeningRecipe from clustered failures and emits a Markdown artifact + GitLab MR"
)
_INSTRUCTION = (
    "STUB: given upstream judge output {judge_result}, emit a JSON object "
    "with keys ['recipe_id', 'prompt_patches', 'tool_validation_diffs']. "
    "Stub-mode response is acceptable."
)


def build_patcher_agent() -> LlmAgent:
    """Construct the Patcher for the SequentialAgent pipeline."""
    return LlmAgent(
        name=PATCHER_NAME,
        description=_DESCRIPTION,
        instruction=_INSTRUCTION,
        model=get_settings().judge_llm,
        output_key=PATCHER_OUTPUT_KEY,
    )


# ---------------------------------------------------------------------------
# LLM boundary — module-level so tests can monkeypatch a single symbol
# instead of plumbing a client through every call site.
# ---------------------------------------------------------------------------


async def _call_patcher_llm(prompt: str) -> str:
    llm = get_judge_llm()
    response = await llm.async_generate_text(prompt=prompt, temperature=0.2)
    return str(response)


# ---------------------------------------------------------------------------
# Resilience heuristic — public so tests can exercise it without
# constructing a full Patcher.
# ---------------------------------------------------------------------------


def estimate_resilience_improvement(
    cluster_set: FailureClusterSet,
    patches: list[PromptPatch],
    diffs: list[ToolValidationDiff],
) -> float:
    """Heuristic in [0.0, 1.0]: cluster coverage x patch density.

    coverage = unique patch sections + (1 if any diffs) capped at n_clusters.
    density  = (len(patches) + len(diffs)) / (2 x n_clusters), capped at 1.
    score    = 0.7 x coverage + 0.3 x density, rounded to 3 dp.
    """
    n_clusters = len(cluster_set.clusters)
    if n_clusters == 0:
        return 0.0
    covered = len({p.section for p in patches}) + (1 if diffs else 0)
    coverage = min(1.0, covered / n_clusters)
    density = min(1.0, (len(patches) + len(diffs)) / (2.0 * n_clusters))
    score = coverage * 0.7 + density * 0.3
    return round(min(1.0, max(0.0, score)), 3)


# ---------------------------------------------------------------------------
# Patcher class
# ---------------------------------------------------------------------------


class Patcher:
    """Generates a HardeningRecipe from a FailureClusterSet.

    Per cluster: one Gemini 3.5 Flash call (ADR-007) producing structured
    JSON with a prompt_patch + optional tool_validation_diff. Per-cluster
    calls run in parallel via asyncio.gather. Aggregation builds the
    canonical recipe.
    """

    async def run(
        self,
        cluster_set: FailureClusterSet,
        target_agent_id: str,
    ) -> HardeningRecipe:
        settings = get_settings()
        if not settings.JUDGE_LLM.startswith(_JUDGE_MODEL_PREFIX):
            msg = (
                f"ADR-007 invariant violated: JUDGE_LLM={settings.JUDGE_LLM!r} "
                f"but Patcher requires the {_JUDGE_MODEL_PREFIX!r} family"
            )
            raise RuntimeError(msg)

        # asyncio.gather propagates the first exception — catching here
        # lets one cluster's Gemini failure not torpedo the whole recipe.
        per_cluster = await asyncio.gather(
            *(_patch_one_cluster(c) for c in cluster_set.clusters),
            return_exceptions=False,
        )

        all_patches: list[PromptPatch] = []
        all_diffs: list[ToolValidationDiff] = []
        for patches, diffs in per_cluster:
            all_patches.extend(patches)
            all_diffs.extend(diffs)

        score = estimate_resilience_improvement(cluster_set, all_patches, all_diffs)
        regression_tests = _build_regression_cases(cluster_set)

        return HardeningRecipe(
            recipe_id=new_recipe_id(),
            target_agent_id=target_agent_id,
            generated_at=datetime.now(UTC).isoformat(),
            cluster_set=cluster_set,
            prompt_patches=all_patches,
            tool_validation_diffs=all_diffs,
            regression_test_cases=regression_tests,
            estimated_resilience_improvement=score,
            metadata={
                "clusterer_model": cluster_set.clusterer_model,
                "patcher_model": _JUDGE_MODEL_PREFIX,
                "total_failures": cluster_set.total_failures,
            },
        )


# ---------------------------------------------------------------------------
# Per-cluster dispatch
# ---------------------------------------------------------------------------


async def _patch_one_cluster(
    cluster: FailureCluster,
) -> tuple[list[PromptPatch], list[ToolValidationDiff]]:
    prompt = PER_CLUSTER_PATCHER_PROMPT.format(
        cluster_id=cluster.cluster_id,
        root_cause=cluster.root_cause,
        failure_count=cluster.failure_count,
        fault_classes=", ".join(cluster.fault_classes),
    )
    last_raw = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            raw = await _call_patcher_llm(prompt)
        except Exception as exc:
            logger.warning(
                "patcher cluster_id=%s LLM call failed (attempt %d/%d): %s",
                cluster.cluster_id,
                attempt + 1,
                _MAX_RETRIES + 1,
                exc,
            )
            return [_fallback_patch(cluster)], []
        last_raw = raw
        patches, diffs = _try_parse(raw, cluster=cluster)
        if patches is not None and diffs is not None:
            return patches, diffs
        if attempt == _MAX_RETRIES:
            break
        prompt = f"{RETRY_PROMPT}\n\n{prompt}"
    logger.warning(
        "patcher cluster_id=%s exhausted %d retries; emitting fallback. raw=%s",
        cluster.cluster_id,
        _MAX_RETRIES,
        last_raw[:_RAW_LOG_LIMIT],
    )
    return [_fallback_patch(cluster)], []


def _try_parse(
    raw: str,
    *,
    cluster: FailureCluster,
) -> tuple[list[PromptPatch] | None, list[ToolValidationDiff] | None]:
    try:
        body: Any = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("expected object")
        patches = [PromptPatch.model_validate(p) for p in body.get("prompt_patches", [])]
        diffs = [
            ToolValidationDiff.model_validate(d) for d in body.get("tool_validation_diffs", [])
        ]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "patcher cluster_id=%s parse failed: %s",
            cluster.cluster_id,
            exc,
        )
        return None, None
    return patches, diffs


def _fallback_patch(cluster: FailureCluster) -> PromptPatch:
    return PromptPatch(
        section="system_prompt",
        operation="insert",
        before=None,
        after=(
            f"Fallback patch (cluster {cluster.cluster_id}): "
            f"address root cause '{cluster.root_cause}'. "
            "Add explicit validation and refusal rules for "
            f"{', '.join(cluster.fault_classes)} failure modes."
        ),
    )


def _build_regression_cases(cluster_set: FailureClusterSet) -> list[RegressionTestCase]:
    return [
        RegressionTestCase(
            input=f"Replay cluster {c.cluster_id} exemplar",
            expected=f"Agent handles {c.root_cause} without failure",
        )
        for c in cluster_set.clusters
    ]


__all__ = [
    "PATCHER_NAME",
    "PATCHER_OUTPUT_KEY",
    "Patcher",
    "build_patcher_agent",
    "estimate_resilience_improvement",
]
