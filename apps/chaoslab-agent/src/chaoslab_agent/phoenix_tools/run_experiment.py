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
from typing import Any

import httpx
from phoenix.client import AsyncClient
from pydantic import BaseModel, Field

from chaoslab_agent.adk_types import FunctionTool
from chaoslab_agent.config import Settings, get_settings
from chaoslab_agent.errors import PhoenixExperimentError

# Phoenix's experiment id is a stable wire contract; the regex anchors it.
_EXPERIMENT_ID_RE = r"^exp_[a-z0-9]+$"

# Minimum length for the literal-key reverse scrub. Any configured key shorter
# than this is treated as a test sentinel + skipped (avoids false-positive scrubs).
_MIN_SECRET_LEN = 8

# Regex matching anything that looks like a Phoenix API key — used to scrub
# SDK error messages before surfacing. Phoenix keys are opaque strings; any
# token longer than 20 chars adjacent to "key" / "Authorization" / "Bearer"
# is treated as suspect.
_SECRET_SCRUB_RE = re.compile(
    r"(api[_-]?key|authorization|bearer)[\s:=]+([^\s,;]{8,})",
    re.IGNORECASE,
)


class ExperimentResult(BaseModel):
    """Structured output of `run_phoenix_experiment` — what the Judge consumes."""

    experiment_id: str = Field(pattern=_EXPERIMENT_ID_RE)
    dataset_name: str
    evaluator_names: list[str]
    metrics: dict[str, float]
    span_ids: list[str]
    total_examples: int
    elapsed_seconds: float


def _passthrough_task(example: Any) -> Any:
    """Default task callable: return whatever the dataset example already has.

    Phoenix experiments grade existing outputs by default; the passthrough lets
    the Judge re-run evaluators against already-observed spans (`architecture/02 §9.5`).
    """
    return getattr(example, "output", example)


_DEFAULT_TASK_KEY = "passthrough"

TASK_REGISTRY: dict[str, Callable[[Any], Any | Awaitable[Any]]] = {
    _DEFAULT_TASK_KEY: _passthrough_task,
}

# Registry is empty until Judge rubric classes (Epic 6) are wired. The Judge
# sub-agent will register entries like `"tool_invocation"`, `"hallucination"`,
# etc.; until then `_resolve_evaluators` will raise on any non-empty list.
_EVALUATOR_REGISTRY: dict[str, object] = {}


def _scrub_secret(message: str, settings: Settings | None = None) -> str:
    """Best-effort scrub of API key material from a message.

    Two passes: (1) regex match on `(api_?key|authorization|bearer)<sep><token>`
    keyword-adjacent patterns (see `_SECRET_SCRUB_RE`); (2) literal-string scrub
    of the actually-configured `phoenix_api_key` value, which defends against
    SDK leaks that don't include a keyword (raw token in a stack trace, JSON
    body echo, etc.). Pass `settings=None` to skip pass 2 (used in unit tests).
    """
    scrubbed = _SECRET_SCRUB_RE.sub(r"\1=<redacted>", message)
    s = settings if settings is not None else get_settings()
    if s.phoenix_api_key is not None:
        key_value = s.phoenix_api_key.get_secret_value()
        # Only attempt literal scrub if the key is long enough to be a real
        # secret; avoids accidentally scrubbing short test sentinels.
        if len(key_value) >= _MIN_SECRET_LEN and key_value in scrubbed:
            scrubbed = scrubbed.replace(key_value, "<redacted>")
    return scrubbed


def _resolve_evaluators(names: list[str]) -> list[object]:
    """Look up evaluator strings; unknown names raise to fail loud (no silent passthrough)."""
    resolved: list[object] = []
    unknown: list[str] = []
    for name in names:
        if name in _EVALUATOR_REGISTRY:
            resolved.append(_EVALUATOR_REGISTRY[name])
        else:
            unknown.append(name)
    if unknown:
        registered = sorted(_EVALUATOR_REGISTRY)
        raise PhoenixExperimentError(
            f"unknown evaluator(s): {unknown!r} (registered={registered!r})"
        )
    return resolved


def _derive_base_url(settings: Settings) -> str | None:
    """Derive the Phoenix REST base URL from `phoenix_collector_endpoint` (drop /v1/traces)."""
    endpoint = settings.phoenix_collector_endpoint
    if endpoint.endswith("/v1/traces"):
        return endpoint[: -len("/v1/traces")]
    return endpoint or None


def _rate_limit_errors() -> tuple[type[BaseException], ...]:
    """Exception types Phoenix should treat as retryable rate-limit signals.

    `httpx.HTTPStatusError` covers HTTP-level rate limit responses (Phoenix uses
    429 per its OpenAPI spec); we also accept `google.api_core.exceptions.ResourceExhausted`
    if the dependency is present (Gemini-side rate limits surface there). Both are
    narrow signals — `Exception` would over-retry on legitimate failures.
    """
    errors: list[type[BaseException]] = [httpx.HTTPStatusError]
    try:
        from google.api_core.exceptions import ResourceExhausted

        errors.append(ResourceExhausted)
    except ImportError:
        # google.api_core is optional; skip if not installed.
        pass
    return tuple(errors)


