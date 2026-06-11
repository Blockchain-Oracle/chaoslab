"""Dataset evidence chain at audit finalize (story-9.15).

This module is the dataset half of the post-pipeline work — the audit
finalize plumbing itself lives in `audit_runner_emit.py`. Split so
neither module brushes the 400-line cap and each carries a single
responsibility.

Three public surfaces the finalize path calls:

- `dataset_snapshot_fields(idx, version_id)` — builds the merge dict that
  populates `RunRecord.dataset_*` / `RunCompletion.dataset_*` so the
  signed report cover names the corpus and the JSON artifact carries the
  Phoenix bridge ids.
- `build_dataset_snapshot(dataset_id, run_id)` — contained snapshot
  builder. Looks up the index, hits Phoenix for a version_id, logs +
  returns None on any failure so the audit finalizes cleanly even if
  Phoenix is down at the wrong moment.
- `try_regression_upsert(agent_id, owner_uid, failing_rows, run_id)` —
  contained regression-set upsert. Returns the new version_id on success
  or None on any failure.

The lower-level `upsert_regression_set` (no `try_` prefix) is exported
for tests that exercise the upsert directly without the finalize
plumbing — it raises on Phoenix-side failures so the test sees the real
exception.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from pydantic import ValidationError

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.phoenix_tools.dataset_client import (
    PhoenixDatasetNotFoundError,
    PhoenixUnavailableError,
)

_log = structlog.get_logger(__name__)

# Round-3+4 review: contained-failure tuple covers the NETWORK / STORE
# OUTAGE families only. ValidationError is read-path-specific (a corrupt
# Firestore DatasetIndex doc) and is handled at the read call sites in
# build_dataset_snapshot — NOT in this shared tuple, so the upsert write
# path's `DatasetIndex(...)` construction doesn't silently swallow
# programming errors (round-4 HIGH-3).
_CONTAINED_STORE_ERRORS: tuple[type[BaseException], ...] = (
    httpx.HTTPError,
    TimeoutError,
    ConnectionError,
)

try:
    # Firestore raises google.api_core.exceptions.GoogleAPIError on outage —
    # NOT httpx.HTTPError (I-1). Import is optional so tests using the
    # in-memory fake don't need the google package at runtime.
    from google.api_core.exceptions import GoogleAPIError as _GoogleAPIError

    _CONTAINED_STORE_ERRORS = (*_CONTAINED_STORE_ERRORS, _GoogleAPIError)
except ImportError:  # pragma: no cover — google-api-core is a prod dep
    pass


@dataclass(frozen=True)
class RegressionSnapshot:
    """Phoenix-side identifiers for the regression set after an upsert."""

    phoenix_dataset_id: str
    version_id: str
    row_count: int


# 200-row cap per the story-9.15 BDD ("most-recent 200, deduped on case_id").
REGRESSION_CAP = 200


def dataset_snapshot_fields(*, idx: Any, version_id: str) -> dict[str, Any]:
    """Build the run-record merge dict that carries the dataset evidence
    chain (story-9.15). Returns the exact field set the report cover +
    JSON artifact pull from."""
    return {
        "dataset_id": idx.dataset_id,
        "dataset_name": idx.name,
        "dataset_phoenix_id": idx.phoenix_dataset_id,
        "dataset_version_id": version_id,
        "dataset_kind": idx.kind,
        "dataset_source_url": idx.source_url,
    }


def _regression_slug(agent_id: str) -> str:
    """Canonical slug for an agent's regression set."""
    return f"regression-{agent_id}"


def _case_id(row: dict[str, Any]) -> str:
    """Pull case_id off a failing-probe row with a typed error path.

    I1 (review-fleet finding): bare `row["case_id"]` would raise KeyError
    deep inside `asyncio.gather` if upstream ever emits a row missing the
    field. Surface the bad shape at the boundary with a usable error.
    """
    case_id = row.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        msg = f"regression row missing case_id; got row keys={sorted(row.keys())!r}"
        raise ValueError(msg)
    return case_id


