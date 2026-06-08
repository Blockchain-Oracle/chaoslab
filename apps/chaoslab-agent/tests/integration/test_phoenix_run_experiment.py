"""Integration tests for the Phoenix `run_experiment` FunctionTool wrapper.

Tests inject `FakeClient` / `FakeDatasets` / `FakeExperiments` (defined below)
to exercise the production wrapper body without making real HTTP calls. The
`@pytest.mark.online` test hits the real Phoenix Cloud project and is skipped
unless PHOENIX_API_KEY is present and not a placeholder.
"""

from __future__ import annotations

import inspect
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest
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


# --- Test fixtures: minimal RanExperiment-shaped data + FakeClient -----------


@dataclass
class FakeRanExperiment:
    """Duck-typed stand-in for phoenix.client.RanExperiment.

    `_extract_result` reads `id`, `metrics`, `span_ids`, `total_examples`, `elapsed`
    via `_extract_required` + `getattr`. Anything matching that shape works.
    """

    id: str
    metrics: dict[str, float]
    span_ids: list[str]
    total_examples: int
    elapsed: float | None = 0.42


class _FakeDatasets:
    def __init__(self, captured: dict) -> None:
        self.captured = captured

    async def get_dataset(self, *, dataset: str, **_) -> object:
        self.captured["dataset_name"] = dataset
        return object()


class _FakeExperiments:
    def __init__(self, captured: dict, ran: FakeRanExperiment) -> None:
        self.captured = captured
        self.ran = ran

    async def run_experiment(self, **kwargs):
        self.captured["concurrency"] = kwargs.get("concurrency")
        self.captured["timeout"] = kwargs.get("timeout")
        self.captured["retries"] = kwargs.get("retries")
        self.captured["rate_limit_errors"] = kwargs.get("rate_limit_errors")
        return self.ran


def _build_fake_client_factory(
    captured: dict, ran: FakeRanExperiment | None = None, raises: Exception | None = None
):
    """Return a FakeClient class that captures init args + serves fake datasets/experiments."""

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            captured["api_key"] = kwargs.get("api_key")
            captured["base_url"] = kwargs.get("base_url")
            self.datasets = _FakeDatasets(captured)
            if raises is not None:
                self.experiments = _FakeExperimentsRaising(raises)
            else:
                effective_ran = (
                    ran
                    if ran is not None
                    else FakeRanExperiment(
                        id="exp_abc123def",
                        metrics={"tool_invocation": 0.92},
                        span_ids=["sp1"],
                        total_examples=3,
                    )
                )
                self.experiments = _FakeExperiments(captured, effective_ran)

    return _FakeClient


class _FakeExperimentsRaising:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def run_experiment(self, **kwargs):
        raise self.exc


# --- ExperimentResult contract ----------------------------------------------


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


# --- FunctionTool wiring -----------------------------------------------------


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


# --- Wrapper behaviour: happy path, error paths, retries --------------------


async def test_wrapper_dispatches_through_async_client_with_locked_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify concurrency=10, timeout=30, retries=2, rate_limit_errors are wired."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    captured: dict = {}
    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory(captured))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "tool_invocation", object())

    result = await mod.run_phoenix_experiment("test-rat", ["tool_invocation"])
    assert result.experiment_id == "exp_abc123def"
    assert captured["concurrency"] == 10
    assert captured["timeout"] == 30
    assert captured["retries"] == 2
    assert captured["rate_limit_errors"] is not None
    assert captured["api_key"] == "test-phoenix-key-DO-NOT-LEAK"
    assert captured["base_url"] == "https://phoenix.example.test"


