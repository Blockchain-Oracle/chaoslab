#!/usr/bin/env python
"""Seed REAL sample audits (story-9.11; absorbs story-8.2's core).

Runs N full audits through the REAL pipeline (Injector -> Judge -> Patcher ->
signed report -> replay timeline) against a live target, registering each as
an OWNERLESS record. Ownerless rows are the product's visible-to-all,
clearly-labeled sample data — and /featured-run serves the newest one to the
public /replay showcase. No fixtures, no fabrication.

Usage (local ADC against the staging project; same env the agent service uses):
    uv run python scripts/seed_demo.py --target-url https://<target-agent>.run.app --count 3

Idempotent: exits early when --count ownerless replayable samples already
exist; --force adds more anyway.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.audit_runner import drive_audit
from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.storage.models import RunCompletion, RunRecord
from phoenix_audit_agent.storage.runs import (
    create_run_record,
    get_run_store,
    persist_run_completion,
)


async def existing_sample_count() -> int:
    rows, _truncated = await get_run_store().list_runs(limit=200, visible_to=None)
    return sum(
        1 for r in rows if r.owner_uid is None and r.phase == "succeeded" and r.events_available
    )


async def seed_one(target_url: str, runs_per_fault: int) -> str:
    run_id = "run_" + secrets.token_hex(6)
    created = utc_now_iso()
    await create_run_record(
        RunRecord(run_id=run_id, target_url=target_url, created_at=created, owner_uid=None)
    )

    async def emit(event: str, payload: dict) -> None:
        # persistence_failed surfaced loudly: a seed whose registry write
        # failed must not read as a clean "seed complete".
        suffix = (
            " PERSISTENCE_FAILED"
            if event == "complete" and payload.get("persistence_failed")
            else ""
        )
        print(f"  [{run_id}] {event}{suffix}", flush=True)

    try:
        await drive_audit(
            run_id=run_id,
            target_url=target_url,
            runs_per_fault=runs_per_fault,
            emit=emit,
            set_phase=lambda _p: None,
            created_at=created,
        )
    except Exception:
        # Ownerless records are PUBLIC sample rows — a crashed seed must not
        # strand a queued-forever phantom in everyone's registry.
        await persist_run_completion(
            run_id,
            RunCompletion(
                run_id=run_id,
                target_url=target_url,
                created_at=created,
                phase="failed",
                finished_at=utc_now_iso(),
            ),
        )
        raise
    return run_id


async def amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-url", required=True, help="Live target agent to audit.")
    parser.add_argument("--count", type=int, default=3, help="Sample runs to ensure exist.")
    parser.add_argument("--runs-per-fault", type=int, default=2)
    parser.add_argument("--force", action="store_true", help="Seed even if samples exist.")
    args = parser.parse_args()

    # Same fail-loud observability posture as the service — traces are the
    # judge's evidence; an untraced audit is not a real audit.
    from phoenix_audit_agent.observability import setup_logging, setup_phoenix_otel

    settings = get_settings()
    setup_logging(env=settings.environment)
    setup_phoenix_otel(settings)

    have = await existing_sample_count()
    if have >= args.count and not args.force:
        print(f"already seeded: {have} ownerless replayable sample runs exist (use --force)")
        return 0

    todo = args.count if args.force else args.count - have
    print(f"seeding {todo} real audit(s) against {args.target_url}")
    for i in range(todo):
        print(f"audit {i + 1}/{todo} ...", flush=True)
        run_id = await seed_one(args.target_url, args.runs_per_fault)
        print(f"  done: {run_id}")
    print("seed complete")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(amain()))
