"""Patcher class behavioral tests."""

from __future__ import annotations

import asyncio
import json
import re

import pytest

import chaoslab_agent.patcher.agent as patcher_module
from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.judge.rubrics import FaultClass
from chaoslab_agent.patcher.agent import Patcher
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _cluster(
    cluster_id: str,
    span_ids: list[str],
    fault_classes: list[FaultClass],
) -> FailureCluster:
    return FailureCluster(
        cluster_id=cluster_id,
        root_cause=f"root cause for {cluster_id}",
        failure_count=len(span_ids),
        span_ids=span_ids,
        fault_classes=fault_classes,
    )


def _cluster_set_3_clusters() -> FailureClusterSet:
    return FailureClusterSet(
        clusters=[
            _cluster(
                "cluster_aaaaaaaa",
                ["0000000000000001", "0000000000000002"],
                ["malformed_tool_output"],
            ),
            _cluster(
                "cluster_bbbbbbbb",
                ["0000000000000003", "0000000000000004"],
                ["prompt_injection", "context_poisoning"],
            ),
            _cluster(
                "cluster_cccccccc",
                ["0000000000000005"],
                ["latency_spike"],
            ),
        ],
        total_failures=5,
    )


def _patch_for(fault_classes: list[FaultClass]) -> str:
    """Build a valid JSON response from the Patcher LLM for one cluster."""
    has_tool = any(fc in {"malformed_tool_output", "latency_spike"} for fc in fault_classes)
    has_prompt_injection = "prompt_injection" in fault_classes
    has_latency = "latency_spike" in fault_classes
    tool_op = "add_retry_policy" if has_latency else "add_input_validator"
    return json.dumps(
        {
            "prompt_patches": [
                {
                    "section": "system_prompt" if has_prompt_injection else "tool_description",
                    "operation": "insert",
                    "before": None,
                    "after": f"Patch for {','.join(fault_classes)}",
                }
            ],
            "tool_validation_diffs": (
                [
                    {
                        "tool_name": "lookup_order",
                        "operation": tool_op,
                        "code_patch": "--- a/tools.py\n+++ b/tools.py\n@@ ...",
                    }
                ]
                if has_tool
                else []
            ),
        }
    )


class _Scripted:
    """Stand-in for the per-cluster LLM call.

    Maps `cluster_id` → response. Records call latencies so tests can verify
    parallel dispatch via wall-clock.
    """

    def __init__(
        self,
        per_cluster: dict[str, str | Exception],
        *,
        delay_s: float = 0.0,
    ) -> None:
        self._per_cluster = per_cluster
        self._delay_s = delay_s
        self.calls: list[str] = []

    async def __call__(self, prompt: str) -> str:
        # The cluster_id appears in the rendered prompt; extract it so the
        # stub can dispatch deterministically without re-implementing
        # prompt formatting.
        m = re.search(r"cluster_id:\s*(\S+)", prompt)
        assert m, "prompt template changed; test stub needs a re-look"
        cluster_id = m.group(1)
        self.calls.append(cluster_id)
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        resp = self._per_cluster.get(cluster_id, "")
        if isinstance(resp, Exception):
            raise resp
        return resp


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_patcher_returns_hardening_recipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted(
        {
            "cluster_aaaaaaaa": _patch_for(["malformed_tool_output"]),
            "cluster_bbbbbbbb": _patch_for(["prompt_injection", "context_poisoning"]),
            "cluster_cccccccc": _patch_for(["latency_spike"]),
        }
    )
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target_customer_support")
    assert isinstance(recipe, HardeningRecipe)
    assert recipe.target_agent_id == "target_customer_support"
    assert len(recipe.prompt_patches) >= 1
    assert 0.0 <= recipe.estimated_resilience_improvement <= 1.0


async def test_patcher_recipe_id_matches_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert re.match(r"^recipe_[a-z0-9]{12}$", recipe.recipe_id)


async def test_patcher_generated_at_is_iso_8601(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", recipe.generated_at)


async def test_patcher_preserves_cluster_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert recipe.cluster_set == cs


async def test_patcher_recipe_round_trips_through_model_validate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    HardeningRecipe.model_validate(recipe.model_dump())


async def test_patcher_metadata_records_clusterer_and_patcher_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert recipe.metadata["clusterer_model"] == "gemini-3.5-flash"
    assert recipe.metadata["patcher_model"] == "gemini-3.5-flash"
    assert recipe.metadata["total_failures"] == cs.total_failures


# ---------------------------------------------------------------------------
# Fault-class -> fix-shape mapping
# ---------------------------------------------------------------------------


async def test_malformed_tool_output_cluster_emits_tool_validation_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[_cluster("cluster_aaaaaaaa", ["0000000000000001"], ["malformed_tool_output"])],
        total_failures=1,
    )
    stub = _Scripted({"cluster_aaaaaaaa": _patch_for(["malformed_tool_output"])})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert len(recipe.tool_validation_diffs) >= 1
    assert recipe.tool_validation_diffs[0].operation in {
        "add_input_validator",
        "add_output_validator",
    }


async def test_latency_spike_cluster_emits_retry_or_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[_cluster("cluster_cccccccc", ["0000000000000001"], ["latency_spike"])],
        total_failures=1,
    )
    stub = _Scripted({"cluster_cccccccc": _patch_for(["latency_spike"])})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert any(
        d.operation in {"add_retry_policy", "add_timeout"} for d in recipe.tool_validation_diffs
    )


