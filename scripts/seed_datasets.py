#!/usr/bin/env python
"""Seed the 3 battery datasets into Phoenix + the Firestore index.

Idempotent. For each definition in `BATTERY_DATASETS`:

1. Compute the content_hash over `(name + description + source_url + items)`.
2. If the Firestore index row exists AND its content_hash matches, skip
   (no Phoenix write, no Firestore write).
3. Otherwise create the Phoenix dataset (or replace it — story-9.15 v1
   ships with create only; mutation lands in a follow-up if a corpus
   ever changes) and upsert the Firestore index row.

Usage:
    uv run python scripts/seed_datasets.py [--dry-run]

The Phoenix client config is the same env the agent service reads
(`PHOENIX_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT`). Firestore uses ADC.

Exit codes: 0 on success; 1 on any unexpected error per dataset (one
failing slug does NOT abort the remaining seeds — we log + continue).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from enum import StrEnum
from typing import Any


class SeedOutcome(StrEnum):
    """M4 (review-fleet): make seed/skip/fail distinguishable in summary
    counts. A CI/cron caller that always sees "all OK" can no longer tell
    a stale-hash skip from a real seed."""

    SEEDED = "SEEDED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("seed_datasets")


async def _seed_one(definition: Any, *, dry_run: bool) -> SeedOutcome:
    """M4: returns the precise outcome (SEEDED / SKIPPED / FAILED) so the
    summary can show counts."""
    from phoenix_audit_agent._time import utc_now_iso
    from phoenix_audit_agent.api.datasets import get_phoenix_client
    from phoenix_audit_agent.storage.datasets import get_dataset_index_store
    from phoenix_audit_agent.storage.datasets_battery import load_battery_dataset
    from phoenix_audit_agent.storage.models import DatasetIndex

    slug = definition.slug
    try:
        loaded = load_battery_dataset(definition)
    except Exception as e:
        _log.error("seed:%s load_failed error=%r", slug, e)
        return SeedOutcome.FAILED

    store = get_dataset_index_store()
    existing = await store.get_by_slug(slug)
    if existing is not None and existing.content_hash == loaded.content_hash:
        _log.info("seed:%s unchanged (hash=%s) — skipped", slug, loaded.content_hash[:14])
        return SeedOutcome.SKIPPED

    if dry_run:
        _log.info(
            "seed:%s WOULD seed (new=%s, %d items)",
            slug,
            existing is None,
            len(loaded.items),
        )
        return SeedOutcome.SKIPPED

    phoenix = get_phoenix_client()
    try:
        created = await phoenix.create(
            name=loaded.name,
            examples=loaded.items,
            description=loaded.description,
            source_url=loaded.source_url,
        )
    except Exception as e:
        _log.error("seed:%s phoenix_create_failed error=%r", slug, e)
        return SeedOutcome.FAILED

    now = utc_now_iso()
    try:
        idx = DatasetIndex(
            dataset_id=slug,
            phoenix_dataset_id=created.phoenix_dataset_id,
            name=loaded.name,
            kind="battery",
            owner_uid=None,
            agent_id=None,
            row_count=created.example_count,
            source_url=loaded.source_url,
            content_hash=loaded.content_hash,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        await store.upsert(idx)
    except Exception as e:
        _log.error("seed:%s index_upsert_failed error=%r", slug, e)
        return SeedOutcome.FAILED

    _log.info(
        "seed:%s OK (phoenix_id=%s, %d items)",
        slug,
        created.phoenix_dataset_id,
        created.example_count,
    )
    return SeedOutcome.SEEDED


async def main_async(args: argparse.Namespace) -> int:
    from phoenix_audit_agent.storage.datasets_battery import BATTERY_DATASETS

    counts: dict[SeedOutcome, int] = dict.fromkeys(SeedOutcome, 0)
    for definition in BATTERY_DATASETS:
        outcome = await _seed_one(definition, dry_run=args.dry_run)
        counts[outcome] += 1
    failures = counts[SeedOutcome.FAILED]
    _log.info(
        "seed summary: seeded=%d skipped=%d failed=%d (total=%d)",
        counts[SeedOutcome.SEEDED],
        counts[SeedOutcome.SKIPPED],
        failures,
        len(BATTERY_DATASETS),
    )
    if failures:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Phoenix Audit battery datasets")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute hashes + decide what would be seeded, but do not write.",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
