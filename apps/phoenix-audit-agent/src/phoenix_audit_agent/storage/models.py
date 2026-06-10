"""Persistent record shapes. Every record carries org/owner fields now so
auth scoping (story-9.4) is a query filter, not a migration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Framework = Literal[
    "adk-a2a",
    "langchain-http",
    "crewai-http",
    "openai-agents",
    "http-blackbox",
]

RunSource = Literal["manual", "scheduled"]

# Single source of truth for run phases — main.py and the registry share it so
# a typo'd phase can never be persisted into the regulator-facing registry.
RunPhase = Literal["queued", "injector", "judge", "patcher", "succeeded", "failed"]


class RunRecord(BaseModel):
    """One row in the audit registry. Artifact URLs are NOT stored — v4 signed
    URLs expire; object paths are deterministic (reports/{run_id}/..., and
    {recipe_id}.md) and re-signed at read time."""

    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(min_length=1)
    agent_id: str | None = None
    target_url: str = Field(min_length=1)
    framework_label: str = "EU AI Act · high-risk system"
    source: RunSource = "manual"
    phase: RunPhase = "queued"
    created_at: str = Field(min_length=1)
    finished_at: str | None = None
    duration_sec: float | None = None
    passed: int = 0
    failed: int = 0
    errored: int = 0
    transport_failed: int = 0
    recipe_id: str | None = None
    report_available: bool = False
    mr_url: str | None = None
    org_id: str = "default"
    owner_uid: str | None = None


class RunCompletion(BaseModel):
    """Typed finalize payload — extra='forbid' makes a typo'd field a
    constructor error instead of a silently-dropped write (the registry reads
    with extra='ignore'). Carries enough keys (run_id/target_url/created_at)
    to heal a failed create via merge."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    target_url: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    phase: RunPhase
    finished_at: str | None = None
    duration_sec: float | None = None
    passed: int | None = None
    failed: int | None = None
    errored: int | None = None
    transport_failed: int | None = None
    recipe_id: str | None = None
    report_available: bool | None = None
    mr_url: str | None = None

    def merge_fields(self) -> dict[str, object]:
        """Only the fields actually set — merge must not null-out create data."""
        return self.model_dump(exclude_none=True)


class AgentRecord(BaseModel):
    """A registered target agent."""

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    framework: Framework
    tier: int = Field(ge=1, le=3)
    registered_at: str = Field(min_length=1)
    status: Literal["ok", "unreachable"] = "ok"
    org_id: str = "default"
    owner_uid: str | None = None


__all__ = ["AgentRecord", "Framework", "RunCompletion", "RunPhase", "RunRecord", "RunSource"]
