"""Persistent record shapes. Every record carries org/owner fields now so
auth scoping (story-9.4) is a query filter, not a migration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

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
    # A replay timeline (reports/{run_id}/events.json) exists for this run.
    events_available: bool = False
    # Story 9.5: the monitoring schedule that launched this run (None for
    # manual runs). The finalize email hook resolves `deliver_email` from it.
    schedule_id: str | None = None
    mr_url: str | None = None
    org_id: str = "default"
    owner_uid: str | None = None
    # Story 9.15: dataset snapshot. Set at finalize when the run was launched
    # with `RunRequest.dataset_id`. The signed report cover renders
    # `Dataset: <dataset_name>` (and `source_url` when present); the JSON
    # artifact emits all six fields. `dataset_name` is the canonical string
    # snapshot — when the dataset is later deleted, the run record + signed
    # PDF stay valid evidence.
    dataset_id: str | None = None
    dataset_name: str | None = None
    dataset_phoenix_id: str | None = None
    dataset_version_id: str | None = None
    dataset_kind: str | None = None
    dataset_source_url: str | None = None
    # Story 9.15: how the regression upsert resolved case_id collisions on
    # this run. Currently always "newest_wins" when an upsert happened
    # (story-9.16 will add SDK-side strategies). Declared on RunRecord so a
    # read-back via model_validate doesn't drop it (silent-failure H-NEW-1
    # from the second review pass).
    regression_overwrite_mode: str | None = None


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
    events_available: bool | None = None
    mr_url: str | None = None
    # Story 9.5: launch-time identity the heal-path merge must NOT drop —
    # when the launch-time create failed (contained Firestore blip), the
    # finalize merge is the record's ONLY write. Without these, a healed
    # scheduled run reads back as a manual, ownerless run and the summary
    # email silently never sends.
    source: RunSource | None = None
    owner_uid: str | None = None
    schedule_id: str | None = None
    # Story 9.15: same shape as `RunRecord` so the finalize path can write
    # the dataset snapshot through `merge_fields` without a side-channel.
    # The fields live on `RunRecord` (extra="ignore") AND here (extra="forbid")
    # so a typo'd snapshot key fails loudly at finalize, never silently drops.
    dataset_id: str | None = None
    dataset_name: str | None = None
    dataset_phoenix_id: str | None = None
    dataset_version_id: str | None = None
    dataset_kind: str | None = None
    dataset_source_url: str | None = None
    # Story 9.15: marker for the regression-set upsert. "newest_wins" when an
    # upsert ran (case_id collisions resolve newest-wins); None when no
    # upsert ran. Story-9.16 will add SDK-side strategies. The marker rides
    # to Firestore via merge_fields() and is declared on RunRecord too so a
    # read-back via model_validate doesn't drop it (extra="ignore" rule).
    regression_overwrite_mode: str | None = None

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


class GitLabConnection(BaseModel):
    """Per-user GitLab OAuth connection (story-9.17), stored on
    `users/{uid}.gitlab`. Tokens live ONLY in Firestore — `UserProfile`
    excludes this field from every dump so /profile can't leak them."""

    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    # Epoch seconds (authlib token shape). GitLab access tokens live 2h;
    # the refresh gate compares against now+60s. gt=0 keeps a clock-skewed
    # or zeroed value from reading as expired-forever (refresh storm).
    expires_at: float = Field(gt=0)
    username: str = Field(min_length=1)
    gitlab_user_id: int
    connected_at: str = Field(min_length=1)


class GitLabOAuthState(BaseModel):
    """Single-use PKCE state doc (`gitlab_oauth_states/{state}`) — the
    code_verifier never leaves the server."""

    model_config = ConfigDict(extra="ignore")

    state: str = Field(min_length=1)
    uid: str = Field(min_length=1)
    code_verifier: str = Field(min_length=1)
    created_at: str = Field(min_length=1)


HostingPref = Literal["default", "byo"]


