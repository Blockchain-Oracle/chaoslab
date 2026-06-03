# Story — Demo seed script (canonical Phoenix replay project)

**ID:** story-8.2-demo-seed-script
**Epic:** Epic 8 — README + Submission polish
**Depends on:** Should run AFTER all other epics (E1–E7) complete; technically the script itself only depends on E4 (Phoenix tool wrappers, ADR-005) being landable, but the `seed-data/canonical-run.json` payload it loads is captured from a real end-to-end run, so this story comes after Epic 7's `/attack` route has produced at least one real cascade-flip recording
**Estimate:** ~1.5h
**Status:** PENDING

**Tags:** `[docs, p0, submission]`

---

## User story

**As a** Stage-2 human judge clicking the demo URL during the 2026-06-22 → 2026-07-06 judging window when the live Cloud Run target agent might be cold-started, mid-deploy, or rate-limited by Gemini,
**I want to** hit `/replay` and see the canonical 25-attack pre-recorded run + the hardening recipe + the post-patch resilience curve, sourced from a Phoenix Cloud project (`chaoslab-replay`) seeded with real OpenInference traces,
**So that** even if the live attack path is degraded, the judge still sees the entire cascade-flip + PATCH-as-wedge story in <30s with real Phoenix span IDs they can click through to (per `docs/architecture.md` §"Demo" + ADR-004)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `scripts/seed_demo_data.py` — NEW — Python script (≤300 lines) that idempotently seeds Phoenix Cloud project `chaoslab-replay` with the canonical 25-attack run. CLI surface: `python scripts/seed_demo_data.py --project chaoslab-replay [--dry-run] [--force]`. Behavior: (1) reads `PHOENIX_API_KEY` + `PHOENIX_CLIENT_HEADERS` from env (loaded via pydantic-settings — same pattern as `chaoslab_agent.config`); (2) loads `seed-data/canonical-run.json` from disk; (3) instantiates `phoenix.client.AsyncClient()` (per ADR-005); (4) creates or no-ops the project (Phoenix Cloud project creation is idempotent via `projects.get_or_create()` — if absent, fall back to `tracer_provider` writing spans to `chaoslab-replay` causes project to materialize on first span ingest); (5) uses the OTLP HTTP exporter pointed at `https://app.phoenix.arize.com/v1/traces` with `PHOENIX_API_KEY` to push exactly 50 spans (25 baseline + 25 attack) from the JSON payload — each span carries the OpenInference attribute set captured from a real run (input/output/llm.\* attributes); (6) creates a Phoenix dataset named `canonical-attacks` with 25 examples via `client.datasets.create_dataset(name="canonical-attacks", examples=[...])`; (7) creates a follow-up `experiments` row via `client.experiments.create_experiment(dataset=..., name="canonical-replay-run")` referencing the seeded spans; (8) emits one structured log line per resource created (project, dataset, experiment, span count); (9) returns exit 0 on full success, exit 1 on any failure with full traceback. Uses `structlog` (per `docs/coding-standards.md`), never `print()`. Uses `typer` for the CLI surface. Imports `phoenix.client` lazily inside `main()` so `--help` doesn't require the SDK.
- `seed-data/canonical-run.json` — NEW — committed-to-repo JSON payload (≤400 lines) holding the canonical 25-attack run as a list of 50 OpenInference span objects (25 baseline-phase + 25 attack-phase). Each span has: `name`, `span_id`, `trace_id`, `parent_id`, `start_time`, `end_time`, `status_code`, `attributes` (the OpenInference `llm.*`, `tool.*`, `input.*`, `output.*` keys). Captured from one canonical real run during E7.11 dev — DO NOT hand-author span IDs; rerun the live `/attack` flow against the staged target-agent, export traces via `phoenix-cli traces export --project chaoslab-demo --output seed-data/canonical-run.json --format openinference-json`, then commit. Schema documented in a top-of-file `_schema` key referencing OpenInference v1.
- `seed-data/canonical-attacks-dataset.json` — NEW — 25 example rows for the Phoenix dataset (≤200 lines). Schema: `[{ "input": { "user_message": str, "fault_class": "malformed_tool_output" | "prompt_injection" | "context_poisoning" | "latency_spike" }, "output": { "expected_pass": bool, "expected_root_cause_cluster": str } }, ...]`. The `seed_demo_data.py` script loads this and passes it to `client.datasets.create_dataset(examples=...)`.
- `apps/chaoslab-web/app/(demo)/replay/page.tsx` — UPDATE — server component fetches `chaoslab-replay` project metadata from chaoslab-agent's `/replay-meta` endpoint and renders the canonical run. This story does NOT re-implement the page (story-7.10 owns it) — this story confirms the page's data source is the seeded `chaoslab-replay` project, not a local stub. One-line change: replace any `MOCK_REPLAY_PROJECT` constant or hardcoded fallback with `process.env.NEXT_PUBLIC_PHOENIX_REPLAY_PROJECT ?? "chaoslab-replay"`.
- `scripts/tests/test_seed_demo_data.py` — NEW — pytest tests (≤200 lines, ≥8 tests) for the seed script. Cases: (a) `--dry-run` exits 0 without hitting Phoenix; (b) malformed `canonical-run.json` raises `pydantic.ValidationError`; (c) missing `PHOENIX_API_KEY` raises a config error with a clear message; (d) `--force` overwrites existing dataset; (e) without `--force`, second invocation is idempotent (no duplicate spans); (f) span count assertion — 50 spans loaded from canonical JSON; (g) dataset example count = 25; (h) experiment is created and linked to the dataset. Uses `respx` to mock Phoenix HTTP endpoints (real Phoenix Cloud not hit in unit tests). One additional `@pytest.mark.online` test in `scripts/tests/test_seed_demo_data_online.py` (≤80 lines) hits real Phoenix Cloud — gated behind `PHOENIX_API_KEY` env presence; skipped in default CI.
- `Makefile` — UPDATE — adds `seed-demo` target that runs `uv run python scripts/seed_demo_data.py --project chaoslab-replay`. One-line addition to the existing Makefile.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the seed-data/ directory and seed_demo_data.py exist
When `test -f scripts/seed_demo_data.py && test -f seed-data/canonical-run.json && test -f seed-data/canonical-attacks-dataset.json` runs
Then exit 0