async def test_prompt_injection_cluster_emits_system_prompt_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[_cluster("cluster_bbbbbbbb", ["0000000000000001"], ["prompt_injection"])],
        total_failures=1,
    )
    stub = _Scripted({"cluster_bbbbbbbb": _patch_for(["prompt_injection"])})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert any(p.section == "system_prompt" for p in recipe.prompt_patches)


# ---------------------------------------------------------------------------
# Parallel dispatch
# ---------------------------------------------------------------------------


async def test_patcher_dispatches_in_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[
            _cluster(
                f"cluster_{i:08x}",
                [f"{i:016x}"],
                ["malformed_tool_output"],
            )
            for i in range(5)
        ],
        total_failures=5,
    )
    per_cluster_response = _patch_for(["malformed_tool_output"])
    stub = _Scripted(
        {c.cluster_id: per_cluster_response for c in cs.clusters},
        delay_s=0.1,
    )
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    start = asyncio.get_running_loop().time()
    recipe = await Patcher().run(cs, target_agent_id="target")
    elapsed = asyncio.get_running_loop().time() - start
    # Sequential would be 5 * 0.1 = 0.5s; parallel ~0.1s. Allow up to 0.4s
    # to keep the test stable on CI.
    assert elapsed < 0.4, f"parallel dispatch too slow ({elapsed:.2f}s)"
    assert len(recipe.cluster_set.clusters) == 5


# ---------------------------------------------------------------------------
# Retry / fallback on parse failure
# ---------------------------------------------------------------------------


async def test_patcher_retries_on_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[_cluster("cluster_aaaaaaaa", ["0000000000000001"], ["malformed_tool_output"])],
        total_failures=1,
    )
    # Track per-cluster call count by returning bad JSON once then good.
    call_count: dict[str, int] = {"cluster_aaaaaaaa": 0}
    good = _patch_for(["malformed_tool_output"])

    async def stub(prompt: str) -> str:
        m = re.search(r"cluster_id:\s*(\S+)", prompt)
        assert m
        cid = m.group(1)
        call_count[cid] = call_count.get(cid, 0) + 1
        if call_count[cid] == 1:
            return "not-json"
        return good

    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert call_count["cluster_aaaaaaaa"] == 2
    assert len(recipe.prompt_patches) >= 1


async def test_patcher_falls_back_after_retry_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[_cluster("cluster_aaaaaaaa", ["0000000000000001"], ["malformed_tool_output"])],
        total_failures=1,
    )
    stub = _Scripted({"cluster_aaaaaaaa": "still not json"})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    # Partial recipe still emitted with a generic fallback patch.
    assert len(recipe.prompt_patches) >= 1
    assert any(
        "fallback" in p.after.lower() or "root cause" in p.after.lower()
        for p in recipe.prompt_patches
    )


async def test_patcher_falls_back_when_gemini_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cs = FailureClusterSet(
        clusters=[
            _cluster("cluster_aaaaaaaa", ["0000000000000001"], ["malformed_tool_output"]),
            _cluster("cluster_bbbbbbbb", ["0000000000000002"], ["prompt_injection"]),
        ],
        total_failures=2,
    )
    # Cluster A explodes; cluster B returns valid JSON. The recipe must
    # ship a partial result, not fail the whole run.
    stub = _Scripted(
        {
            "cluster_aaaaaaaa": RuntimeError("Gemini quota exhausted"),
            "cluster_bbbbbbbb": _patch_for(["prompt_injection"]),
        }
    )
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert len(recipe.prompt_patches) >= 1


# ---------------------------------------------------------------------------
# ADR-007 enforcement
# ---------------------------------------------------------------------------


async def test_patcher_rejects_non_flash_judge_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patcher_module,
        "get_settings",
        lambda: type(  # noqa: PLW0108
            "S",
            (),
            {"JUDGE_LLM": "claude-3-haiku", "MAX_CLUSTERS": 5},
        )(),
    )
    cs = _cluster_set_3_clusters()
    with pytest.raises(RuntimeError, match="ADR-007"):
        await Patcher().run(cs, target_agent_id="target")


async def test_patcher_accepts_flash_variants_via_startswith(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patcher_module,
        "get_settings",
        lambda: type(  # noqa: PLW0108
            "S",
            (),
            {"JUDGE_LLM": "gemini-3.5-flash-002", "MAX_CLUSTERS": 5},
        )(),
    )
    cs = _cluster_set_3_clusters()
    stub = _Scripted({c.cluster_id: _patch_for(c.fault_classes) for c in cs.clusters})
    monkeypatch.setattr(patcher_module, "_call_patcher_llm", stub)
    recipe = await Patcher().run(cs, target_agent_id="target")
    assert isinstance(recipe, HardeningRecipe)


# ---------------------------------------------------------------------------
# Existing factory should still build (orchestrator pipeline contract)
# ---------------------------------------------------------------------------


def test_build_patcher_agent_still_exports() -> None:
    from chaoslab_agent.patcher import PATCHER_NAME, build_patcher_agent

    agent = build_patcher_agent()
    assert agent is not None
    assert PATCHER_NAME == "Patcher"
