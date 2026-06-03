# Story — Patcher Sub-Agent (FailureClusterSet → HardeningRecipe)

**ID:** story-6.4-patcher-sub-agent
**Epic:** Epic 6 — Judge + clustering + hardening recipe
**Depends on:** story-6.2-failure-clustering (consumes `FailureClusterSet`), story-6.3-recipe-schema (emits `HardeningRecipe`)
**Estimate:** ~2h
**Status:** PENDING
**tags:** [backend, p0, patcher]

---

## User story

**As a** ChaosLab orchestrator that has just received a `FailureClusterSet` with 1-5 root-cause clusters
**I want to** dispatch each cluster to a Gemini 3.5 Flash call that produces (a) a `PromptPatch` addressing the cluster's root cause and (b) an optional `ToolValidationDiff` for tool-class failures, then aggregate everything into a single `HardeningRecipe` object with an `estimated_resilience_improvement` in `[0.0, 1.0]`
**So that** the Markdown emitter (S6.5) has a canonical recipe to render, the GitLab emitter (S6.6) has a canonical recipe to commit, the Receipt card in `chaoslab-web` displays "X root causes → 1 hardening recipe", and the full closed loop (per `PRD.md` demo moment §3-§6: "PATCH GENERATED → re-attack → cascade-flip green") has a real artifact

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py` — NEW — defines `Patcher` class with `async run(cluster_set: FailureClusterSet, target_agent_id: str) -> HardeningRecipe` entry point. Contains the per-cluster Gemini prompt template and the aggregation logic. ≤300 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py` — NEW — module-level constants for the per-cluster Patcher prompt (the structured "generate prompt patch + tool diff" prompt). ≤120 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/__init__.py` — UPDATE — append `from chaoslab_agent.patcher.agent import Patcher` re-export
- `apps/chaoslab-agent/tests/unit/patcher/test_agent.py` — NEW — ≥10 behavioral structural-assertion tests; uses a real `FailureClusterSet` fixture (3 clusters across all 4 fault classes), asserts the returned `HardeningRecipe` satisfies the pydantic invariants
- `apps/chaoslab-agent/tests/unit/patcher/test_estimated_resilience.py` — NEW — ≥3 tests asserting the `estimated_resilience_improvement` calculation: bounded `[0.0, 1.0]`, increases with cluster confidence, deterministic for the same input

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py exists
When  `uv run python -c "from chaoslab_agent.patcher.agent import Patcher; print('ok')"` runs
Then  stdout contains "ok" and exit code is 0

Given a FailureClusterSet with 3 clusters covering all 4 fault classes (clusters: C1=malformed_tool_output, C2=prompt_injection+context_poisoning, C3=latency_spike)
When  `await Patcher().run(cluster_set, target_agent_id="target_customer_support")` runs
Then  result is an instance of HardeningRecipe
And   len(result.prompt_patches) >= 1
And   len(result.tool_validation_diffs) >= 0
And   0.0 <= result.estimated_resilience_improvement <= 1.0
And   result.target_agent_id == "target_customer_support"
And   result.recipe_id matches r"^recipe_[a-z0-9]{12}$"
And   result.cluster_set == cluster_set.clusters
And   result.generated_at matches ISO 8601 (regex r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

Given a FailureClusterSet with 1 cluster of fault_class=["malformed_tool_output"]
When  Patcher.run executes
Then  len(result.tool_validation_diffs) >= 1
And   result.tool_validation_diffs[0].operation in ["add_input_validator", "add_output_validator"]

Given a FailureClusterSet with 1 cluster of fault_class=["latency_spike"]
When  Patcher.run executes
Then  len(result.tool_validation_diffs) >= 1
And   any(d.operation in ["add_retry_policy", "add_timeout"] for d in result.tool_validation_diffs)

Given a FailureClusterSet with 1 cluster of fault_class=["prompt_injection"]
When  Patcher.run executes
Then  len(result.prompt_patches) >= 1
And   any(p.section == "system_prompt" for p in result.prompt_patches)

Given the Patcher LLM call uses get_settings().JUDGE_LLM
When  the call is traced
Then  the LLM span attribute `llm.model_name` equals "gemini-3.5-flash" (ADR-007)

Given the Patcher receives a FailureClusterSet with 5 clusters (max allowed)
When  Patcher.run executes
Then  it dispatches 5 parallel Gemini calls via asyncio.gather (verified by span concurrency in trace)
And   all 5 results are aggregated into one HardeningRecipe

Given the Gemini call for cluster X returns malformed JSON
When  Patcher.run encounters the parse error
Then  it retries up to 2 times with a corrective re-prompt
And   if all retries fail, it logs a structured warning and emits a fallback PromptPatch with a generic root-cause description (does NOT raise — partial recipe is better than no recipe)

Given the Patcher produces a HardeningRecipe
When  HardeningRecipe.model_validate(result.model_dump()) is called
Then  no ValidationError is raised (round-trip ok)

Given `uv run pytest apps/chaoslab-agent/tests/unit/patcher/test_agent.py apps/chaoslab-agent/tests/unit/patcher/test_estimated_resilience.py -v` runs
When  the test suite completes
Then  ≥13 behavioral tests pass

Given the agent.py source file
When  `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py` runs
Then  exit code is 0 (file ≤300 LOC per task)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py` runs
When  output is checked
Then  zero results appear (§14 gate clean)