def _dedupe_newest_wins(
    new_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge two row lists, deduped on `case_id`. New rows beat existing
    rows of the same `case_id`. Result is sorted **oldest-first** —
    existing rows first (in their original order), then any genuinely-new
    rows. Callers that need a most-recent cap take `[-cap:]`. Raises
    `ValueError` if any row lacks `case_id` (see `_case_id`)."""
    by_case: dict[str, dict[str, Any]] = {_case_id(r): r for r in existing_rows}
    for r in new_rows:
        by_case[_case_id(r)] = r  # newest wins
    return list(by_case.values())


def _dedupe_items_newest_wins(items: list[Any]) -> list[Any]:
    """Same as `_dedupe_newest_wins` but on `FlatDatasetItem` instances;
    later occurrences win (Phoenix returns the order we appended)."""
    by_case: dict[str, Any] = {}
    for item in items:
        by_case[item.case_id] = item
    return list(by_case.values())


async def _create_regression_dataset(
    *,
    slug: str,
    agent_id: str,
    owner_uid: str,
    new_rows: list[dict[str, Any]],
    phoenix: Any,
    idx_store: Any,
    now: str,
) -> RegressionSnapshot:
    """First-failure path: create the Phoenix dataset + the Firestore index row."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    created = await phoenix.create(
        name=f"Regression — {agent_id}",
        examples=new_rows,
        description=f"Auto-populated regression set for agent {agent_id}",
        source_url=None,
    )
    await idx_store.upsert(
        DatasetIndex(
            dataset_id=slug,
            phoenix_dataset_id=created.phoenix_dataset_id,
            name=f"Regression — {agent_id}",
            kind="regression",
            owner_uid=owner_uid,
            agent_id=agent_id,
            row_count=created.example_count,
            source_url=None,
            content_hash=f"sha256:regression:{slug}:{now}",
            created_at=now,
            updated_at=now,
        )
    )
    return RegressionSnapshot(
        phoenix_dataset_id=created.phoenix_dataset_id,
        version_id=created.version_id,
        row_count=created.example_count,
    )


async def _append_regression_examples(
    *,
    existing_idx: Any,
    new_rows: list[dict[str, Any]],
    phoenix: Any,
    idx_store: Any,
    now: str,
) -> RegressionSnapshot:
    """Subsequent-failure path: dedup against the existing Phoenix examples,
    add the merged result, refresh the index row's row_count.

    Known limitation (I5): Phoenix's `add_examples_to_dataset` cannot
    remove rows, so case_id collisions are resolved by the in-memory fake
    at read time. The production SDK path will need a recreate-or-merge
    strategy — tracked for story-9.16. The finalize path sets
    `RunCompletion.regression_overwrite_mode = "fake_newest_wins"` so the
    fallback is visible in the audit metadata (silent-failure pattern #4).
    """
    from phoenix_audit_agent.storage.models import DatasetIndex

    existing_items = await phoenix.get_examples(existing_idx.phoenix_dataset_id)
    existing_rows = [i.model_dump() for i in existing_items]
    # `[-REGRESSION_CAP:]` keeps the NEWEST 200 (Finding A).
    deduped = _dedupe_newest_wins(new_rows, existing_rows)
    capped = deduped[-REGRESSION_CAP:]

    version_id = await phoenix.add_examples(existing_idx.phoenix_dataset_id, capped)
    refreshed_items = await phoenix.get_examples(existing_idx.phoenix_dataset_id)
    refreshed = _dedupe_items_newest_wins(refreshed_items)

    await idx_store.upsert(
        DatasetIndex(
            dataset_id=existing_idx.dataset_id,
            phoenix_dataset_id=existing_idx.phoenix_dataset_id,
            name=existing_idx.name,
            kind="regression",
            owner_uid=existing_idx.owner_uid,
            agent_id=existing_idx.agent_id,
            row_count=len(refreshed),
            source_url=existing_idx.source_url,
            content_hash=f"sha256:regression:{existing_idx.dataset_id}:{now}",
            created_at=existing_idx.created_at,
            updated_at=now,
        )
    )
    return RegressionSnapshot(
        phoenix_dataset_id=existing_idx.phoenix_dataset_id,
        version_id=version_id,
        row_count=len(refreshed),
    )


async def upsert_regression_set(
    *,
    agent_id: str,
    owner_uid: str,
    failing_rows: list[dict[str, Any]],
    phoenix: Any,
    idx_store: Any,
    now: str,
) -> RegressionSnapshot:
    """Append failing-probe rows into the agent's regression dataset
    (story-9.15 BDD).

    First failure for this agent → `create_dataset`; subsequent failures →
    `add_examples_to_dataset` (Phoenix versioning). Dedup-by-`case_id`
    happens server-side (newest wins) BEFORE the SDK call, then the union
    is capped at REGRESSION_CAP rows.

    Raises `ValueError` if any failing row lacks a `case_id`; raises
    whatever the Phoenix SDK raises on network failure (the caller wraps).
    """
    slug = _regression_slug(agent_id)
    existing_idx = await idx_store.get_by_slug(slug)
    if existing_idx is None:
        # `[-REGRESSION_CAP:]` keeps the NEWEST 200 (Finding A, review-fleet
        # pass 2): the BDD says "most-recent 200, deduped on case_id". The
        # dedup helper preserves oldest-first order, so the tail is newest.
        new_rows = _dedupe_newest_wins(failing_rows, [])[-REGRESSION_CAP:]
        return await _create_regression_dataset(
            slug=slug,
            agent_id=agent_id,
            owner_uid=owner_uid,
            new_rows=new_rows,
            phoenix=phoenix,
            idx_store=idx_store,
            now=now,
        )
    return await _append_regression_examples(
        existing_idx=existing_idx,
        new_rows=failing_rows,
        phoenix=phoenix,
        idx_store=idx_store,
        now=now,
    )