Given seed-data/canonical-run.json exists
When `python -c "import json; d=json.load(open('seed-data/canonical-run.json')); assert len(d['spans']) >= 50, f'span count {len(d[\"spans\"])} < 50'"` runs
Then exit 0 (canonical payload has 50+ spans — gate from story brief)

Given seed-data/canonical-attacks-dataset.json exists
When `python -c "import json; d=json.load(open('seed-data/canonical-attacks-dataset.json')); assert len(d) == 25"` runs
Then exit 0 (25 dataset examples — gate from story brief)

Given PHOENIX_API_KEY is unset in env
When `python scripts/seed_demo_data.py --project chaoslab-replay` runs
Then exit code is 1
And stderr contains "PHOENIX_API_KEY" (clear config error message)

Given PHOENIX_API_KEY is set AND seed-data/canonical-run.json exists
When `python scripts/seed_demo_data.py --project chaoslab-replay --dry-run` runs
Then exit code is 0 (dry-run path works without hitting Phoenix)
And stdout contains "would create project: chaoslab-replay"
And stdout contains "would push 50 spans"
And stdout contains "would create dataset: canonical-attacks (25 examples)"

Given PHOENIX_API_KEY is set in env AND seed-data/canonical-run.json exists
When `python scripts/seed_demo_data.py --project chaoslab-replay` runs against Phoenix Cloud
Then exit code is 0 (full gate from story brief)
And Phoenix Cloud project "chaoslab-replay" exists (verifiable via `curl -H "Authorization: Bearer $PHOENIX_API_KEY" https://app.phoenix.arize.com/v1/projects/chaoslab-replay`)
And `curl ... /v1/projects/chaoslab-replay/spans | jq '.data | length'` returns ≥ 50
And `curl ... /v1/datasets?name=canonical-attacks | jq '.data[0].example_count'` returns 25

Given the script ran once successfully
When the script runs a second time without --force
Then exit code is 0 (idempotent)
And Phoenix project span count is still 50 (no duplicates)

Given the unit test file exists
When `uv run pytest scripts/tests/test_seed_demo_data.py -v` runs
Then exit code is 0
And output contains "8 passed" or more

Given the Makefile was updated
When `grep -E "^seed-demo:" Makefile` runs
Then exit 0
And `make -n seed-demo` shows the python invocation in dry-run output

Given the script file
When `wc -l scripts/seed_demo_data.py` runs
Then the line count is ≤ 400 (ADR-010 compliance)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# File scaffolding
test -f scripts/seed_demo_data.py
test -f seed-data/canonical-run.json
test -f seed-data/canonical-attacks-dataset.json
test -f scripts/tests/test_seed_demo_data.py