Given `grep -E "JUDGE_LLM|gemini-3\.5-flash" apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py` runs
When  output is checked
Then  at least 1 match found (ADR-007 explicit reference required)
```

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py
test -f apps/chaoslab-agent/tests/unit/patcher/test_agent.py
test -f apps/chaoslab-agent/tests/unit/patcher/test_estimated_resilience.py

# Imports resolve
uv run python -c "from chaoslab_agent.patcher.agent import Patcher; from chaoslab_agent.patcher.recipe import HardeningRecipe; print('ok')"

# ADR-007 reference
grep -qE "JUDGE_LLM|gemini-3\.5-flash" apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py

# Tests pass
cd apps/chaoslab-agent && uv run pytest tests/unit/patcher/test_agent.py tests/unit/patcher/test_estimated_resilience.py -v 2>&1 | tee /tmp/patcher-test.log && cd -
PASS_COUNT=$(grep -E "PASSED" /tmp/patcher-test.log | wc -l | tr -d ' ')
[ "$PASS_COUNT" -ge 13 ] || { echo "expected ≥13 tests, got $PASS_COUNT"; exit 1; }

# Lint + type-check + 400-line + 300-line per task ceiling
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/patcher/ || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/

LOC=$(wc -l < apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py | tr -d ' ')
[ "$LOC" -le 300 ] || { echo "agent.py has $LOC lines, exceeds per-task 300 LOC ceiling"; exit 1; }

# §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py

echo "story-6.4 verification: PASS"
```

---

## Notes for coding agent

### Patcher class shape

```python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/agent.py
from __future__ import annotations
import asyncio
import json
from datetime import datetime, UTC
from typing import Any

import structlog
from phoenix.evals import LLM

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher._prompts import PER_CLUSTER_PATCHER_PROMPT
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    ToolValidationDiff,
    new_recipe_id,
)

log = structlog.get_logger(__name__)


class Patcher:
    """Generates a HardeningRecipe from a FailureClusterSet.

    Per cluster: one Gemini 3.5 Flash call (ADR-007) producing structured JSON
    with a prompt_patch + optional tool_validation_diff. Per-cluster calls run
    in parallel via asyncio.gather. Aggregation builds the canonical recipe.
    """

    def __init__(self, llm: LLM | None = None) -> None:
        settings = get_settings()
        assert settings.JUDGE_LLM == "gemini-3.5-flash", "ADR-007 invariant"  # noqa: S101
        self._llm = llm or LLM(provider="google_genai", model=settings.JUDGE_LLM)

    async def run(
        self,
        cluster_set: FailureClusterSet,
        target_agent_id: str,
    ) -> HardeningRecipe:
        # 1. Dispatch one Gemini call per cluster, in parallel
        tasks = [self._patch_one_cluster(c) for c in cluster_set.clusters]
        results: list[tuple[FailureCluster, list[PromptPatch], list[ToolValidationDiff]]] = (
            await asyncio.gather(*tasks)
        )

        # 2. Flatten per-cluster outputs into recipe-level lists
        all_patches: list[PromptPatch] = []
        all_diffs: list[ToolValidationDiff] = []
        for _cluster, patches, diffs in results:
            all_patches.extend(patches)
            all_diffs.extend(diffs)

        # 3. Estimate resilience improvement (heuristic: cluster coverage × patch density)
        estimated = self._estimate_improvement(cluster_set, all_patches, all_diffs)

        # 4. Build regression test cases from cluster exemplars
        regression_tests = self._build_regression_cases(cluster_set)

        return HardeningRecipe(
            recipe_id=new_recipe_id(),
            target_agent_id=target_agent_id,
            generated_at=datetime.now(UTC).isoformat(),
            cluster_set=list(cluster_set.clusters),
            prompt_patches=all_patches,
            tool_validation_diffs=all_diffs,
            regression_test_cases=regression_tests,
            estimated_resilience_improvement=estimated,
            metadata={
                "clusterer_model": cluster_set.clusterer_model,
                "patcher_model": "gemini-3.5-flash",  # ADR-007
                "total_failures": cluster_set.total_failures,
            },
        )

    async def _patch_one_cluster(
        self, cluster: FailureCluster
    ) -> tuple[FailureCluster, list[PromptPatch], list[ToolValidationDiff]]:
        prompt = PER_CLUSTER_PATCHER_PROMPT.format(
            cluster_id=cluster.cluster_id,
            root_cause=cluster.root_cause,
            failure_count=cluster.failure_count,
            fault_classes=", ".join(cluster.fault_classes),
        )
        for attempt in range(3):  # 1 + 2 retries
            try:
                raw = await self._llm.acomplete(prompt)
                parsed = json.loads(raw)
                patches = [PromptPatch.model_validate(p) for p in parsed.get("prompt_patches", [])]
                diffs = [ToolValidationDiff.model_validate(d) for d in parsed.get("tool_validation_diffs", [])]
                return cluster, patches, diffs
            except (json.JSONDecodeError, ValueError) as e:
                log.warning("patcher_parse_failed", cluster_id=cluster.cluster_id, attempt=attempt, error=str(e))
                if attempt == 2:
                    # Fallback: emit a generic patch so the recipe is not empty
                    return cluster, [self._fallback_patch(cluster)], []
        return cluster, [], []  # unreachable
```

