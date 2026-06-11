"""`run_phoenix_experiment` forwards the optional `experiment_name` kwarg.

Story 9.7 (phoenix-sessions). Phoenix's **Experiments** tab is the regulator
deep-link for "what rubric ran with what scores on which run." Without a name,
every audit collapses into one anonymous experiment in the UI. The wire
contract: `run_phoenix_experiment(..., experiment_name="phoenix-audit-{run_id}")`
forwards that exact kwarg into `client.experiments.run_experiment(...)`. Omitted
or `None` => the kwarg is NOT passed (Phoenix auto-generates a name, current
SDK behavior preserved for callers that haven't migrated).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from phoenix_audit_agent.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Settings env that matches the integration suite — Phoenix key + endpoint."""
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


@dataclass
class _FakeRan:
    """Duck-typed RanExperiment matching what `_extract_result` reads."""

    id: str = "exp_namedabc123"
    metrics: dict[str, float] | None = None
    span_ids: list[str] | None = None
    total_examples: int = 1
    elapsed: float | None = 0.5

    def __post_init__(self) -> None:
        if self.metrics is None:
            self.metrics = {"tool_invocation": 1.0}
        if self.span_ids is None:
            self.span_ids = ["sp1"]


def _client_factory(captured: dict[str, object]):
    """Minimal AsyncClient stand-in. Captures every kwarg passed to run_experiment."""

    class _FakeDatasets:
        async def get_dataset(self, *, dataset: str, **_):
            captured["dataset_name"] = dataset
            return object()

    class _FakeExperiments:
        async def run_experiment(self, **kwargs):
            captured["all_kwargs"] = dict(kwargs)
            captured["experiment_name_kwarg_present"] = "experiment_name" in kwargs
            captured["experiment_name_value"] = kwargs.get("experiment_name")
            return _FakeRan()

    class _FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.datasets = _FakeDatasets()
            self.experiments = _FakeExperiments()

    return _FakeClient


async def test_experiment_name_forwarded_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """`experiment_name="phoenix-audit-run_xxx"` reaches the SDK verbatim."""
    from phoenix_audit_agent.phoenix_tools import run_experiment as mod

    captured: dict[str, object] = {}
    monkeypatch.setattr(mod, "AsyncClient", _client_factory(captured))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "tool_invocation", object())

    await mod.run_phoenix_experiment(
        "test-dataset",
        ["tool_invocation"],
        experiment_name="phoenix-audit-run_abcabcabcabc",
    )

    assert captured["experiment_name_kwarg_present"] is True
    assert captured["experiment_name_value"] == "phoenix-audit-run_abcabcabcabc"


async def test_experiment_name_omitted_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """`experiment_name=None` (or omitted) MUST NOT pass the kwarg — Phoenix
    auto-generates a name, preserving the pre-9.7 wire contract."""
    from phoenix_audit_agent.phoenix_tools import run_experiment as mod

    captured: dict[str, object] = {}
    monkeypatch.setattr(mod, "AsyncClient", _client_factory(captured))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "tool_invocation", object())

    await mod.run_phoenix_experiment("test-dataset", ["tool_invocation"])
    assert captured["experiment_name_kwarg_present"] is False, captured["all_kwargs"]


async def test_experiment_name_omitted_when_explicit_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit `experiment_name=None` is treated identically to omission."""
    from phoenix_audit_agent.phoenix_tools import run_experiment as mod

    captured: dict[str, object] = {}
    monkeypatch.setattr(mod, "AsyncClient", _client_factory(captured))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "tool_invocation", object())

    await mod.run_phoenix_experiment(
        "test-dataset",
        ["tool_invocation"],
        experiment_name=None,
    )
    assert captured["experiment_name_kwarg_present"] is False, captured["all_kwargs"]
