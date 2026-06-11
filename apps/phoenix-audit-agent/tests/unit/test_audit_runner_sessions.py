"""drive_audit wraps the pipeline in OpenInference `using_attributes`.

Story 9.7 (phoenix-sessions). The Phoenix Sessions tab groups spans by
`session.id` and filters by `user.id` — Phoenix Audit MUST emit both for every
span the auditor produces, with `session.id == run_id` and `user.id == owner_uid`
(empty string when the run is ownerless / a "sample" run).

Trace-as-assertion: we don't mock `using_attributes`. We monkeypatch one of the
collaborators (`apply_rubric`) to read OpenInference's actual contextvar at
call time via `get_attributes_from_context()` — the same contract Phoenix uses.
If a future refactor changes HOW we set the attributes, this test stays valid
as long as the attributes ARRIVE.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from openinference.instrumentation import get_attributes_from_context

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.injector.agent import AttackResult
from phoenix_audit_agent.judge.rubrics import EvalScore
from phoenix_audit_agent.patcher.recipe import HardeningRecipe

# Reuse the heavy fakes wired into the suite — same fixture, same seam.
from .test_audit_runner import (  # type: ignore[import-not-found]
    SPAN_OK_PASS,
    _attack_result,
    _Emitted,
    _FakeInjector,
    wired,
)

__all__ = ["wired"]  # silence "unused import" — the fixture IS the contract


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Mirror test_audit_runner's settings + in-memory run-store seam.

    Without this, get_settings() reads the developer's .env (the canonical
    suite fixture is module-local to test_audit_runner so we can't import-and-share)."""
    from phoenix_audit_agent.storage import runs as run_storage

    from .storage.fakes import InMemoryRunStore

    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()
    run_storage.set_run_store(InMemoryRunStore())
    yield
    run_storage.set_run_store(None)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_drive_audit_emits_session_and_user_id_on_attributes_context(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inside drive_audit, the OpenInference contextvar must carry
    session.id == run_id AND user.id == owner_uid."""
    import phoenix_audit_agent.audit_runner as ar

    seen_inside: list[dict[str, Any]] = []

    async def rubric_recording(inp: Any) -> EvalScore:
        # apply_rubric runs deep inside drive_audit (judge phase). If the
        # using_attributes scope is correctly wrapping the work, this read
        # will see session.id + user.id.
        seen_inside.append(dict(get_attributes_from_context()))
        return EvalScore(passed=True, score=1.0, reason="ok")

    monkeypatch.setattr(ar, "apply_rubric", rubric_recording)

    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await ar.drive_audit(
        run_id="run_sessions12",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
        owner_uid="uid_alice",
    )

    assert seen_inside, "apply_rubric was never invoked — pipeline didn't reach the judge"
    # Every rubric call observes the same scope (no per-attack churn).
    for attrs in seen_inside:
        assert attrs.get("session.id") == "run_sessions12", attrs
        assert attrs.get("user.id") == "uid_alice", attrs


@pytest.mark.asyncio
async def test_drive_audit_owner_uid_none_yields_empty_user_id(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample runs (owner_uid=None) still group by session.id. user.id is empty
    string — OpenInference's no-op default; we never invent a tenant."""
    import phoenix_audit_agent.audit_runner as ar

    seen_inside: list[dict[str, Any]] = []

    async def rubric_recording(inp: Any) -> EvalScore:
        seen_inside.append(dict(get_attributes_from_context()))
        return EvalScore(passed=True, score=1.0, reason="ok")

    monkeypatch.setattr(ar, "apply_rubric", rubric_recording)

    _FakeInjector.results = [_attack_result(0, SPAN_OK_PASS, "ok")]
    phases: list[str] = []

    await ar.drive_audit(
        run_id="run_sample0001",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
        owner_uid=None,
    )

    assert seen_inside
    for attrs in seen_inside:
        assert attrs.get("session.id") == "run_sample0001"
        # user.id absent OR empty — both are valid no-ops for OpenInference.
        assert attrs.get("user.id", "") == ""


@pytest.mark.asyncio
async def test_drive_audit_keeps_scope_through_recipe_phase(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scope must wrap the WHOLE pipeline — including the patcher phase.
    A bug where using_attributes wraps only the injector would leak the
    recipe/report spans out of the session group, breaking the Sessions tab
    for the very phase that produced the regulator-facing evidence."""
    import phoenix_audit_agent.audit_runner as ar

    seen_in_patcher: list[dict[str, Any]] = []

    class _RecordingPatcher:
        async def run(self, cluster_set: Any, target_agent_id: str) -> HardeningRecipe:
            seen_in_patcher.append(dict(get_attributes_from_context()))
            from .test_audit_runner import _recipe  # type: ignore[import-not-found]

            return _recipe()

    monkeypatch.setattr(ar, "Patcher", _RecordingPatcher)
    # Force a failure so the clusterer + patcher fire.
    from .test_audit_runner import SPAN_OK_FAIL  # type: ignore[import-not-found]

    async def fake_rubric(inp: Any) -> EvalScore:
        if inp.span_id == SPAN_OK_FAIL:
            return EvalScore(passed=False, score=0.0, reason="injected directive obeyed")
        return EvalScore(passed=True, score=1.0, reason="ok")

    monkeypatch.setattr(ar, "apply_rubric", fake_rubric)
    _FakeInjector.results = [_attack_result(0, SPAN_OK_FAIL, "ok")]
    phases: list[str] = []

    await ar.drive_audit(
        run_id="run_patcherscope",
        target_url="https://target.example",
        runs_per_fault=1,
        emit=wired.emit,
        set_phase=phases.append,
        owner_uid="uid_bob",
    )

    assert seen_in_patcher
    assert seen_in_patcher[0].get("session.id") == "run_patcherscope"
    assert seen_in_patcher[0].get("user.id") == "uid_bob"


@pytest.mark.asyncio
async def test_drive_audit_keeps_scope_even_when_pipeline_raises(
    wired: _Emitted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pipeline crash must not leak the scope. The failure-timeline write
    happens INSIDE the except arm — which itself relies on no contextvar
    poisoning. The cleanest test: assert the contextvar is empty AFTER
    drive_audit raises."""
    import phoenix_audit_agent.audit_runner as ar

    async def boom(*_args: Any, **_kwargs: Any) -> AttackResult:
        msg = "synthetic-injector-crash"
        raise RuntimeError(msg)

    class _ExplodingInjector:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def run(self) -> None:
            msg = "synthetic-injector-crash"
            raise RuntimeError(msg)

    monkeypatch.setattr(ar, "Injector", _ExplodingInjector)

    with pytest.raises(RuntimeError, match="synthetic-injector-crash"):
        await ar.drive_audit(
            run_id="run_explodexxx0",
            target_url="https://target.example",
            runs_per_fault=1,
            emit=wired.emit,
            set_phase=lambda _phase: None,
            owner_uid="uid_eve",
        )

    # Contextvar reset after `with` exits — exception or not.
    after = dict(get_attributes_from_context())
    assert "session.id" not in after
    assert "user.id" not in after