async def build_dataset_snapshot(*, dataset_id: str, run_id: str) -> dict[str, Any] | None:
    """Contained snapshot builder for `finalize_run`.

    Returns the snapshot fields on success, None on any failure (with a
    structured log line). Any failure mode keeps the audit finalizing —
    the cover line falls back to "synthetic battery" rather than blocking
    a successful audit on a dataset-evidence hiccup.
    """
    from phoenix_audit_agent.api.datasets import get_phoenix_client
    from phoenix_audit_agent.storage.datasets import get_dataset_index_store

    # Contained catch families (round-3 + round-4 HIGH-3): ValidationError
    # is specific to corrupt-doc-on-READ and is caught HERE, not in the
    # shared tuple — the upsert write path must not silently swallow a
    # `DatasetIndex(...)` construction error.
    try:
        idx = await get_dataset_index_store().get_by_slug(dataset_id)
    except (*_CONTAINED_STORE_ERRORS, ValidationError) as e:
        _log.warning(
            "finalize.dataset_index_lookup_failed",
            run_id=run_id,
            dataset_id=dataset_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        return None
    if idx is None:
        _log.warning("finalize.dataset_index_missing", run_id=run_id, dataset_id=dataset_id)
        return None

    # Capture the REAL Phoenix version_id; if the lookup fails (outage OR
    # TOCTOU delete between the index read and now), return None so the
    # signed report falls back cleanly to "synthetic battery". A
    # "version_id=unknown" snapshot would silently pin regulator-facing
    # evidence to a meaningless string. Round-4 MED: split bridge-drift
    # (Phoenix says NotFound) from outage so they're distinguishable in
    # the audit log.
    try:
        version_id = await get_phoenix_client().get_current_version_id(idx.phoenix_dataset_id)
    except PhoenixDatasetNotFoundError as e:
        _log.warning(
            "finalize.dataset_bridge_drift",
            run_id=run_id,
            dataset_id=dataset_id,
            phoenix_dataset_id=idx.phoenix_dataset_id,
            error=str(e),
        )
        return None
    except PhoenixUnavailableError as e:
        _log.warning(
            "finalize.dataset_version_outage",
            run_id=run_id,
            dataset_id=dataset_id,
            error=str(e),
        )
        return None

    return dataset_snapshot_fields(idx=idx, version_id=version_id)


async def try_regression_upsert(
    *,
    agent_id: str,
    owner_uid: str,
    failing_rows: list[dict[str, Any]],
    run_id: str,
) -> str | None:
    """Contained regression-upsert wrapper for `finalize_run`.

    Returns the new version_id on success or None when Phoenix was
    unreachable / the upsert raised. The finalize path uses None to
    decide whether to set the fake-only marker.
    """
    from phoenix_audit_agent.api.datasets import get_phoenix_client
    from phoenix_audit_agent.storage.datasets import get_dataset_index_store

    # M-NEW-1: narrow to Phoenix + network families. A ValueError from
    # `_case_id` (malformed failing-row shape) propagates — that's a
    # programming bug in the caller, not a Phoenix outage to swallow.
    try:
        snap = await upsert_regression_set(
            agent_id=agent_id,
            owner_uid=owner_uid,
            failing_rows=failing_rows,
            phoenix=get_phoenix_client(),
            idx_store=get_dataset_index_store(),
            now=utc_now_iso(),
        )
    except PhoenixDatasetNotFoundError as e:
        # Round-3 MED-2 + round-5 MED-2: split bridge-drift (index says
        # Phoenix has the dataset, Phoenix says NotFound) from outage so the
        # two are distinguishable in the audit log. The `phoenix_dataset_id`
        # key mirrors the dataset-side split for log-analyzer symmetry.
        _log.warning(
            "finalize.regression_bridge_drift",
            run_id=run_id,
            agent_id=agent_id,
            phoenix_dataset_id=str(e),
            error=str(e),
        )
        return None
    except (PhoenixUnavailableError, *_CONTAINED_STORE_ERRORS) as e:
        _log.warning(
            "finalize.regression_upsert_failed",
            run_id=run_id,
            agent_id=agent_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        return None
    return snap.version_id


__all__ = [
    "REGRESSION_CAP",
    "RegressionSnapshot",
    "build_dataset_snapshot",
    "dataset_snapshot_fields",
    "try_regression_upsert",
    "upsert_regression_set",
]
