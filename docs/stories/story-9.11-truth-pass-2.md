# story-9.11 — truth-pass-2: real replay, real samples, working downloads

**Epic:** 9 (product surfaces real) · **Depends on:** story-9.10 (ux-truth-pass), story-9.4 (firebase-auth)
**Decided with Abu 2026-06-10:** frontend fixtures are deleted entirely; sample data = REAL seeded audit runs (ownerless ⇒ visible to all, labeled); replay must work for ANY finished run; `/replay` stays the public showcase, now backed by a real run.

## Why

Abu's staging walk: the product still _feels_ mocked. Root disease: the Epic-7 prototype's fixture layer (`lib/fixtures.ts`, `sample-merge.ts`) still merges 7 fake runs + 3 fake agents into every page; replay exists only for the hardcoded HERO fixture; download buttons on the sample report are handler-less `<button>`s; the report preview renders HERO data even for real runs. Every fix here replaces a fabrication with the real capability.

## Two PRs

1. **Backend** (`story/truth-pass-2` → PR a): persist the SSE event timeline per run; expose it; public featured-run endpoint; seed script (absorbs story-8.2's core).
2. **Web** (`story/truth-pass-2-web` → PR b): delete fixture layer; replay any finished run from persisted events; fix downloads; honest empty states.

## BDD acceptance criteria

### Backend

- **Given** a run driven by `drive_audit` to completion, **then** `reports/{run_id}/events.json` exists in GCS containing `{run_id, created_at, duration_sec, frames:[{t, event, data}…]}` where frames exactly mirror the emitted SSE stream INCLUDING the terminal `complete` frame, with non-decreasing relative `t` seconds, **and** the run record has `events_available: true`.
- **Given** the events upload fails, **then** the audit still completes (`complete` emitted, phase `succeeded`) and `events_available` stays `false` — contained, logged, never silent corruption.
- **Given** `GET /runs/{run_id}` for a record with `events_available`, **then** `artifact_urls` includes a fresh-signed `events.json` URL (same signing path/error disclosure as report artifacts).
- **Given** `GET /featured-run` with NO auth, **then** it returns the newest ownerless (`owner_uid == None`) `succeeded` run with `events_available=true` as a RunDetailResponse; 404 when none exists. Owned runs NEVER appear.
- **Given** `scripts/seed_demo.py` against a reachable target, **then** N real audits run through the REAL pipeline (real injector/judge/patcher/report/events) and land as ownerless records (visible-to-all samples). Idempotent per `--label` (skips if matching sample runs already exist).

### Web

- **Given** any finished run with `events_available`, **when** the user opens `/run/{runId}`, **then** the chamber replays the REAL recorded frames through the same reducer as live mode, with transport (play/pause/scrub/restart); the HERO-only redirect is gone.
- **Given** `/replay` (signed out), **then** it plays the featured sample run's real recorded frames (via `GET /featured-run`, server-fetched).
- **Given** the audits/agents/monitoring pages, **then** rows come ONLY from the backend; ownerless rows are labeled `sample`; `lib/fixtures.ts` and `lib/sample-merge.ts` no longer exist; no component imports them.
- **Given** a real run's report page, **then** the preview/downloads render THAT run's data: PDF/JSON buttons are real signed-URL links when `report_available`, an honest disabled state otherwise; the dead handler-less sample buttons are gone.
- **Given** the chamber in any mode, **then** no fixture-derived probes/cluster/recipe/receipt render — wire-truth only (live components).

## File map (backend PR)

- `storage/models.py` — `RunRecord.events_available: bool = False`; `RunCompletion.events_available: bool | None`.
- `reporter/events.py` (new) — `persist_run_events(run_id, frames, *, created_at) -> bool` (ReportEmitter reuse, contained).
- `audit_runner.py` — recording emit wrapper (relative-`t` frames); post-`complete` events persist + events_available finalize; `persist_run_events` as module-attribute seam.
- `api/runs.py` — `events.json` in artifact signing; `GET /featured-run` (no auth) reusing the detail-signing helper.
- `scripts/seed_demo.py` (new) — real seeded sample runs.
- Tests: `tests/unit/test_audit_runner.py` (events recording/containment), `tests/unit/reporter/test_events_persistence.py`, `tests/unit/api/test_runs_api.py` (events URL), `tests/unit/api/test_featured_run.py`.

## File map (web PR)

- Delete `lib/fixtures.ts`, `lib/sample-merge.ts`; strip `lib/timeline.ts` to pacing-free helpers (or delete).
- `lib/replay.ts` (new) — `replayStateAt(frames, t)` pure fold over `reduceWireEvent`; frame/document types for events.json.
- `components/chamber/use-audit-clock.ts` — duration from recorded frames, not TIMELINE.
- `components/chamber/audit-chamber.tsx` — single wire-truth canvas; replay = live components + Transport fed by `replayStateAt`; fixture canvas components (`cascade-overlay`, `probe-ledger`, `cluster-card`, `recipe-card`, `receipt`) deleted with their fixture data.
- `app/run/[runId]/page.tsx`, `app/replay/page.tsx`, `app/report/[runId]/page.tsx`, `components/artifacts/report-preview.tsx`, `components/history/audits-client.tsx`, `components/agents/*`, `components/monitoring/monitoring-client.tsx`, `app/{audits,agents,monitoring,recipe}` pages — backend-data-only rendering, sample labeling from `owner_uid == null`, real download links.
- `lib/api.ts` — `events_available` on RunDto; featured-run fetcher.
- Tests: vitest for `replayStateAt` parity with live reducer, run-page routing, report download states, sample labeling.

## Gates

Standard: per-app pytest, ruff, ty, vitest, tsc, max-lines, pre-commit. Verification beyond gates: local web+agent click-through (Playwright) — start a real local audit, watch live, replay it after finish, download artifacts.
