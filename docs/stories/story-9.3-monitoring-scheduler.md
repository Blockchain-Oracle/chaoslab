# Story 9.3 — Continuous monitoring: schedules + Cloud Scheduler tick

**Epic:** Epic 9 — product surfaces real
**Status:** IN PROGRESS
**Depends on:** story-9.1-firestore-persistence, story-9.2-web-real-wiring

## Why

The prototype's Monitoring surface promises scheduled audits ("EU AI Act
Article 72 — post-market monitoring"). Decision locked with Abu 2026-06-10:
scheduled BATTERY RE-RUNS (not trace-window judging) — one Cloud Scheduler
job ticks an internal endpoint every 15 minutes; the endpoint claims due
schedules from Firestore and launches real runs tagged `source="scheduled"`,
which already flow into the registry + audits UI from S9.1/S9.2.

## BDD acceptance criteria

1. **Schedules CRUD.** `POST /schedules` upserts a schedule (agent_id,
   target_url, cadence hourly|daily, deliver_email flag + recipient,
   enabled); `GET /schedules` lists; `PATCH /schedules/{id}` toggles
   enabled / changes cadence. Records carry org/owner fields.
2. **Tick fires due schedules exactly once.** `POST /internal/scheduler-tick`
   claims schedules where `enabled AND next_fire_at <= now` by advancing
   `next_fire_at` BEFORE launching (a crash after claim skips one tick — it
   never double-fires), then launches a real run per schedule with
   `source="scheduled"` and records `last_fired_at` + `last_run_id`.
3. **Tick is OIDC-gated.** Requests must carry a Google-signed ID token with
   the service's own URL as audience and a caller from this project's
   service accounts; misconfigured verification fails CLOSED (503 with a
   named env var, never an open endpoint).
4. **Cadence math:** hourly → +1h, daily → +24h from the scheduled time (not
   from the tick time — no drift accumulation). A new schedule's first
   `next_fire_at` is now (fires on the next tick).
5. **Monitoring page goes real:** the schedule form POSTs through the proxy
   and lists existing schedules; the "audits produced by this schedule"
   table shows real `source=scheduled` runs merged with labeled samples;
   live-API failure shows the standard visible notice.
6. **Infra:** `infra/scheduler-setup.sh` creates the single Cloud Scheduler
   job (every 15 min, OIDC via deploy SA, audience = agent URL).
7. Unit tests cover: claim-before-launch ordering, no double-fire on
   concurrent tick, cadence math, OIDC fail-closed, schedules API.

## File map

- `src/phoenix_audit_agent/storage/models.py` — `ScheduleRecord`
- `src/phoenix_audit_agent/storage/schedules.py` (new) — store + seam
- `src/phoenix_audit_agent/scheduler/__init__.py`, `scheduler/tick.py` (new)
  — due-claim + launch logic with injected store/launcher/clock
- `src/phoenix_audit_agent/api/schedules.py` (new) — CRUD + tick endpoint
  (+ OIDC verifier)
- `src/phoenix_audit_agent/main.py` — include router; extract `launch_run`
  helper shared by POST /run and the tick
- `apps/phoenix-audit-web/app/monitoring/page.tsx` + client component
- `infra/scheduler-setup.sh` (new)
- tests: `tests/unit/scheduler/`, `tests/unit/api/test_schedules_api.py`,
  fakes extension
