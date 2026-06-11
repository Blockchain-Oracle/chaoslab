"""finalize_run → maybe_send_scheduled_summary wiring (story-9.5).

The hook fires AFTER the completion persist + `complete` frame (mail must
never delay the UI) and is contained (a mail outage never fails a finalize).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from phoenix_audit_agent import audit_runner as ar
from phoenix_audit_agent.audit_runner_emit import finalize_run

_TALLY = SimpleNamespace(passed=6, failed=2, errored=0, transport_failed=0)


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from phoenix_audit_agent.notifier import report_mail

    order: list[str] = []
    hook_calls: list[str] = []

    async def fake_persist_completion(run_id: str, completion: Any) -> bool:
        order.append("persist")
        return True

    async def fake_persist_events(run_id: str, frames: Any, *, created_at: str) -> bool:
        return False

    async def fake_emit(event: str, data: dict[str, Any]) -> None:
        order.append(f"emit:{event}")

    async def fake_hook(run_id: str) -> None:
        order.append("hook")
        hook_calls.append(run_id)

    monkeypatch.setattr(ar, "persist_run_completion", fake_persist_completion)
    monkeypatch.setattr(ar, "persist_run_events", fake_persist_events)
    monkeypatch.setattr(report_mail, "maybe_send_scheduled_summary", fake_hook)
    return {"order": order, "hook_calls": hook_calls, "emit": fake_emit}


async def _finalize(harness: dict[str, Any]) -> None:
    await finalize_run(
        run_id="run_abc123def456",
        target_url="https://target.example",
        created_at="2026-06-11T10:00:00Z",
        tally=_TALLY,
        recipe_id=None,
        markdown_url=None,
        report_urls=None,
        frames=[],
        emit=harness["emit"],
    )


async def test_finalize_fires_summary_hook_after_complete_frame(
    harness: dict[str, Any],
) -> None:
    await _finalize(harness)
    assert harness["hook_calls"] == ["run_abc123def456"]
    order = harness["order"]
    assert order.index("hook") > order.index("emit:complete")


async def test_finalize_contains_hook_failure(
    harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from phoenix_audit_agent.notifier import report_mail

    async def exploding_hook(run_id: str) -> None:
        raise RuntimeError("mail outage")

    monkeypatch.setattr(report_mail, "maybe_send_scheduled_summary", exploding_hook)
    await _finalize(harness)  # must not raise
    assert "emit:complete" in harness["order"]


async def test_finalize_completion_carries_launch_identity(
    harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The heal-path merge (failed create at launch) must not strip schedule
    linkage / ownership — the completion carries them (PR #111 MED-1)."""
    captured: list[Any] = []

    async def capture_completion(run_id: str, completion: Any) -> bool:
        captured.append(completion)
        return True

    monkeypatch.setattr(ar, "persist_run_completion", capture_completion)
    await finalize_run(
        run_id="run_abc123def456",
        target_url="https://target.example",
        created_at="2026-06-11T10:00:00Z",
        tally=_TALLY,
        recipe_id=None,
        markdown_url=None,
        report_urls=None,
        frames=[],
        emit=harness["emit"],
        owner_uid="user-a",
        schedule_id="sch_1",
        source="scheduled",
    )
    completion = captured[0]
    assert completion.owner_uid == "user-a"
    assert completion.schedule_id == "sch_1"
    assert completion.source == "scheduled"
    merged = completion.merge_fields()
    assert merged["schedule_id"] == "sch_1"
    assert merged["owner_uid"] == "user-a"
    assert merged["source"] == "scheduled"


async def test_failure_timeline_fires_summary_hook(
    harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Crashed monitoring runs email too — the hook fires on the crash
    finalize path, even when the events write fails (PR #111 MED-4)."""
    from phoenix_audit_agent.audit_runner_emit import persist_failure_timeline

    async def no_events(run_id: str, frames: Any, *, created_at: str) -> bool:
        return False

    monkeypatch.setattr(ar, "persist_run_events", no_events)
    await persist_failure_timeline(
        run_id="run_abc123def456",
        target_url="https://target.example",
        created_at="2026-06-11T10:00:00Z",
        frames=[],
        owner_uid="user-a",
        schedule_id="sch_1",
        source="scheduled",
    )
    assert harness["hook_calls"] == ["run_abc123def456"]
