"""Story-9.15 — `DatasetIndex` pydantic model contract.

The Firestore index row that maps slug → phoenix_dataset_id and carries the
three-kinds invariant: battery ⇒ owner_uid is None, uploaded ⇒ owner_uid
is set, regression ⇒ owner_uid + agent_id both set. The discriminator on
`kind` makes a typo a parse-time error, never a silent drop (docs/architecture.md
silent-failure pattern #6 in spirit — wrapper-level invariants beat
list-level checks).

These tests pin the contract BEFORE the implementation lands. RED first.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_battery_dataset_index_requires_owner_uid_none() -> None:
    """`kind="battery"` with `owner_uid` set must raise — battery sets are
    visible to all and own no tenant."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    # The happy path.
    ok = DatasetIndex(
        dataset_id="harmbench-v1-sample",
        phoenix_dataset_id="RGF0YXNldDox",
        name="HarmBench v1 (sample)",
        kind="battery",
        owner_uid=None,
        agent_id=None,
        row_count=50,
        source_url="https://github.com/centerforaisafety/HarmBench",
        content_hash="sha256:abc",
        created_at="2026-06-11T07:00:00+00:00",
        updated_at="2026-06-11T07:00:00+00:00",
    )
    assert ok.kind == "battery"

    # The contract violation.
    with pytest.raises(ValidationError, match="battery"):
        DatasetIndex(
            dataset_id="harmbench-v1-sample",
            phoenix_dataset_id="RGF0YXNldDox",
            name="HarmBench v1 (sample)",
            kind="battery",
            owner_uid="uid_alice",  # forbidden
            agent_id=None,
            row_count=50,
            source_url=None,
            content_hash="sha256:abc",
            created_at="2026-06-11T07:00:00+00:00",
            updated_at="2026-06-11T07:00:00+00:00",
        )


def test_uploaded_dataset_index_requires_owner_uid_set() -> None:
    """`kind="uploaded"` MUST carry `owner_uid` — uploaded sets are scoped
    per-user, and `None` would silently make them world-visible."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    ok = DatasetIndex(
        dataset_id="ds_a1b2c3d4",
        phoenix_dataset_id="RGF0YXNldDoy",
        name="Meridian — refusal corpus",
        kind="uploaded",
        owner_uid="uid_alice",
        agent_id=None,
        row_count=120,
        source_url=None,
        content_hash="sha256:def",
        created_at="2026-06-11T08:00:00+00:00",
        updated_at="2026-06-11T08:00:00+00:00",
    )
    assert ok.owner_uid == "uid_alice"

    with pytest.raises(ValidationError, match="uploaded"):
        DatasetIndex(
            dataset_id="ds_a1b2c3d4",
            phoenix_dataset_id="RGF0YXNldDoy",
            name="Meridian — refusal corpus",
            kind="uploaded",
            owner_uid=None,  # forbidden
            agent_id=None,
            row_count=120,
            source_url=None,
            content_hash="sha256:def",
            created_at="2026-06-11T08:00:00+00:00",
            updated_at="2026-06-11T08:00:00+00:00",
        )


def test_regression_dataset_index_requires_owner_uid_and_agent_id() -> None:
    """`kind="regression"` MUST carry BOTH `owner_uid` and `agent_id` —
    regression sets always tie to an agent owned by a user."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    ok = DatasetIndex(
        dataset_id="regression-meridian-prior-auth",
        phoenix_dataset_id="RGF0YXNldDoz",
        name="Regression — Meridian prior-auth",
        kind="regression",
        owner_uid="uid_alice",
        agent_id="agt_meridian001",
        row_count=37,
        source_url=None,
        content_hash="sha256:ghi",
        created_at="2026-06-11T09:00:00+00:00",
        updated_at="2026-06-11T09:00:00+00:00",
    )
    assert ok.agent_id == "agt_meridian001"

    # Missing owner_uid → reject.
    with pytest.raises(ValidationError, match="regression"):
        DatasetIndex(
            dataset_id="regression-meridian-prior-auth",
            phoenix_dataset_id="RGF0YXNldDoz",
            name="Regression — Meridian prior-auth",
            kind="regression",
            owner_uid=None,
            agent_id="agt_meridian001",
            row_count=0,
            source_url=None,
            content_hash="sha256:ghi",
            created_at="2026-06-11T09:00:00+00:00",
            updated_at="2026-06-11T09:00:00+00:00",
        )

    # Missing agent_id → reject.
    with pytest.raises(ValidationError, match="regression"):
        DatasetIndex(
            dataset_id="regression-meridian-prior-auth",
            phoenix_dataset_id="RGF0YXNldDoz",
            name="Regression — Meridian prior-auth",
            kind="regression",
            owner_uid="uid_alice",
            agent_id=None,
            row_count=0,
            source_url=None,
            content_hash="sha256:ghi",
            created_at="2026-06-11T09:00:00+00:00",
            updated_at="2026-06-11T09:00:00+00:00",
        )


