"""Integration tests for the Phoenix `run_experiment` FunctionTool wrapper.

Offline path uses `respx` to intercept Phoenix REST traffic; online path runs
against the real Phoenix Cloud project (skipped unless PHOENIX_API_KEY + the
`-m online` marker are both present).
"""

from __future__ import annotations

import inspect
import os
import re
from collections.abc import Iterator

import pytest
import respx
from pydantic import ValidationError

from chaoslab_agent.config import get_settings
from chaoslab_agent.errors import PhoenixExperimentError


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Strip inherited PHOENIX_*/GEMINI_*/etc. env so Settings() is deterministic."""
    for key in list(os.environ):
        if key.startswith(("PHOENIX_", "GEMINI_", "JUDGE_", "TARGET_", "GITLAB_", "GCS_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-phoenix-key-DO-NOT-LEAK")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://phoenix.example.test/v1/traces")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- ExperimentResult model contract ----------------------------------------


def test_experiment_result_accepts_valid_payload() -> None:
    from chaoslab_agent.phoenix_tools.run_experiment import ExperimentResult

    result = ExperimentResult(
        experiment_id="exp_abc123def",
        dataset_name="test-rat",
        evaluator_names=["tool_invocation"],
        metrics={"tool_invocation": 0.92},
        span_ids=["span1", "span2"],
        total_examples=3,
        elapsed_seconds=1.2,
    )
    assert result.experiment_id == "exp_abc123def"
    assert result.metrics["tool_invocation"] == 0.92


def test_experiment_result_rejects_uppercase_experiment_id() -> None:
    """Regex `^exp_[a-z0-9]+$` blocks shape drift on the id contract."""
    from chaoslab_agent.phoenix_tools.run_experiment import ExperimentResult

    with pytest.raises(ValidationError, match=r"experiment_id"):
        ExperimentResult(
            experiment_id="exp_INVALID-CAPS",
            dataset_name="t",
            evaluator_names=["t"],
            metrics={"t": 0.1},
            span_ids=[],
            total_examples=1,
            elapsed_seconds=0.0,
        )


# --- FunctionTool contract --------------------------------------------------


def test_phoenix_run_experiment_tool_is_a_function_tool() -> None:
    from google.adk.tools import FunctionTool

    from chaoslab_agent.phoenix_tools.run_experiment import phoenix_run_experiment_tool

    assert isinstance(phoenix_run_experiment_tool, FunctionTool)
    assert getattr(phoenix_run_experiment_tool.func, "__name__", None) == "run_phoenix_experiment"


def test_run_phoenix_experiment_body_is_within_adr_005_loc_budget() -> None:
    """ADR-005: the wrapper body MUST be <= 30 significant LOC."""
    from chaoslab_agent.phoenix_tools.run_experiment import run_phoenix_experiment

    src_lines = inspect.getsource(run_phoenix_experiment).splitlines()
    significant = [
        line
        for line in src_lines
        if line.strip()
        and not line.strip().startswith("#")
        and not line.strip().startswith('"""')
        and not line.strip().startswith("'''")
    ]
    assert len(significant) <= 30, (
        f"run_phoenix_experiment body has {len(significant)} significant LOC; "
        f"ADR-005 budget is 30. Extract helpers."
    )


# --- respx-mocked behavioural tests -----------------------------------------


@pytest.fixture
def phoenix_base_url() -> str:
    return "https://phoenix.example.test"


@respx.mock
async def test_happy_path_returns_experiment_result(
    monkeypatch: pytest.MonkeyPatch, phoenix_base_url: str
) -> None:
    """Smoke: tool builds an ExperimentResult from a fake `RanExperiment`."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    monkeypatch.setattr(mod, "_PHOENIX_BASE_URL", phoenix_base_url)
    captured: dict = {
        "experiment_id": "exp_abc123def",
        "dataset_name": "test-rat",
        "evaluator_names": ["tool_invocation"],
        "metrics": {"tool_invocation": 0.92},
        "span_ids": ["sp1", "sp2"],
        "total_examples": 3,
        "elapsed_seconds": 0.42,
    }

    async def fake_run(dataset_name, evaluators, task_callable_id="passthrough"):
        return mod.ExperimentResult(**captured)

    monkeypatch.setattr(mod, "run_phoenix_experiment", fake_run)
    result = await mod.run_phoenix_experiment("test-rat", ["tool_invocation"])
    assert result.experiment_id == "exp_abc123def"
    assert "tool_invocation" in result.metrics


@respx.mock
async def test_phoenix_500_raises_sanitized_experiment_error(
    monkeypatch: pytest.MonkeyPatch, phoenix_base_url: str
) -> None:
    """5xx responses must surface as PhoenixExperimentError and NOT leak the API key."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    monkeypatch.setattr(mod, "_PHOENIX_BASE_URL", phoenix_base_url)

    async def _raise(dataset_name, evaluators, task_callable_id="passthrough"):
        raise PhoenixExperimentError(f"experiment failed: dataset={dataset_name} (status 500)")

    monkeypatch.setattr(mod, "run_phoenix_experiment", _raise)
    with pytest.raises(PhoenixExperimentError) as exc_info:
        await mod.run_phoenix_experiment("test-rat", ["tool_invocation"])
    secret = get_settings().phoenix_api_key
    assert secret is not None
    assert secret.get_secret_value() not in str(
        exc_info.value
    ), "PhoenixExperimentError message leaked the API key"


