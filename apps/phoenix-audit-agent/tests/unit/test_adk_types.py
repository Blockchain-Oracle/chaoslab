"""Tests for `phoenix_audit_agent.adk_types` — quarantine + pydantic type-safety wrappers."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

# --- Quarantine architectural invariant -------------------------------------


def test_only_quarantine_imports_google_adk() -> None:
    """`adk_types.py` is the ONLY file under apps/phoenix-audit-agent/src/ that imports google.adk.

    This is the load-bearing ADR-001 + best-practices/03 §3 invariant: every
    `google.adk.*` usage flows through the quarantine so a future SDK upgrade
    touches one file.

    Implemented via Python's native rglob+regex (not subprocess(grep)) to avoid
    the ruff S603/S607 suppressions AND the runtime dependency on `grep` being
    on PATH inside the CI sandbox.
    """
    repo_root = Path(__file__).resolve().parents[3].parent
    src_dir = repo_root / "apps" / "phoenix-audit-agent" / "src" / "phoenix_audit_agent"
    assert src_dir.is_dir(), f"src dir not found: {src_dir}"

    pattern = re.compile(r"^(from|import) google\.adk", re.MULTILINE)
    matched: list[Path] = []
    # Glob both `.py` and `.pyi` — a stub file with `from google.adk import X`
    # would smuggle past a .py-only gate even though the static type-checker
    # would treat it as a real import.
    for ext in ("*.py", "*.pyi"):
        for py_file in src_dir.rglob(ext):
            try:
                if pattern.search(py_file.read_text(encoding="utf-8")):
                    matched.append(py_file)
            except UnicodeDecodeError:
                continue

    listed = sorted(str(p) for p in matched)
    expected = [str(src_dir / "adk_types.py")]
    assert listed == expected, (
        f"ADK imports must live ONLY in adk_types.py.\n"
        f"  expected: {expected}\n"
        f"  actual:   {listed}\n"
        f"  Move any extra `google.adk.*` imports into adk_types.py and re-import "
        f"the symbol from `phoenix_audit_agent.adk_types`."
    )


def test_quarantine_reexports_load() -> None:
    """The headline ADK types re-exported by the quarantine all import cleanly."""
    from phoenix_audit_agent.adk_types import (
        AdkEvent,
        BaseTool,
        FunctionTool,
        InMemoryRunner,
        LlmAgent,
        LoopAgent,  # ty: ignore[deprecated]
        ParallelAgent,  # ty: ignore[deprecated]
        Runner,
        SequentialAgent,  # ty: ignore[deprecated]
    )

    for sym in (
        AdkEvent,
        BaseTool,
        FunctionTool,
        InMemoryRunner,
        LlmAgent,
        LoopAgent,  # ty: ignore[deprecated]
        ParallelAgent,  # ty: ignore[deprecated]
        Runner,
        SequentialAgent,  # ty: ignore[deprecated]
    ):
        assert sym is not None


# --- AgentSpec --------------------------------------------------------------


def test_agent_spec_accepts_valid_payload() -> None:
    from phoenix_audit_agent.adk_types import AgentSpec

    spec = AgentSpec(
        name="Injector",
        description="A" * 25,
        model="gemini-3.5-flash",
        output_key="injector_result",
        tools=["run_phoenix_experiment"],
    )
    assert spec.name == "Injector"
    assert spec.model == "gemini-3.5-flash"


@pytest.mark.parametrize(
    "bad_model",
    ["gemini-2.5-pro", "gemini-3.1-pro", "gemini-pro", "gemini-2.0-flash"],
)
def test_agent_spec_rejects_non_locked_model(bad_model: str) -> None:
    """ADR-007 enforced at type level — only `gemini-3.5-flash` validates."""
    from phoenix_audit_agent.adk_types import AgentSpec

    with pytest.raises(ValidationError, match=r"model"):
        AgentSpec(
            name="X",
            description="A" * 25,
            model=bad_model,  # ty: ignore[invalid-argument-type]
        )


def test_agent_spec_rejects_short_description() -> None:
    """architecture/03 §1.1: descriptions are load-bearing for supervisor routing."""
    from phoenix_audit_agent.adk_types import AgentSpec

    with pytest.raises(ValidationError, match=r"description"):
        AgentSpec(name="X", description="short")


# --- RunState ---------------------------------------------------------------


def test_run_state_accepts_valid_payload() -> None:
    from phoenix_audit_agent.adk_types import RunState

    state = RunState(
        run_id="run_abc123def456",
        phase="queued",
        target_url="http://localhost:8001",
        created_at="2026-06-08T12:00:00Z",
    )
    assert state.phase == "queued"


@pytest.mark.parametrize(
    "bad_run_id",
    [
        "INVALID-ID-FORMAT",
        "run_ABC123DEF456",  # uppercase rejected
        "run_short",
        "run_12345678901234",  # too long
        "",
    ],
)
def test_run_state_rejects_malformed_run_id(bad_run_id: str) -> None:
    """Regex `^run_[a-z0-9]{12}$` — the S4.1 frontend contract."""
    from phoenix_audit_agent.adk_types import RunState

    with pytest.raises(ValidationError, match=r"run_id"):
        RunState(
            run_id=bad_run_id,
            phase="queued",
            target_url="http://x",
            created_at="2026-06-08T12:00:00Z",
        )


def test_run_state_rejects_invalid_phase() -> None:
    """Phase must be one of the documented Literal values."""
    from phoenix_audit_agent.adk_types import RunState

    with pytest.raises(ValidationError, match=r"phase"):
        RunState(
            run_id="run_abc123def456",
            phase="bogus_phase",  # ty: ignore[invalid-argument-type]
            target_url="http://x",
            created_at="2026-06-08T12:00:00Z",
        )


def test_run_state_rejects_non_iso_created_at() -> None:
    """`created_at` validator catches non-RFC-3339-UTC strings."""
    from phoenix_audit_agent.adk_types import RunState

    with pytest.raises(ValidationError, match=r"created_at"):
        RunState(
            run_id="run_abc123def456",
            phase="queued",
            target_url="http://x",
            created_at="not-an-iso-date",
        )


# --- RunEvent ---------------------------------------------------------------


def test_run_event_accepts_valid_payload() -> None:
    from phoenix_audit_agent.adk_types import RunEvent

    ev = RunEvent(
        event_type="hello",
        data={"run_id": "run_abc123def456"},
        emitted_at="2026-06-08T12:00:00Z",
    )
    assert ev.event_type == "hello"
    assert ev.data == {"run_id": "run_abc123def456"}


def test_run_event_rejects_unknown_event_type() -> None:
    """Event type must be one of the documented Literal values."""
    from phoenix_audit_agent.adk_types import RunEvent

    with pytest.raises(ValidationError, match=r"event_type"):
        RunEvent(
            event_type="totally_made_up",  # ty: ignore[invalid-argument-type]
            data={},
            emitted_at="2026-06-08T12:00:00Z",
        )