def _extract_required(ran_experiment: Any, attr: str) -> Any:
    """Read a required attribute from a RanExperiment-shaped object; raise if missing.

    Phoenix's SDK should always provide these fields; defaulting them silently turned
    a malformed-response bug into a hidden empty result. Fail loud instead.
    """
    if not hasattr(ran_experiment, attr):
        raise PhoenixExperimentError(
            f"malformed RanExperiment: missing required attribute {attr!r}"
        )
    return getattr(ran_experiment, attr)


def _extract_result(
    ran_experiment: Any, dataset_name: str, evaluator_names: list[str]
) -> ExperimentResult:
    """Map the SDK's RanExperiment into our pydantic contract.

    `elapsed_seconds` uses `None` from the SDK as the sentinel for "not measured";
    the caller backfills with wall-clock when None. Other required fields raise
    if absent (no silent empty-default).
    """
    elapsed_attr = getattr(ran_experiment, "elapsed", None)
    return ExperimentResult(
        experiment_id=str(_extract_required(ran_experiment, "id")),
        dataset_name=dataset_name,
        evaluator_names=list(evaluator_names),
        metrics=dict(_extract_required(ran_experiment, "metrics") or {}),
        span_ids=list(_extract_required(ran_experiment, "span_ids") or []),
        total_examples=int(_extract_required(ran_experiment, "total_examples")),
        elapsed_seconds=float(elapsed_attr) if elapsed_attr is not None else 0.0,
    )


def _build_client(settings: Settings) -> AsyncClient:
    """Build an AsyncClient with PHOENIX_API_KEY pulled via SecretStr (no env-implicit lookup)."""
    api_key = settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    return AsyncClient(api_key=api_key, base_url=_derive_base_url(settings))


async def _invoke_sdk(dataset_name: str, evaluators: list[str], task_callable_id: str) -> Any:
    """Resolve dataset + task + evaluators then call the SDK's run_experiment.

    Evaluator resolution happens BEFORE the SDK call so unknown names fail loud
    with a useful PhoenixExperimentError instead of being wrapped as a generic
    `(KeyError)` after the catch-all in `run_phoenix_experiment`.
    """
    if task_callable_id not in TASK_REGISTRY:
        raise PhoenixExperimentError(
            f"unknown task_callable_id: {task_callable_id!r} (registered={sorted(TASK_REGISTRY)!r})"
        )
    resolved_evaluators = _resolve_evaluators(evaluators)
    client = _build_client(get_settings())
    dataset = await client.datasets.get_dataset(dataset=dataset_name)
    return await client.experiments.run_experiment(
        dataset=dataset,
        task=TASK_REGISTRY[task_callable_id],
        # Suppression rationale: list[object] subsumes Phoenix's Evaluator |
        # Callable union; the registry lookup is the runtime contract.
        evaluators=resolved_evaluators,  # ty: ignore[invalid-argument-type]
        concurrency=10,
        timeout=30,
        retries=2,
        rate_limit_errors=_rate_limit_errors(),
    )


def _finalize_result(
    ran: Any, dataset_name: str, evaluators: list[str], start_monotonic: float
) -> ExperimentResult:
    """Build ExperimentResult; backfill elapsed only when SDK reported zero/missing.

    The `experiment_id` regex contract is enforced by the pydantic `Field` on
    construction — no redundant re-check here (dead-code per pr-test review).
    """
    result = _extract_result(ran, dataset_name, evaluators)
    if result.elapsed_seconds == 0.0:
        # SDK didn't surface elapsed; backfill with wall-clock. Floor at a small
        # non-zero so downstream code can distinguish "ran but fast" from "didn't run."
        backfill = max(time.monotonic() - start_monotonic, 1e-6)
        result = result.model_copy(update={"elapsed_seconds": backfill})
    return result


async def run_phoenix_experiment(
    dataset_name: str,
    evaluators: list[str],
    task_callable_id: str = _DEFAULT_TASK_KEY,
) -> ExperimentResult:
    """Run a Phoenix LLM-as-judge experiment over a dataset.

    ADR-005 keystone tool — wraps `AsyncClient.experiments.run_experiment`. Body
    is intentionally short (<=30 significant LOC) per ADR-005; setup, SDK call,
    and post-validation live in `_build_client`, `_invoke_sdk`, `_finalize_result`.

    Error sanitization: the wrapper's own raised message excludes the API key by
    construction; the chained exception (preserved via `raise ... from e`) may
    include SDK-side detail, scrubbed of obvious key patterns.
    """
    start = time.monotonic()
    try:
        ran = await _invoke_sdk(dataset_name, evaluators, task_callable_id)
    except PhoenixExperimentError:
        raise
    except httpx.HTTPStatusError as e:
        raise PhoenixExperimentError(
            f"experiment failed: dataset={dataset_name} status={e.response.status_code}"
        ) from e
    except Exception as e:
        # Scrub passes the cached settings explicitly so a future test fixture
        # that monkeypatches `get_settings` doesn't accidentally bypass the
        # literal-key reverse-scrub.
        raise PhoenixExperimentError(
            f"experiment failed: dataset={dataset_name} "
            f"cause={type(e).__name__}: {_scrub_secret(str(e), get_settings())}"
        ) from e
    return _finalize_result(ran, dataset_name, evaluators, start)


phoenix_run_experiment_tool: FunctionTool = FunctionTool(func=run_phoenix_experiment)