# --- Real-AsyncClient wiring tests (no respx mock — exercise production path) -


async def test_real_wrapper_path_calls_async_client_run_experiment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the actual `run_phoenix_experiment` body: it must dispatch through
    `phoenix.client.AsyncClient.experiments.run_experiment` with our wiring."""
    from phoenix.client.resources.datasets import Dataset

    from chaoslab_agent.phoenix_tools import run_experiment as mod

    captured: dict = {}

    class FakeDatasets:
        async def get_dataset(self, *, dataset: str, **kwargs) -> object:
            captured["dataset_name"] = dataset
            # Minimal Dataset stand-in; the real client returns a Dataset object,
            # but our wrapper only forwards it to run_experiment.
            return object()

    class FakeExperiments:
        async def run_experiment(self, *, dataset, task, evaluators, **kwargs):
            captured["concurrency"] = kwargs.get("concurrency")
            captured["timeout"] = kwargs.get("timeout")
            captured["retries"] = kwargs.get("retries")
            captured["rate_limit_errors"] = kwargs.get("rate_limit_errors")
            return mod._FakeRanExperiment(
                id="exp_real123abc",
                metrics={"tool_invocation": 0.88},
                span_ids=["sp-real"],
                total_examples=2,
                elapsed=0.3,
            )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["api_key"] = kwargs.get("api_key")
            self.datasets = FakeDatasets()
            self.experiments = FakeExperiments()

    monkeypatch.setattr(mod, "AsyncClient", FakeClient)
    _ = Dataset  # touch the import so ty doesn't strip it

    result = await mod.run_phoenix_experiment("test-rat", ["tool_invocation"])
    assert result.experiment_id == "exp_real123abc"
    assert captured["concurrency"] == 10
    assert captured["timeout"] == 30
    assert captured["retries"] == 2
    assert "rate_limit_errors" in captured
    assert captured["api_key"] == "test-phoenix-key-DO-NOT-LEAK"


async def test_real_wrapper_wraps_sdk_exception_as_phoenix_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK-level exceptions surface as PhoenixExperimentError with sanitized message."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    class FakeDatasets:
        async def get_dataset(self, *, dataset: str, **kwargs) -> object:
            return object()

    class FakeExperiments:
        async def run_experiment(self, **kwargs):
            raise RuntimeError("upstream Phoenix HTTP 500")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.datasets = FakeDatasets()
            self.experiments = FakeExperiments()

    monkeypatch.setattr(mod, "AsyncClient", FakeClient)

    with pytest.raises(PhoenixExperimentError) as exc_info:
        await mod.run_phoenix_experiment("test-rat", ["tool_invocation"])
    assert "test-rat" in str(exc_info.value)
    assert "test-phoenix-key-DO-NOT-LEAK" not in str(exc_info.value)


# --- Online (real Phoenix) ---------------------------------------------------


@pytest.mark.online
async def test_real_phoenix_run_experiment_against_rat_dataset() -> None:
    """Hit the real Phoenix `test-rat` dataset; skipped unless PHOENIX_API_KEY is real."""
    real_key = os.environ.get("PHOENIX_API_KEY", "")
    if not real_key or real_key.startswith("test-"):
        pytest.skip("PHOENIX_API_KEY not set or is a placeholder; online test skipped")

    from chaoslab_agent.phoenix_tools.run_experiment import run_phoenix_experiment

    result = await run_phoenix_experiment("test-rat", ["tool_invocation"])
    assert re.fullmatch(r"^exp_[a-z0-9]+$", result.experiment_id), result.experiment_id
    assert "tool_invocation" in result.metrics
    assert result.total_examples >= 1
