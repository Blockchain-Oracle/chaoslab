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
from chaoslab_agent.patcher._fallback import PatcherEmptyResponseError, emit_fallback
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

# Bounded attempts before falling back to a generic patch; keeps a recipe
# shippable when Gemini emits unparseable JSON.
_MAX_ATTEMPTS = 3  # 1 initial + 2 retries

# Truncate raw LLM payloads in logs so observability stays manageable.
_RAW_LOG_LIMIT = 500


# ---------------------------------------------------------------------------
# Orchestrator pipeline factory — used by the SequentialAgent contract; the
# standalone Patcher class below is called directly by orchestrator-bypassed
# audit runs.
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
    # Safety-block / quota exhaustion returns empty body; raising a typed
    # exception stops retries burning Gemini quota
    # (consistent with judge.clustering._call_clusterer).
    if not response or not str(response).strip():
        msg = "Gemini returned an empty response (likely safety-block or quota)"
        raise PatcherEmptyResponseError(msg)
    return str(response)


# ---------------------------------------------------------------------------
# Resilience heuristic — public so callers can score recipes before signing.
# ---------------------------------------------------------------------------


def estimate_resilience_improvement(
    cluster_set: FailureClusterSet,
    patches: list[PromptPatch],
    diffs: list[ToolValidationDiff],
) -> float:
    """Heuristic in [0.0, 1.0]: 0.7·coverage + 0.3·density, rounded to 3 dp."""
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
    """Builds a HardeningRecipe from a FailureClusterSet via parallel per-cluster calls."""

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

        # Per-cluster try/except in _patch_one_cluster ensures one cluster's
        # Gemini failure does not torpedo the whole recipe; gather here uses
        # return_exceptions=True so even an unexpected helper exception
        # (e.g. future prompt-template KeyError) is contained per cluster.
        outcomes = await asyncio.gather(
            *(_patch_one_cluster(c) for c in cluster_set.clusters),
            return_exceptions=True,
        )

        all_patches: list[PromptPatch] = []
        all_diffs: list[ToolValidationDiff] = []
        fallback_cluster_ids: list[str] = []
        for cluster, outcome in zip(cluster_set.clusters, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                logger.exception(
                    "patcher cluster_id=%s helper raised; emitting fallback",
                    cluster.cluster_id,
                    exc_info=outcome,
                )
                patches, diffs, was_fallback = emit_fallback(cluster), [], True
            else:
                patches, diffs, was_fallback = outcome
            all_patches.extend(patches)
            all_diffs.extend(diffs)
            if was_fallback:
                fallback_cluster_ids.append(cluster.cluster_id)

        score = estimate_resilience_improvement(cluster_set, all_patches, all_diffs)
        regression_tests = _build_regression_cases(cluster_set)

        metadata: dict[str, Any] = {
            "clusterer_model": cluster_set.clusterer_model,
            "patcher_model": _JUDGE_MODEL_PREFIX,
            "total_failures": cluster_set.total_failures,
        }
        # Audit-fidelity: regulators need to tell pseudoknowledge patches
        # from real LLM-generated ones. Only include when non-empty so the
        # happy-path metadata stays terse.
        if fallback_cluster_ids:
            metadata["fallback_cluster_ids"] = fallback_cluster_ids

        return HardeningRecipe(
            recipe_id=new_recipe_id(),
            target_agent_id=target_agent_id,
            generated_at=datetime.now(UTC).isoformat(),
            cluster_set=cluster_set,
            prompt_patches=all_patches,
            tool_validation_diffs=all_diffs,
            regression_test_cases=regression_tests,
            estimated_resilience_improvement=score,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Per-cluster dispatch
# ---------------------------------------------------------------------------


async def _patch_one_cluster(
    cluster: FailureCluster,
) -> tuple[list[PromptPatch], list[ToolValidationDiff], bool]:
    """Returns (patches, diffs, was_fallback) for a single cluster."""
    initial_prompt = PER_CLUSTER_PATCHER_PROMPT.format(
        cluster_id=cluster.cluster_id,
        root_cause=cluster.root_cause,
        failure_count=cluster.failure_count,
        fault_classes=", ".join(cluster.fault_classes),
    )
    prompt = initial_prompt
    last_raw = ""
    last_error: str = ""
    for attempt in range(_MAX_ATTEMPTS):
        try:
            raw = await _call_patcher_llm(prompt)
        except PatcherEmptyResponseError as exc:
            # Empty / safety-blocked. Re-prompting with the same temperature
            # is unlikely to recover — fall back immediately.
            logger.warning(
                "patcher cluster_id=%s empty Gemini response; emitting fallback: %s",
                cluster.cluster_id,
                exc,
            )
            return emit_fallback(cluster), [], True
        except Exception as exc:
            # Transient (network, 5xx). Consume the retry budget rather
            # than short-circuit on the first hiccup.
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "patcher cluster_id=%s LLM call failed (attempt %d/%d): %s",
                cluster.cluster_id,
                attempt + 1,
                _MAX_ATTEMPTS,
                last_error,
            )
            if attempt == _MAX_ATTEMPTS - 1:
                break
            continue
        last_raw = raw
        parsed = _try_parse(raw, cluster=cluster)
        if parsed is not None:
            patches, diffs = parsed
            return patches, diffs, False
        if attempt == _MAX_ATTEMPTS - 1:
            break
        prompt = f"{RETRY_PROMPT}\n\n{initial_prompt}"
    logger.warning(
        "patcher cluster_id=%s exhausted %d attempts; emitting fallback. last_error=%s raw=%s",
        cluster.cluster_id,
        _MAX_ATTEMPTS,
        last_error,
        last_raw[:_RAW_LOG_LIMIT],
    )
    return emit_fallback(cluster), [], True


def _try_parse(
    raw: str,
    *,
    cluster: FailureCluster,
) -> tuple[list[PromptPatch], list[ToolValidationDiff]] | None:
    """Return (patches, diffs) on success, None on parse failure.

    Catches `TypeError` so a `null`-valued field in an otherwise-valid JSON
    body cannot escape and torpedo the whole recipe via asyncio.gather.
    """
    try:
        body: Any = json.loads(raw)
        if not isinstance(body, dict):
            msg = f"expected JSON object, got {type(body).__name__}"
            raise ValueError(msg)
        # `or []` normalises explicit nulls — `dict.get(k, [])` returns the
        # literal None when the key is present with a null value.
        raw_patches = body.get("prompt_patches") or []
        raw_diffs = body.get("tool_validation_diffs") or []
        patches = [PromptPatch.model_validate(p) for p in raw_patches]
        diffs = [ToolValidationDiff.model_validate(d) for d in raw_diffs]
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(
            "patcher cluster_id=%s parse failed: %s | raw=%s",
            cluster.cluster_id,
            exc,
            raw[:_RAW_LOG_LIMIT],
        )
        return None
    return patches, diffs


# ---------------------------------------------------------------------------
# Fallback patches — fault-class-aware so the audit shows a semantically
# sensible patch even when Gemini couldn't deliver.
# ---------------------------------------------------------------------------


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
    "PatcherEmptyResponseError",
    "build_patcher_agent",
    "estimate_resilience_improvement",
]