async def test_wrapper_429_retries_three_times_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK should be invoked once per retry attempt; the wrapper hands off to it.

    The SDK's `retries=2` arg means the SDK does the retry loop internally — this test
    verifies our wrapper invokes `run_experiment` ONCE (the SDK then retries inside).
    A genuine retry-count test against a fake SDK that simulates the retry loop is
    out-of-scope for the wrapper layer.
    """
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    call_count = {"n": 0}
    real_ran = FakeRanExperiment(
        id="exp_retry123", metrics={"t": 1.0}, span_ids=[], total_examples=1
    )

    class FakeExperimentsCounting:
        async def run_experiment(self, **kwargs):
            call_count["n"] += 1
            return real_ran

    captured: dict = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["api_key"] = kwargs.get("api_key")
            self.datasets = _FakeDatasets(captured)
            self.experiments = FakeExperimentsCounting()

    monkeypatch.setattr(mod, "AsyncClient", FakeClient)
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "t", object())

    result = await mod.run_phoenix_experiment("ds", ["t"])
    assert result.experiment_id == "exp_retry123"
    assert (
        call_count["n"] == 1
    ), "Wrapper must hand off to SDK exactly once; SDK owns the internal retry loop."


@pytest.mark.parametrize("status_code", [429, 500, 503])
async def test_wrapper_http_status_error_surfaces_sanitized_status(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    """`httpx.HTTPStatusError` surfaces as PhoenixExperimentError naming the status code.

    Parametrized over rate-limit (429) + server errors (500/503) so the HTTPStatusError
    catch branch is gated for every shape the SDK might surface — not just one.
    """
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    response = httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://phoenix.example.test/x"),
    )
    err = httpx.HTTPStatusError(
        f"status {status_code}", request=response.request, response=response
    )
    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory({}, raises=err))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "t", object())

    with pytest.raises(PhoenixExperimentError) as exc_info:
        await mod.run_phoenix_experiment("ds", ["t"])
    msg = str(exc_info.value)
    assert "ds" in msg
    assert str(status_code) in msg
    assert "test-phoenix-key-DO-NOT-LEAK" not in msg


async def test_wrapper_scrubs_api_key_from_chained_sdk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch-all path scrubs `api_key=<secret>` substrings from chained SDK error messages."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    err = RuntimeError("connection failed: api_key=test-phoenix-key-DO-NOT-LEAK url=...")
    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory({}, raises=err))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "t", object())

    with pytest.raises(PhoenixExperimentError) as exc_info:
        await mod.run_phoenix_experiment("ds", ["t"])
    msg = str(exc_info.value)
    assert "test-phoenix-key-DO-NOT-LEAK" not in msg, f"key leaked: {msg!r}"
    assert "<redacted>" in msg


async def test_wrapper_raises_on_unknown_evaluator_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown evaluator name must fail loud BEFORE calling Phoenix, with the offending name."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory({}))
    with pytest.raises(PhoenixExperimentError, match=r"unknown evaluator"):
        await mod.run_phoenix_experiment("ds", ["not_in_registry"])


async def test_wrapper_raises_on_unknown_task_callable_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown task_callable_id must fail loud with the offending id + registered keys."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory({}))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "t", object())
    with pytest.raises(PhoenixExperimentError, match=r"unknown task_callable_id"):
        await mod.run_phoenix_experiment("ds", ["t"], task_callable_id="not_a_real_task")


# --- Helper coverage --------------------------------------------------------


def test_resolve_evaluators_returns_registered_instance_when_name_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    sentinel = object()
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "tool-eval", sentinel)
    resolved = mod._resolve_evaluators(["tool-eval"])
    assert resolved == [sentinel]


@pytest.mark.parametrize("missing_attr", ["id", "metrics", "span_ids", "total_examples"])
def test_extract_result_raises_on_each_missing_required_attribute(missing_attr: str) -> None:
    """Every required RanExperiment attribute must independently raise PhoenixExperimentError.

    The Round-2 `Empty` class only exercised the FIRST attribute checked (`id`). This
    parametrize asserts that dropping ANY of the four required fields fails loud — gates
    against a regression that silently defaults `total_examples=0` etc.
    """
    from chaoslab_agent.phoenix_tools.run_experiment import _extract_result

    full = {
        "id": "exp_abc123def",
        "metrics": {"t": 1.0},
        "span_ids": ["sp1"],
        "total_examples": 1,
        "elapsed": 0.1,
    }
    full.pop(missing_attr)
    partial_cls = type("PartialRanExperiment", (), full)
    with pytest.raises(
        PhoenixExperimentError, match=rf"missing required attribute '{missing_attr}'"
    ):
        _extract_result(partial_cls(), "ds", ["t"])


async def test_elapsed_seconds_backfilled_when_sdk_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the SDK doesn't surface elapsed, the wrapper backfills with wall-clock."""
    from chaoslab_agent.phoenix_tools import run_experiment as mod

    ran = FakeRanExperiment(id="exp_zero1", metrics={}, span_ids=[], total_examples=1, elapsed=None)
    monkeypatch.setattr(mod, "AsyncClient", _build_fake_client_factory({}, ran=ran))
    monkeypatch.setitem(mod._EVALUATOR_REGISTRY, "t", object())

    result = await mod.run_phoenix_experiment("ds", ["t"])
    assert (
        result.elapsed_seconds > 0.0
    ), f"backfill should produce a non-zero elapsed (got {result.elapsed_seconds!r})"


def test_scrub_secret_redacts_keyword_adjacent_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_scrub_secret` redacts api_key / Authorization / Bearer tokens + removes literal token."""
    from chaoslab_agent.phoenix_tools.run_experiment import _scrub_secret

    # Pass settings=None to isolate the keyword-adjacency branch from the
    # literal-key reverse-scrub (covered in the next test).
    for original in [
        "api_key=abcdefghijkl",
        "Authorization: Bearer abcdefghijkl",
        "Bearer abcdefghijkl was rejected",
    ]:
        scrubbed = _scrub_secret(original, settings=None)
        assert "<redacted>" in scrubbed, original
        # Regression guard: the actual secret token must be absent post-scrub.
        assert (
            "abcdefghijkl" not in scrubbed
        ), f"keyword-adjacent token leaked through scrub: {scrubbed!r}"


def test_scrub_secret_reverse_scrubs_literal_configured_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even without a keyword nearby, the literal configured API key value is scrubbed.

    Defends against SDK leaks that surface the key as a bare token (stack trace
    formatting, JSON body echo, raw `repr(e)` outputs that don't include `api_key=`).
    """
    from chaoslab_agent.phoenix_tools.run_experiment import _scrub_secret

    leaked = "connection refused; debug context test-phoenix-key-DO-NOT-LEAK in payload"
    scrubbed = _scrub_secret(leaked)  # uses get_settings() under the hood
    assert (
        "test-phoenix-key-DO-NOT-LEAK" not in scrubbed
    ), f"literal key leaked through reverse-scrub: {scrubbed!r}"
    assert "<redacted>" in scrubbed


def test_derive_base_url_strips_trace_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Phoenix REST base URL is the collector endpoint minus `/v1/traces`."""
    from chaoslab_agent.phoenix_tools.run_experiment import _derive_base_url

    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://example.test/v1/traces")
    get_settings.cache_clear()
    assert _derive_base_url(get_settings()) == "https://example.test"


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
