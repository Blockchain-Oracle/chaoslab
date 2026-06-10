# Story 9.1 — Firestore persistence + runs/agents API

**Epic:** Epic 9 — product surfaces go real
**Status:** COMPLETE (PR #92, 2026-06-10)
**Depends on:** PR #91 (span-fetch fix), story-5.8 (real pipeline), story-6.7 (signed report)

## Why

Every product surface except the live chamber renders static fixtures because the
backend has no memory: runs live in an in-process dict and vanish on completion
sweep / restart, and the agent registry is a hardcoded seed. The audit registry,
target-agent pages, monitoring and report download in the designer's prototype
all presuppose a persistent record of runs. Firestore (native mode, free tier,
async Python client, zero infra) is the store; the live SSE path stays exactly
as-is (in-memory queues), with persistence as a write-through.

Decisions locked with Abu 2026-06-10: dashboard shows seeded sample data clearly
labeled + real persisted runs; records carry `org_id`/`owner_uid` fields now so
auth scoping (story-9.4) is a filter, not a migration.

## BDD acceptance criteria

1. **POST /run persists a run record.** Given a `POST /run`, a Firestore doc
   `runs/{run_id}` exists with `target_url`, `agent_id`, `source`
   (`manual` default, `scheduled` accepted), `created_at`, `phase="queued"`,
   `org_id="default"`, `owner_uid=None`.
2. **Run completion finalizes the record.** When `drive_audit` completes, the
   record carries `phase`, `passed/failed/errored/transport_failed`,
   `recipe_id`, `report_available`, `finished_at`, `duration_sec`.
3. **GET /runs lists newest-first** with optional `agent_id` / `source` filters;
   each row carries the fields the audit-registry UI renders.
4. **GET /runs/{run_id}** returns the full record with FRESH v4 signed URLs for
   report.pdf / report.json / signature.json (and recipe markdown when present),
   re-signed at read time from the deterministic object paths
   (`reports/{run_id}/...`, `{recipe_id}.md`) — stored URLs would expire.
5. **Agents registry is real.** `POST /agents` registers (id, name, url,
   framework, tier); `GET /agents` lists; `GET /agents/{id}` fetches; the
   `demo-target` seed exists on first read.
6. **Persistence failure never kills an audit.** If Firestore writes fail, the
   run proceeds; the failure is logged at CRITICAL with the run id (the signed
   artifact set is the durable evidence; history is an index). The `complete`
   SSE frame carries `persistence_failed: true` so the UI/registry can disclose.
7. **Unit tests use the store seam** (in-memory fake of the same interface);
   one `@pytest.mark.online` test exercises real Firestore via ADC (or the
   emulator when `FIRESTORE_EMULATOR_HOST` is set).

## File modification map

- `src/phoenix_audit_agent/storage/__init__.py` (new)
- `src/phoenix_audit_agent/storage/models.py` (new) — `RunRecord`, `AgentRecord`
- `src/phoenix_audit_agent/storage/firestore_client.py` (new) — lazy AsyncClient
- `src/phoenix_audit_agent/storage/runs.py` (new) — `RunStore`
- `src/phoenix_audit_agent/storage/agents.py` (new) — `AgentStore`
- `src/phoenix_audit_agent/api/__init__.py` (new)
- `src/phoenix_audit_agent/api/runs.py` (new) — `GET /runs`, `GET /runs/{id}`
- `src/phoenix_audit_agent/api/agents.py` (new) — `POST/GET /agents`,
  `GET /agents/{id}` (moves the endpoint out of main.py)
- `src/phoenix_audit_agent/main.py` — include routers; write-through on
  `POST /run`; `RunRequest.source`
- `src/phoenix_audit_agent/audit_runner.py` — `persist_run_completion` seam
  invoked BEFORE the `complete` frame (so the frame can disclose `persistence_failed`)
- `infra/workload-identity-federation.sh` — document `roles/datastore.user`
  grant (already applied to the live project 2026-06-10)
- `tests/unit/storage/`, `tests/unit/api/` (new), `tests/unit/test_main.py`,
  `tests/unit/test_audit_runner.py`

## Notes

- Bucket/object naming is already deterministic (`reports/{run_id}/{name}`,
  `{recipe_id}.md` in `GCS_RECIPES_BUCKET`) — re-signing at read time reuses
  `ReportEmitter`/`MarkdownEmitter` upload conventions without storing URLs.
- Firestore database `(default)` created in us-central1 (native) and
  `roles/datastore.user` granted to `chaoslab-runtime` on 2026-06-10.
- Cloud Run multi-replica note in main.py still applies to SSE (`/stream`);
  history reads are replica-safe once Firestore-backed.