class UserProfile(BaseModel):
    """The users/{uid} settings document. extra='ignore' so later stories
    (gitlab connection blob, wizard fields) can land without migration.
    Email mirrors the verified token at read/write time — display
    convenience, not identity."""

    model_config = ConfigDict(extra="ignore")

    uid: str = Field(min_length=1)
    email: str | None = None
    org_name: str | None = None
    framework_default: str = Field(default="EU AI Act", min_length=1)
    hosting_pref: HostingPref = "default"
    onboarded: bool = False
    # None ⇔ never persisted (GET-computed defaults). A stored profile always
    # carries both timestamps; empty strings are unrepresentable.
    created_at: str | None = Field(default=None, min_length=1)
    updated_at: str | None = Field(default=None, min_length=1)
    # Story-9.17: populated on VALIDATION (the backend reads tokens off the
    # model) but `exclude=True` strips it from every dump — GET /profile
    # returns this model verbatim, and tokens must never reach a browser.
    gitlab: GitLabConnection | None = Field(default=None, exclude=True)

    @field_validator("gitlab", mode="before")
    @classmethod
    def _gitlab_lenient(cls, v: Any) -> Any:
        # A malformed/legacy gitlab blob must degrade to "not connected"
        # (reconnect fixes it) — never 500 every /profile read for the user.
        # The degradation is LOGGED (error keys only, never values) so schema
        # drift doesn't silently disconnect a cohort.
        if v is None or isinstance(v, GitLabConnection):
            return v
        try:
            return GitLabConnection.model_validate(v)
        except ValidationError as exc:
            import structlog

            structlog.get_logger(__name__).warning(
                "gitlab_blob_degraded_to_disconnected",
                invalid_fields=[str(e["loc"]) for e in exc.errors()],
            )
            return None


Cadence = Literal["hourly", "daily"]


class ScheduleRecord(BaseModel):
    """A continuous-monitoring schedule. The tick claims due schedules by
    advancing next_fire_at BEFORE launching — crash-after-claim skips one
    tick; it never double-fires."""

    model_config = ConfigDict(extra="ignore")

    schedule_id: str = Field(min_length=1)
    agent_id: str | None = None
    target_url: str = Field(min_length=1)
    cadence: Cadence = "daily"
    enabled: bool = True
    next_fire_at: str = Field(min_length=1)
    last_fired_at: str | None = None
    last_run_id: str | None = None
    deliver_email: bool = False
    email_recipient: str | None = None
    created_at: str = Field(min_length=1)
    org_id: str = "default"
    owner_uid: str | None = None


DatasetKind = Literal["battery", "regression", "uploaded"]


class DatasetIndex(BaseModel):
    """The thin Firestore `datasets/{slug}` index row.

    Phoenix Datasets holds the actual examples — this index carries only the
    bridge fields our app needs: slug + phoenix_dataset_id mapping, ownership,
    kind, agent linkage (regression only), and an idempotency hash for the
    seed script.

    Three-kinds invariant (story-9.15):
    - `battery`    ⇒ `owner_uid is None` and `agent_id is None`
    - `uploaded`   ⇒ `owner_uid` is set and `agent_id is None`
    - `regression` ⇒ both `owner_uid` and `agent_id` are set

    The model_validator enforces all three in one place so a future kind
    addition has a single touch-point.
    """

    model_config = ConfigDict(extra="ignore")

    # `[a-z0-9_-]+`: URL-safe so the slug travels verbatim in routes.
    dataset_id: str = Field(min_length=1, pattern=r"^[a-z0-9_-]+$")
    # Bridge to Phoenix. Empty string would silently break the deep-link.
    phoenix_dataset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: DatasetKind
    owner_uid: str | None = None
    agent_id: str | None = None
    row_count: int = Field(ge=0)
    source_url: str | None = None
    # SHA-256 over (items + name + description + source_url) — the seed script
    # skips writes when the stored hash matches.
    content_hash: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def _enforce_kind_invariants(self) -> DatasetIndex:
        if self.kind == "battery" and (self.owner_uid is not None or self.agent_id is not None):
            msg = "battery dataset must have owner_uid=None and agent_id=None"
            raise ValueError(msg)
        if self.kind == "uploaded" and self.owner_uid is None:
            msg = "uploaded dataset must carry owner_uid"
            raise ValueError(msg)
        if self.kind == "uploaded" and self.agent_id is not None:
            msg = "uploaded dataset must have agent_id=None"
            raise ValueError(msg)
        if self.kind == "regression" and (self.owner_uid is None or self.agent_id is None):
            msg = "regression dataset must carry both owner_uid and agent_id"
            raise ValueError(msg)
        return self


__all__ = [
    "AgentRecord",
    "Cadence",
    "DatasetIndex",
    "DatasetKind",
    "Framework",
    "HostingPref",
    "RunCompletion",
    "RunPhase",
    "RunRecord",
    "RunSource",
    "ScheduleRecord",
    "UserProfile",
]