### Per-cluster prompt template (in `_prompts.py`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/_prompts.py
"""Patcher LLM prompts. Separated from agent.py to keep per-task LOC ceiling."""
from __future__ import annotations

PER_CLUSTER_PATCHER_PROMPT = """You are ChaosLab's Patcher. Given one cluster of agent failures
with a single root cause, generate (a) one or more PromptPatch entries that fix the root cause
by editing the agent's system prompt, tool descriptions, or few-shot examples, and (b) optionally
one or more ToolValidationDiff entries that add input/output validators, retry policies, or
timeouts to the affected tools.

CLUSTER:
- cluster_id: {cluster_id}
- root_cause: {root_cause}
- failure_count: {failure_count}
- fault_classes: {fault_classes}

FAULT-CLASS → FIX MAPPING (guidance, not constraint):
- malformed_tool_output → add_input_validator OR add_output_validator + prompt rule "validate tool outputs"
- prompt_injection → system_prompt insert with refusal pattern
- context_poisoning → system_prompt insert with provenance-check rule
- latency_spike → add_retry_policy AND add_timeout

OUTPUT STRICT JSON ONLY (no markdown fences, no prose):
{{
  "prompt_patches": [
    {{
      "section": "system_prompt" | "tool_description" | "few_shot_example",
      "operation": "insert" | "replace" | "append",
      "before": <string|null>,
      "after": "<the patch text>"
    }}
  ],
  "tool_validation_diffs": [
    {{
      "tool_name": "<tool name from cluster context>",
      "operation": "add_input_validator" | "add_output_validator" | "add_retry_policy" | "add_timeout",
      "code_patch": "<unified diff format>"
    }}
  ]
}}

CONSTRAINTS:
- prompt_patches MUST contain at least 1 entry per cluster.
- tool_validation_diffs SHOULD contain at least 1 entry for malformed_tool_output and latency_spike clusters.
- When operation == "replace", "before" MUST be the exact text being replaced.
- code_patch MUST be valid unified-diff format starting with "--- " and "+++ ".
"""
```

### Estimated resilience improvement heuristic

```python
def _estimate_improvement(
    self,
    cluster_set: FailureClusterSet,
    patches: list[PromptPatch],
    diffs: list[ToolValidationDiff],
) -> float:
    """Heuristic in [0.0, 1.0]: cluster coverage × patch density.

    Coverage = fraction of clusters that received at least one patch or diff.
    Density = min(1.0, (len(patches) + len(diffs)) / (2 * len(clusters))).
    Improvement = coverage * 0.7 + density * 0.3  (coverage weighted higher).
    """
    n_clusters = len(cluster_set.clusters)
    if n_clusters == 0:
        return 0.0
    covered = len({p.section for p in patches}) + (1 if diffs else 0)
    coverage = min(1.0, covered / n_clusters)
    density = min(1.0, (len(patches) + len(diffs)) / (2.0 * n_clusters))
    improvement = coverage * 0.7 + density * 0.3
    return round(min(1.0, max(0.0, improvement)), 3)
