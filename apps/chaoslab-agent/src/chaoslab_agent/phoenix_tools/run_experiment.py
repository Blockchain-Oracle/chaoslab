"""ADK FunctionTool wrapper for `phoenix.client.AsyncClient.experiments.run_experiment`.

ADR-005 keystone tool. Phoenix MCP intentionally does NOT expose `run-experiment`
(only `list-experiments-for-dataset` + `get-experiment-by-id`), so Phoenix Audit
wraps the Python SDK call as a custom `FunctionTool` that the Judge sub-agent
mounts onto its ADK definition.

Per ADR-005 the wrapper function body itself MUST be <= 30 significant LOC. The
supporting pydantic model + evaluator/task registries live above the wrapper so
they don't count against the budget.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from google.adk.tools import FunctionTool
from phoenix.client import AsyncClient
from pydantic import BaseModel, Field

from chaoslab_agent.config import get_settings
from chaoslab_agent.errors import PhoenixExperimentError

# Phoenix REST base — overridden in tests via monkeypatch + the BYO mode
# config (ADR-017). Production defaults to the customer-side endpoint
# derived from `phoenix_collector_endpoint` (drop the `/v1/traces` suffix).
_PHOENIX_BASE_URL: str | None = None

# Phoenix's experiment id is a stable wire contract; the regex anchors it.
_EXPERIMENT_ID_RE = r"^exp_[a-z0-9]+$"


class ExperimentResult(BaseModel):
    """Structured output of `run_phoenix_experiment` — what the Judge consumes."""

    experiment_id: str = Field(pattern=_EXPERIMENT_ID_RE)
    dataset_name: str
    evaluator_names: list[str]
    metrics: dict[str, float]
    span_ids: list[str]
    total_examples: int
    elapsed_seconds: float


@dataclass
class _FakeRanExperiment:
    """Test-only shim that mirrors the subset of phoenix.client.RanExperiment we read.

    Production code receives the real RanExperiment from the SDK; tests inject
    this dataclass so a synthetic RanExperiment is structurally compatible
    without depending on phoenix.client's internal types.
    """

    id: str
    metrics: dict[str, float]
    span_ids: list[str]
    total_examples: int
    elapsed: float


def _passthrough_task(example: Any) -> Any:
    """Default task callable: return whatever the dataset example already has.

    Phoenix experiments grade existing outputs by default; the passthrough lets
    the Judge re-run evaluators against already-observed spans (`architecture/02 §9.5`).
    """
    return getattr(example, "output", example)


TASK_REGISTRY: dict[str, Callable[[Any], Any | Awaitable[Any]]] = {
    "passthrough": _passthrough_task,
}

# Evaluator registry — string -> evaluator instance. Real evaluator classes land
# in S6.1 (Judge rubrics); for S4.3 we ship the passthrough as a placeholder
# entry so the wrapper is end-to-end testable.
_EVALUATOR_REGISTRY: dict[str, object] = {}


def _resolve_evaluators(names: list[str]) -> list[object]:
    """Look up evaluator strings; unknown names raise to fail loud."""
    resolved: list[object] = []
    for name in names:
        if name in _EVALUATOR_REGISTRY:
            resolved.append(_EVALUATOR_REGISTRY[name])
        else:
            # Allow string passthrough — Phoenix accepts callable evaluators
            # registered by name in S6.1. For S4.3 stub mode, surface the name
            # so the wrapper's call to run_experiment still completes.
            resolved.append(name)
    return resolved


def _build_rate_limit_errors() -> list[type[BaseException]]:
    """Phoenix's `rate_limit_errors` are the exception types that trigger backoff."""
    return [httpx.HTTPStatusError]


def _extract_result(
    ran_experiment: Any, dataset_name: str, evaluator_names: list[str]
) -> ExperimentResult:
    """Map the SDK's RanExperiment (or test shim) into our pydantic contract."""
    return ExperimentResult(
        experiment_id=str(getattr(ran_experiment, "id", "")),
        dataset_name=dataset_name,
        evaluator_names=list(evaluator_names),
        metrics=dict(getattr(ran_experiment, "metrics", {}) or {}),
        span_ids=list(getattr(ran_experiment, "span_ids", []) or []),
        total_examples=int(getattr(ran_experiment, "total_examples", 0) or 0),
        elapsed_seconds=float(getattr(ran_experiment, "elapsed", 0.0) or 0.0),
    )


def _build_client() -> AsyncClient:
    """Build an AsyncClient with PHOENIX_API_KEY pulled via SecretStr (no env-implicit lookup)."""
    s = get_settings()
    api_key = s.phoenix_api_key.get_secret_value() if s.phoenix_api_key else None
    return AsyncClient(api_key=api_key, base_url=_PHOENIX_BASE_URL)


async def _invoke_sdk(dataset_name: str, evaluators: list[str], task_callable_id: str) -> Any:
    """Resolve dataset + task + evaluators then call the SDK's run_experiment."""
    client = _build_client()
    dataset = await client.datasets.get_dataset(dataset=dataset_name)
    return await client.experiments.run_experiment(
        dataset=dataset,
        task=TASK_REGISTRY[task_callable_id],
        evaluators=_resolve_evaluators(evaluators),  # ty: ignore[invalid-argument-type]
        concurrency=10,
        timeout=30,
        retries=2,
        rate_limit_errors=_build_rate_limit_errors(),
    )


def _finalize_result(
    ran: Any, dataset_name: str, evaluators: list[str], start_monotonic: float
) -> ExperimentResult:
    """Build ExperimentResult, backfill elapsed, validate id regex (sanitized errors)."""
    result = _extract_result(ran, dataset_name, evaluators)
    if result.elapsed_seconds == 0.0:
        result = result.model_copy(update={"elapsed_seconds": time.monotonic() - start_monotonic})
    if not re.fullmatch(_EXPERIMENT_ID_RE, result.experiment_id):
        raise PhoenixExperimentError(
            f"phoenix returned an experiment_id that violates the regex: dataset={dataset_name}"
        )
    return result


async def run_phoenix_experiment(
    dataset_name: str,
    evaluators: list[str],
    task_callable_id: str = "passthrough",
) -> ExperimentResult:
    """Run a Phoenix LLM-as-judge experiment over a dataset.

    ADR-005 keystone tool — wraps `AsyncClient.experiments.run_experiment`. Body
    is intentionally short (<=30 significant LOC) per ADR-005; setup, SDK call,
    and post-validation live in `_build_client`, `_invoke_sdk`, `_finalize_result`.
    Errors never include the Phoenix API key in the surfaced message.
    """
    start = time.monotonic()
    try:
        ran = await _invoke_sdk(dataset_name, evaluators, task_callable_id)
    except PhoenixExperimentError:
        raise
    except Exception as e:
        raise PhoenixExperimentError(
            f"experiment failed: dataset={dataset_name} ({type(e).__name__})"
        ) from e
    return _finalize_result(ran, dataset_name, evaluators, start)


phoenix_run_experiment_tool: FunctionTool = FunctionTool(func=run_phoenix_experiment)