# Canonical payload shape
python3 -c "import json; d=json.load(open('seed-data/canonical-run.json')); assert len(d['spans']) >= 50"
python3 -c "import json; d=json.load(open('seed-data/canonical-attacks-dataset.json')); assert len(d) == 25"

# CLI surface
uv run python scripts/seed_demo_data.py --help | grep -q "project"
uv run python scripts/seed_demo_data.py --help | grep -q "dry-run"

# Dry-run works without secrets
PHOENIX_API_KEY=fake-for-dry-run uv run python scripts/seed_demo_data.py \
  --project chaoslab-replay --dry-run | grep -q "would push 50 spans"

# Missing API key fails clearly
unset PHOENIX_API_KEY
! uv run python scripts/seed_demo_data.py --project chaoslab-replay 2>&1 | tee /tmp/seed-err.txt
grep -q "PHOENIX_API_KEY" /tmp/seed-err.txt

# Unit tests (offline, respx-mocked)
uv run pytest scripts/tests/test_seed_demo_data.py -v
[ "$(uv run pytest scripts/tests/test_seed_demo_data.py --collect-only -q | grep -c '::test_')" -ge 8 ]

# Online integration test ONLY runs if real key present
if [ -n "$PHOENIX_API_KEY_REAL" ]; then
  PHOENIX_API_KEY="$PHOENIX_API_KEY_REAL" \
    uv run pytest scripts/tests/test_seed_demo_data_online.py -v -m online
fi

# Makefile target
grep -E "^seed-demo:" Makefile

# Line count
[ "$(wc -l < scripts/seed_demo_data.py)" -le 400 ]
python3 scripts/check_max_lines.py --strict

echo "story-8.2 verification: PASS"
```

---

## Notes for coding agent

- Phoenix Cloud project creation is implicit — there's no `POST /projects` endpoint exposed publicly. Project materializes the first time a span lands with a `project_name` resource attribute matching `chaoslab-replay`. The script sets this via `os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "openinference.project.name=chaoslab-replay"` BEFORE importing `phoenix.otel`, then calls `phoenix.otel.register(project_name="chaoslab-replay")`.
- The OTLP HTTP exporter endpoint is `https://app.phoenix.arize.com/v1/traces` — confirmed in `architecture/02-phoenix-deep-dive.md` and `arize-phoenix-otel` docs. Auth header: `Authorization: Bearer ${PHOENIX_API_KEY}`.
- `phoenix.client.Client.datasets.create_dataset(name, examples)` is the SDK call per ADR-005. If the dataset already exists, the SDK raises `phoenix.exceptions.ResourceAlreadyExists` — catch this and either skip (default) or call `delete_dataset` then recreate (under `--force`).
- The `canonical-run.json` payload is captured from a REAL run, not hand-authored. The flow: (1) deploy chaoslab-agent + target-agent to staging; (2) run `/attack` once with the canonical seed (matrix completes with ~15 fails, ~10 passes, then re-attack ends ~22 passes, ~3 fails); (3) export traces via `phoenix-cli traces export`; (4) commit the JSON. Hand-authoring would violate §14 ("no fakes in hot path") and the dataset wouldn't have valid llm.\* attributes.
- DO NOT vendor large binary trace payloads. The JSON file IS the canonical artifact — keep it under 400 lines by pretty-printing with `indent=2` and accepting that 50 spans × ~6 lines each ≈ 300 lines.
- The `--dry-run` flag must work WITHOUT a real Phoenix connection — it's how CI verifies the script logic. Use `respx` to mock httpx calls in the test suite; the script itself should branch on `if dry_run: log.info(...); return` before any network call.
- The online test (`test_seed_demo_data_online.py`) is marked `@pytest.mark.online` per `docs/coding-standards.md` pytest markers. CI does not run online tests by default (per `.github/workflows/pr-checks.yaml`). Abu runs it manually before submission.
- Idempotency matters: the orchestrator may re-run this script across deploys. Use Phoenix's `dataset_version` field if two consecutive runs of the same dataset name need to be distinguishable, OR add a content-hash check that skips if the existing dataset already has the same 25 examples.
- This script is invoked by Abu as part of the Day 8 submission ritual (manually, before recording the demo video). It is NOT wired into CI auto-deploy because seeding Phoenix Cloud is rate-limited and we don't want every `staging-deploy.yaml` run hammering it.