```

### Architecture context

- **ADR-007 (mandatory):** Gemini 3.5 Flash is the Patcher LLM. The assert in `__init__` enforces this at construction time so a misconfigured deploy fails-fast at startup, not mid-demo.
- **Parallel dispatch via `asyncio.gather`:** for 5 clusters this saves ~4× wall-clock vs sequential. Per `architecture.md` PRD §"Demo moment" the patch must fire at 1:50; if patcher runs 5 sequential Gemini calls at ~3s each = 15s budget, gather brings it to ~3s.
- **Partial-recipe-on-parse-failure (graceful degradation):** if Gemini emits malformed JSON for cluster X, fall back to a generic `PromptPatch` based on the cluster's `root_cause`. Do NOT raise — the demo must complete. Log a structured warning so observability captures it.
- **Heuristic improvement estimate:** the `estimated_resilience_improvement` is intentionally heuristic, not predicted from a model. The REAL improvement comes from re-attack phase (per `PRD.md` §3 wow moment 2:15). The heuristic gives the frontend something to display before re-attack runs.
- **`HardeningRecipe.cluster_set` must equal `cluster_set.clusters` byte-for-byte.** The recipe carries the cluster context so the Markdown emitter (S6.5) can render "Cluster C1: no input validation → fixed by Patch P1." Tests assert this equality.
- **§14 gate:** the Patcher's Gemini call is REAL. Tests pass `llm=LLM(provider="google_genai", model="gemini-3.5-flash")` and use `respx` to intercept the HTTP call at the boundary, returning recorded fixture responses. NO `_mock_patcher_response()` helpers in `src/`.

### Test guidance

- **Structural assertions on pydantic schemas:** for each fault-class → fix mapping, write one test asserting the right `ToolValidationDiff.operation` appears. Don't assert on natural-language patch text — that's LLM output, not deterministic.
- **`recipe.model_validate(recipe.model_dump())` round-trip:** asserts the recipe is self-consistent. If a field has a custom validator that triggers on construction but not on round-trip, you'll catch it here.
- **`asyncio.gather` concurrency test:** use `respx` to intercept Gemini HTTPS calls, add a 100ms delay to each, dispatch 5 clusters, assert wall-clock < 500ms (proves parallelism).
- **Test JUDGE_LLM enforcement:** instantiate `Patcher()` with `settings.JUDGE_LLM` temporarily overridden to `"gemini-pro"` → assert `AssertionError` raised. Use `monkeypatch.setenv` to override.

### Known pitfalls

- **`asyncio.gather` propagates the first exception** — if cluster 3's Gemini call raises, clusters 1+2 results are discarded. Wrap each `_patch_one_cluster` in try/except internally (as the retry loop shows) so a partial recipe still ships.
- **`datetime.now(UTC).isoformat()` returns `"2026-06-02T14:30:00+00:00"`** — the trailing `+00:00` may not match the `Z` ISO 8601 variant. Test with regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` (no anchor for timezone). The frontend treats both as valid.
- **`phoenix.evals.LLM.acomplete()` may not exist on all phoenix-evals versions.** Verify the actual API: it might be `LLM.generate()` or `LLM.aevaluate()`. Check via `context7` before implementing.
- **`PromptPatch.model_validate` from Gemini-emitted JSON may raise on `operation == "replace"` without `before`.** The retry loop catches this. Don't add `before=""` as a workaround — the schema's `model_validator` rejects empty `before` for replace ops (per S6.3 schema).
- **`cluster_set` parameter type is `FailureClusterSet`, not `list[FailureCluster]`.** The wrapper carries `total_failures` + `clusterer_model` metadata that the recipe's `metadata` dict surfaces. Don't flatten.
- **Cross-reference:** `architecture/04 §6.1-6.3` (recipe components + sample Markdown shape); `architecture.md` ADR-007 (Gemini 3.5 Flash mandate); `architecture.md` §"Data flow" step 7 (Patcher fires after Judge).