def test_kind_typo_rejected_at_parse_time() -> None:
    """A typo'd `kind` is a parse-time error, never a silent drop."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    with pytest.raises(ValidationError, match="kind"):
        DatasetIndex(
            dataset_id="ds_a1b2c3d4",
            phoenix_dataset_id="RGF0YXNldDoy",
            name="Typo dataset",
            kind="upload",  # ty: ignore[invalid-argument-type]  battery|regression|uploaded only
            owner_uid="uid_alice",
            agent_id=None,
            row_count=1,
            source_url=None,
            content_hash="sha256:x",
            created_at="2026-06-11T08:00:00+00:00",
            updated_at="2026-06-11T08:00:00+00:00",
        )


def test_slug_pattern_enforced() -> None:
    """`dataset_id` must be the URL-safe slug pattern `[a-z0-9_-]+`.
    URL paths read it verbatim — a bad character is a routing surprise."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    with pytest.raises(ValidationError, match="dataset_id"):
        DatasetIndex(
            dataset_id="Has Spaces and CAPS",
            phoenix_dataset_id="RGF0YXNldDoy",
            name="x",
            kind="uploaded",
            owner_uid="uid_alice",
            agent_id=None,
            row_count=1,
            source_url=None,
            content_hash="sha256:x",
            created_at="2026-06-11T08:00:00+00:00",
            updated_at="2026-06-11T08:00:00+00:00",
        )


def test_phoenix_id_required_non_empty() -> None:
    """`phoenix_dataset_id` is the bridge to the row store; empty would
    silently break the deep-link + read paths."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    with pytest.raises(ValidationError, match="phoenix_dataset_id"):
        DatasetIndex(
            dataset_id="ds_a1b2c3d4",
            phoenix_dataset_id="",
            name="x",
            kind="uploaded",
            owner_uid="uid_alice",
            agent_id=None,
            row_count=1,
            source_url=None,
            content_hash="sha256:x",
            created_at="2026-06-11T08:00:00+00:00",
            updated_at="2026-06-11T08:00:00+00:00",
        )


def test_row_count_non_negative() -> None:
    """A negative row_count silently breaks the listing 'no rows yet' affordance."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    with pytest.raises(ValidationError, match="row_count"):
        DatasetIndex(
            dataset_id="ds_a1b2c3d4",
            phoenix_dataset_id="RGF0YXNldDoy",
            name="x",
            kind="uploaded",
            owner_uid="uid_alice",
            agent_id=None,
            row_count=-1,
            source_url=None,
            content_hash="sha256:x",
            created_at="2026-06-11T08:00:00+00:00",
            updated_at="2026-06-11T08:00:00+00:00",
        )


def test_extra_fields_ignored_for_forward_compat() -> None:
    """Index docs read with `extra="ignore"` so a Wave-D field landing in
    Firestore doesn't crash an older deployment."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    ok = DatasetIndex.model_validate(
        {
            "dataset_id": "ds_a1b2c3d4",
            "phoenix_dataset_id": "RGF0YXNldDoy",
            "name": "x",
            "kind": "uploaded",
            "owner_uid": "uid_alice",
            "agent_id": None,
            "row_count": 1,
            "source_url": None,
            "content_hash": "sha256:x",
            "created_at": "2026-06-11T08:00:00+00:00",
            "updated_at": "2026-06-11T08:00:00+00:00",
            "future_field_we_havent_invented": "lol",
        }
    )
    assert ok.kind == "uploaded"
