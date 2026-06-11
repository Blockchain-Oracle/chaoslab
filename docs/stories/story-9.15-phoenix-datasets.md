# story-9.15 — phoenix-datasets: name, persist, list, run, download

**Epic:** 9 · **Depends on:** story-9.1 (firestore-persistence — the `Datasets` collection sits next to `Runs` / `Agents`), story-9.12 (user-profile — `owner_uid` is the tenant key), story-9.7 (phoenix-sessions — the `experiment_name` plumbing is the deep-link spine into Phoenix's Experiments tab).
**Source:** Wave B of the unified-finish plan (`~/.claude/plans/there-i-want-you-toasty-ember.md`, §B2). Surface S brief in `docs/assets.md` (full domain context + every state the designer needs to express).

## Why

Today the audit's probe battery is sampled fresh every run — there's no "run the SAME eight probes against this same agent tomorrow" path. A compliance officer cannot show a regulator the before-and-after on a fix because nothing is locked. And Maya's organization has its own corpus of cases ("things our agents must refuse" pulled from prior incidents, internal red-team exercises, industry mappings) that the product cannot run. The signed report's `Dataset:` line on the cover is stubbed with the framework name, which is dishonest.

Phoenix Audit is built on top of Arize Phoenix, whose **Datasets** + **Experiments** features are exactly the primitive we need: named, persisted, immutable collections of test cases that experiments run against and that the UI can deep-link to. Story 9.15 wires three kinds of datasets in:

1. **Battery** — ships with the product, read-only, every user sees the same rows. 3 sets at launch: `harmbench-v1-sample`, `owasp-llm-top10`, `mitre-atlas-min`.
2. **Regression** — auto-populated per registered target agent. Every audit run upserts its failing-probe rows into `regression-<agent_slug>` (most-recent 200). The "Re-audit with this set" button replays them.
3. **Uploaded** — Maya's own JSONL or CSV, named, owner-scoped, validated server-side.

The signed report cover finally carries a real `Dataset:` line and `source_url`; the experiment block deep-links into Phoenix's Experiments tab via the `phoenix-audit-{run_id}` experiment_name from story 9.7.

## BDD acceptance criteria

### Backend — `/datasets` API + persistence

- **Given** an authenticated user, **when** `GET /datasets`, **then** the response lists (a) the 3 battery datasets (visible to everyone), (b) every uploaded dataset where `owner_uid == user.uid`, (c) every regression dataset whose agent has `owner_uid == user.uid`. Each row carries `dataset_id`, `name`, `kind`, `row_count`, `created_at`, `updated_at`, `source_url` (nullable), and `agent_id` (only for regression).
- **Given** an authenticated user POSTing `{"name": "...", "format": "jsonl|csv", "body": "<raw bytes as base64>", "fault_classes": ["prompt_injection", ...]}` to `/datasets`, **when** the body parses and every row carries `case_id` + `fault_class` (one of the 4 known) + `prompt` + `expected` + `source`, **then** the dataset persists as `kind="uploaded"` with `owner_uid=user.uid` and a generated `ds_<hex>` `dataset_id`. Returns 201 with the new dataset's metadata.
- **Given** an upload whose body fails parsing (malformed JSON / unparseable CSV) or whose individual row(s) fail validation (missing required field, unknown `fault_class` value), **then** 422 with a body listing `row_errors: [{"row": N, "reason": "..."}]` AND a `parse_error: "..."` field when the whole file is unparseable. Row-level errors and parse errors are mutually exclusive in the response.
- **Given** `GET /datasets/{dataset_id}`, **when** the user owns or can see the dataset (battery rule above), **then** the response includes the metadata + the full `items: [DatasetItem, ...]` array. Forbidden datasets return 404 (NOT 403 — never leak whether a dataset exists).
- **Given** `DELETE /datasets/{dataset_id}`, **then** uploaded datasets owned by the user delete cleanly and the response is 204. Battery datasets respond 409 with `"reason": "battery datasets are read-only"`. Regression datasets respond 409 with `"reason": "regression datasets are managed by the system — delete the underlying agent to remove"`. Finished audits that referenced the deleted dataset keep their signed PDFs intact (the run record's `dataset_name` field stays populated as a string; the linked dataset_id may dangle).
- **Given** an audit completes with one or more failing probes against a target agent owned by `uid`, **then** those failing rows upsert into the agent's regression dataset (`regression-<agent_slug>`). The upsert is keyed on `case_id`; existing rows for the same `case_id` are overwritten with the most-recent failure. The dataset is capped at 200 rows — when over cap, oldest-by-`created_at` rows are dropped to make room.
- Route-auth contract: `GET /datasets`, `GET /datasets/{id}`, `POST /datasets`, `DELETE /datasets/{id}` ALL carry `require_user` (pinned by the existing auth-scoping registry test automatically).

### Backend — run pipeline integration

- **Given** a `POST /run` request with `dataset_name: "harmbench-v1-sample"` (or any `dataset_id` slug), **when** the dataset is visible to the requester, **then** the Injector pulls the dataset items + the existing synthetic probe battery and runs BOTH. SSE `test_started` / `test_completed` frames include an `origin` field of `"battery" | "dataset:<id>"` so the chamber UI can label each probe row.
- **Given** a `POST /run` request with a `dataset_name` the user cannot see, **then** 422 with `"reason": "dataset not found or not accessible"`. Never 403 (same leak-prevention rule).
- **Given** a finished audit run that used a dataset, **then** the signed report's cover renders `Dataset: <name>` (and `source_url` when present). The report's JSON artifact records `dataset_id`, `dataset_name`, `dataset_kind`, `dataset_source_url` under the existing `experiment` block. The PDF cover line is the same string as the JSON's `dataset_name` — no drift.
- **Given** a finished audit run that DID NOT specify a dataset, **then** the cover line reads `Dataset: synthetic battery (no operator dataset)` — explicit, never blank.

### Backend — battery seed + regression upsert

- **Given** `scripts/seed_datasets.py` runs (idempotent), **then** the 3 battery datasets persist to Firestore at well-known IDs `harmbench-v1-sample`, `owasp-llm-top10`, `mitre-atlas-min`. The script reads row content from versioned JSON files committed at `apps/phoenix-audit-agent/data/datasets/<slug>.json` so a code review sees what changes when the corpus changes.
- **Given** the same script runs a second time with no changes, **then** Firestore writes are no-ops (compare-and-write — the script computes the SHA-256 of the items + metadata and skips if the stored hash matches).
- **Given** a regression upsert lands rows that bring the total over 200, **then** the oldest-by-`created_at` rows are deleted from Firestore in the same transaction as the new insert (single transaction so a partial failure leaves no gap).

### Web — `/datasets` page + wizard picker + agent re-audit CTA

- **Given** an authenticated user lands on `/datasets`, **then** the page renders three labeled sections (battery / regression / uploaded) in that reading order. The battery section always shows the 3 known datasets. The regression and uploaded sections show "no rows yet" affordances when empty.
- **Given** a user lands on `/datasets/<dataset_id>` for a visible dataset, **then** the detail header shows name + kind chip + row_count + last-updated + source_url-when-applicable + CTAs (Use in new audit, Download JSON, Download CSV, Delete-when-uploaded), and the rows table renders all items paginated 50/page client-side.
- **Given** a user picks a `.jsonl` / `.csv` file in the upload card, **then** the page shows in-flight state while the POST is in progress, displays an inline row-by-row error panel on 422 (row errors NOT a toast — persistent until retried), or inserts the new dataset row optimistically on 201.
- **Given** a deep-link `/new?dataset=<id>` opens the wizard, **then** the dataset-picker accordion (§3b) auto-expands and the dataset is preselected. The run-summary line under the button reads "audit will run 8 standard probes + N rows from `<name>`."
- **Given** an agent has at least one finished audit (so a regression set exists), **then** Surface F (agent detail) shows a "Run regression on `regression-<slug>` (N rows)" button alongside the existing "Run audit now" affordance. The button links to `/new?dataset=<regression_id>&agent=<agent_id>`.
- Proxy allowlist: web's `/api/agent/[...path]/route.ts` allowlist gains `/^datasets$/` and `/^datasets\/[a-z0-9_-]+$/`. Auth-scoping registry test on the backend covers the new routes automatically (every route carries `require_user`).

## File map

### Backend (`apps/phoenix-audit-agent/`)

- `src/phoenix_audit_agent/storage/models.py` — `+Dataset`, `+DatasetItem`, `+DatasetKind` Literal, `+UploadValidationError`.
- `src/phoenix_audit_agent/storage/datasets.py` — new, Protocol + Firestore + in-memory seam (mirrors `storage/runs.py`). Operations: `list_visible(uid)`, `get(dataset_id, uid)`, `upsert_uploaded(dataset, uid)`, `delete_uploaded(dataset_id, uid)`, `upsert_regression_rows(agent_id, rows)`.
- `src/phoenix_audit_agent/api/datasets.py` — new router. `GET /datasets`, `GET /datasets/{id}`, `POST /datasets`, `DELETE /datasets/{id}`. All carry `require_user`.
- `src/phoenix_audit_agent/main.py` — include the new router; extend `RunRequest` with `dataset_name: str | None = None` (validates that the dataset is visible to the user inside `launch_run`).
- `src/phoenix_audit_agent/audit_runner.py` — thread `dataset_name` into `drive_audit`; the Injector reads dataset items at attack-construction time and emits per-probe `origin` on the SSE frames.
- `src/phoenix_audit_agent/reporter/service.py` — populate `dataset_name` / `dataset_source_url` in `ReportData`; the cover-page renderer reads them.
- `src/phoenix_audit_agent/storage/datasets_battery.py` — new, holds the canonical battery dataset metadata + the loader that reads `data/datasets/<slug>.json`.
- `data/datasets/harmbench-v1-sample.json`, `owasp-llm-top10.json`, `mitre-atlas-min.json` — versioned row content committed to the repo (small files, <30 KB each; no binary).
- `scripts/seed_datasets.py` — new, idempotent battery seed.
- `tests/unit/api/test_datasets_api.py`, `tests/unit/storage/test_datasets_store.py`, `tests/unit/storage/fakes.py` (+`InMemoryDatasetStore`), `tests/unit/test_audit_runner_dataset.py`, `tests/unit/test_regression_upsert.py`, `tests/unit/test_datasets_battery_loader.py`.

### Web (`apps/phoenix-audit-web/`)

- `app/datasets/page.tsx` — server component, fetches the listing + renders the three sections.
- `app/datasets/[datasetId]/page.tsx` — detail page, server-side fetch.
- `app/datasets/datasets-client.tsx` — listing client (upload card + inline error panel + optimistic insert).
- `app/datasets/[datasetId]/detail-client.tsx` — detail client (rows table pagination + delete confirm modal + download CTAs).
- `app/api/agent/[...path]/route.ts` — proxy allowlist `+/^datasets$/`, `+/^datasets\/[a-z0-9_-]+$/`.
- `app/new/page.tsx` (+ new-audit-form client) — §3b dataset picker accordion, deep-link auto-expansion, run-summary line.
- `app/agents/[agentId]/page.tsx` — "Run regression on `regression-<slug>` (N rows)" CTA when the agent has at least one finished audit.
- `lib/api.ts` — `fetchDatasets`, `fetchDataset`, `uploadDataset`, `deleteDataset` typed fetchers.
- Tests: `app/datasets/__tests__/*`, proxy-allowlist regression, picker behavior, deep-link auto-expansion, optimistic-insert + error-panel state machine.

## Notes

- **Validation invariants on upload**: the request body field `format` is `Literal["jsonl", "csv"]`; the `body` field is base64-encoded raw bytes (handles CRLF/BOM/UTF-8-with-BOM uniformly without query-string mangling). Server-side validates: (a) each row's `fault_class` is in `{prompt_injection, context_poisoning, malformed_tool_output, latency_spike}`; (b) `case_id` is unique within the dataset; (c) `prompt` is non-empty and ≤ 10_000 chars; (d) `expected` is non-empty; (e) `source` is non-empty. Empty file → 422 with `parse_error: "empty file"`. Row count cap: 500 rows per upload (regression cap is 200; uploaded cap is 500 because operators may bring larger corpora).
- **Three-kinds invariant**: a dataset's `kind` is set at creation and immutable. The Pydantic model uses a `Discriminator` so a typo in the `kind` literal is a parse-time error, never a silent drop. `kind` and `owner_uid` are linked by validator: battery ⇒ `owner_uid is None`, uploaded ⇒ `owner_uid is not None`, regression ⇒ `owner_uid` matches the agent's `owner_uid`.
- **The `Dataset:` cover line is the canonical name string**: when the dataset is later deleted, the run record's `dataset_name` (a string) stays populated — the signed PDF is evidence, the deleted-dataset dangle is acceptable. The dataset's `source_url` is captured into the run record at run finalize too, so the cover renders correctly even after deletion.
- **Battery datasets ship as JSON files** committed at `apps/phoenix-audit-agent/data/datasets/`. The seed script's idempotency hash is computed over (items + name + source_url) — a content change in the JSON file triggers a re-seed; a metadata-only change does too. Production deployment runs the seed script as part of the staging-deploy workflow's post-deploy step.
- **Phoenix Datasets API integration is OUT of scope for this story**: we persist in our own Firestore. The "View in Phoenix ↗" link on battery detail pages points to a configured Phoenix dataset URL (`PHOENIX_DATASET_BASE_URL` env var + the dataset's slug) and we trust Phoenix's UI to render the items — this avoids the partial-MCP gotcha (Phoenix MCP exposes `list-datasets` but not `create-dataset`, see ADR-005). A future story can mirror battery datasets into Phoenix Datasets if the deep-link adoption matters; for now the deep-link is one-way and best-effort.
- **No file >400 significant lines** in source after this story — `api/datasets.py` should land around 200, `storage/datasets.py` around 250. If the upload validation grows large, extract a `storage/dataset_validation.py` sibling.
- **CSV parser:** use Python's stdlib `csv.DictReader` (no third-party dep). JSONL parser is `json.loads` per non-empty line. Reject CSVs whose header row doesn't include all required columns.
- **TDD seam**: `audit_runner.dataset_loader` is a module attribute so tests monkeypatch the dataset-fetch path with fakes — same pattern as `Injector`, `apply_rubric`, etc.

## Bundled scope — S9.14 onboarding reconciliation (web only)

Per Abu (2026-06-11): while this story is already in the web codebase for the `/datasets` page + wizard picker + agent CTA, **also port the designer's onboarding redesign** from `/Users/abu/Downloads/Phoenix Audit(2)/js/onboarding.jsx` (and `onboarding-states.jsx` for state variants). The S9.14 reducer + server-gate + lib/onboarding state machine stay unchanged — only the surface components are replaced. Doing both in one PR is more efficient than splintering: the same `pnpm typecheck` + `pnpm test` + visual capture pass covers everything.

### What changes (web only — no backend touch)

- `apps/phoenix-audit-web/components/onboarding/` — replace the 5 placeholder step components with the designer's deliveries. Key components ported:
  - **`OnboardingShell`** — new two-column layout (`onb-grid`). Left column: `Docket` + `CoverPreview` aside. Right column: stepper body + foot.
  - **`Docket`** — TOC of 4 questions with the _answered value_ next to each row (e.g. "EU AI Act · dflt", "first audit"). Replaces the simple step strip. Supports jump-back to any visited step.
  - **`CoverPreview`** — live miniature of Maya's signed-report cover that fills in as she answers (org name + framework articles). The seal mark spins. Persistent context across all steps.
  - **`AuditLoop`** — Welcome step SVG illustration (center diamond "YOUR AGENT", orbiting Phoenix glyph, 4 stations: adversarial battery / judge / root-cause cluster / sign). Answers asset request O-2.
  - **`FrameworkRows`** — replaces the placeholder framework picker. Each row shows the framework name + sub + "cited on your covers" indicator with the actual articles. EU AI Act row carries a DEFAULT chip.
  - **`GitlabPromise`** — replaces the placeholder GitLab teaser. Three numbered commitments (Your OAuth not ours / Review-first / Additive only) + a "specimen MR" card showing a sample merge-request preview under a "Not live yet" stamp.
  - **`DestCards`** — replaces the placeholder CTA cards. Two cards (Run your first audit / Browse sample audits) with custom SVG marks (`DestMarkProbe`, `DestMarkSamples`) + a "FILING YOUR PROFILE…" busy state on the chosen card + an inline error state when the PATCH fails.
  - **`OnbSubmitError`** — replaces the placeholder error notice. Inline `AuthNotice` tied to the destination cards (NOT a toast): "That didn't save — you're not onboarded yet. Nothing you answered was lost: pick a destination again and we'll send the same request."
- `apps/phoenix-audit-web/app/onboarding/page.tsx` — server gate unchanged; `OnboardingShell` renders the same client component.
- `apps/phoenix-audit-web/components/onboarding/onboarding-client.tsx` — reducer + `runFinish` lib unchanged. Only the JSX tree swap (new `Docket` + `CoverPreview` aside + step renderers).
- Per-step skip wording is meaningful copy: "Skip — keep EU AI Act" (step 2), "Skip — set it in Settings later" (step 1). Generic "Skip" goes away.
- Welcome step gains an "In a hurry? Skip to the finish" affordance that jumps directly to step 4.
- **Tests:** existing S9.14 reducer tests pass unchanged (state-machine contract preserved). Add 3 visual snapshot tests against the new components (`Docket` populated states, `CoverPreview` filling-in states, `DestCards` busy + error states).
- **CSS:** the designer drop is plain CSS in `styles.css`. Lift the onboarding-specific classes (`onb-grid`, `onb-rail`, `onb-toc`, `onb-cover`, `audit-loop`, `fw-row`, `opt-card`, `onb-dest-grid`, etc.) into `apps/phoenix-audit-web/app/onboarding/onboarding.css` (or whatever the existing styling convention is). No Tailwind rewrite — match the designer's CSS verbatim so the look survives the port.

### Behavior preserved (do not change)

- The reducer state (`step`, `org`, `framework`, `skipped`, `submitState`) and the `runFinish` action both stay byte-identical to S9.14.
- The PATCH is still sent ONCE on Finish. Per-step skip still just marks the field as omitted.
- The server gate redirect (`profile.onboarded === false` ⇒ `/onboarding`) is unchanged.
- The wizard still opens on Welcome with no resume-where-you-left-off behavior.
- The same `pnpm test --filter phoenix-audit-web` suite stays green.

### Why bundle

Splintering into a separate PR would require two web-side typecheck cycles, two `pnpm test` runs, two visual capture passes, and two reviews. Doing both in one PR — datasets + onboarding port — is one of each. Story-9.14's reducer + server gate are stable; the swap is mechanical (port JSX + CSS, keep state machine).
