# story-9.15 — phoenix-datasets: name, persist, list, run, download

**Epic:** 9 · **Depends on:** story-9.1 (firestore-persistence — the `datasets` index collection sits next to `runs` / `agents`), story-9.12 (user-profile — `owner_uid` is the tenant key), story-9.7 (phoenix-sessions — the `experiment_name` plumbing is the deep-link spine into Phoenix's Experiments tab).
**Source:** Wave B of the unified-finish plan (`~/.claude/plans/there-i-want-you-toasty-ember.md`, §B2). Surface S brief in `docs/assets.md` (full domain context + every state the designer needs to express).
**Spec history:** v1 (committed `715a872`) treated datasets as Firestore-native with our own item shape. **v2 (this file)** grounds in the real `phoenix.client.AsyncClient.datasets` SDK after the 2026-06-11 reality check: Phoenix is the row store; Firestore holds a thin lookup index. See "What v2 changes" at the bottom for the full delta.

## Why

Today the audit's probe battery is sampled fresh every run — there's no "run the SAME eight probes against this same agent tomorrow" path. A compliance officer cannot show a regulator the before-and-after on a fix because nothing is locked. And Maya's organization has its own corpus of cases ("things our agents must refuse" pulled from prior incidents, internal red-team exercises, industry mappings) that the product cannot run. The signed report's `Dataset:` line on the cover is stubbed with the framework name, which is dishonest.

Phoenix Audit is built on top of Arize Phoenix, whose **Datasets** + **Experiments** features are exactly the primitive we need: named, persisted, versioned collections of test cases that experiments run against. Story 9.15 wires three kinds of datasets in:

1. **Battery** — ships with the product, read-only, every user sees the same rows. 3 sets at launch: `harmbench-v1-sample`, `owasp-llm-top10`, `mitre-atlas-min`.
2. **Regression** — auto-populated per registered target agent. Every audit run upserts its failing-probe rows into `regression-<agent_slug>` (most-recent 200, deduped on `case_id`). The "Re-audit with this set" button replays them.
3. **Uploaded** — Maya's own JSONL or CSV, named, owner-scoped, validated server-side.

The signed report cover finally carries a real `Dataset:` line + `source_url`; the experiment block deep-links into Phoenix's Experiments tab via the `phoenix-audit-{run_id}` experiment_name from story 9.7.

## Architecture decision — Phoenix is the row store

After grounding in the actual SDK shape (`phoenix.client.resources.datasets.AsyncDatasets` and `phoenix.client.__generated__.v1.Dataset` / `DatasetExample`):

- **Phoenix Datasets** holds the actual examples. Every dataset is a real Phoenix `Dataset` with a real `phoenix_dataset_id` (Phoenix-generated). Reads of examples (the rows table on `/datasets/<id>`) hit Phoenix via `AsyncClient.datasets.get_dataset(dataset=phoenix_dataset_id)`. Writes (`create_dataset`, `add_examples_to_dataset`) push to Phoenix. "View in Phoenix ↗" links are real evidence.
- **Firestore `datasets/{id}`** holds a thin lookup index for the three things Phoenix doesn't carry: ownership (`owner_uid`), kind (`battery | regression | uploaded`), the slug-to-phoenix-id mapping, and `agent_id` for regression sets. The Firestore document is ~10 fields; the examples are NOT duplicated here.
- This is true to the Arize-track theme and to the recovered plan's "View in Phoenix ↗" + "experiment compare deep-link" asks.

### Example wire shape

A `DatasetExample` on Phoenix is `{id, node_id, input, output, metadata}` where `input/output/metadata` are arbitrary `Mapping[str, Any]`. We slice our flat row shape onto that:

```text
input    = { case_id, prompt, fault_class }
output   = { expected }
metadata = { source, severity, notes }
```

The slicing is handled by Phoenix's own `create_dataset(input_keys=[...], output_keys=[...], metadata_keys=[...])` — we pass a flat row mapping and tell Phoenix which keys belong in which bucket. This is the documented and tested SDK path; we do NOT pre-slice in our code.

### Slug ↔ phoenix_dataset_id

The product talks to operators in slugs (`harmbench-v1-sample`, `regression-meridian-prior-auth`, `ds_a1b2c3d4`). Phoenix talks back in Phoenix-generated IDs (`RGF0YXNldDox` style base64). The Firestore index is the only authoritative slug → phoenix_id mapping.

## BDD acceptance criteria

### Backend — `/datasets` API + persistence

- **Given** an authenticated user, **when** `GET /datasets`, **then** the response lists every dataset visible to them — every battery dataset (visible to all), every uploaded dataset where `owner_uid == user.uid`, and every regression dataset whose agent has `owner_uid == user.uid`. Each row carries `dataset_id` (the slug), `name`, `kind`, `row_count`, `created_at`, `updated_at`, `source_url` (nullable), `agent_id` (only on regression). Phoenix-side IDs are NOT exposed on the API.
- **Given** an authenticated user POSTing `{"name": "...", "format": "jsonl|csv", "body": "<raw bytes base64-encoded>"}` to `/datasets`, **when** the body parses and every row carries `case_id` + `fault_class` (one of the 4 known) + `prompt` + `expected` + `source`, **then** the upload (a) creates a Phoenix dataset via `client.datasets.create_dataset(name=..., examples=rows, input_keys=["case_id","prompt","fault_class"], output_keys=["expected"], metadata_keys=["source","severity","notes"])`, (b) writes the Firestore index row with the returned `phoenix_dataset_id`, `kind="uploaded"`, `owner_uid=user.uid`, and a generated `ds_<hex>` slug. Returns 201 with the index metadata.
- **Given** an upload whose body fails parsing (malformed JSON / unparseable CSV) or whose individual row(s) fail validation (missing required field, unknown `fault_class` value, duplicate `case_id` within the file), **then** 422 with a body listing `row_errors: [{"row": N, "reason": "..."}]` AND a `parse_error: "..."` field when the whole file is unparseable. Row-level errors and parse errors are mutually exclusive in the response. The Phoenix-side dataset is NOT created on validation failure.
- **Given** `GET /datasets/{dataset_id}` (slug), **when** the user can see the dataset, **then** the response includes the index metadata + the `examples: [...]` array fetched from Phoenix via `client.datasets.get_dataset(dataset=phoenix_dataset_id)`. The `input/output/metadata` mappings on each example are flattened back into `{case_id, prompt, fault_class, expected, source, severity, notes}` for the wire response. Forbidden datasets return 404 (NOT 403 — never leak whether a dataset exists).
- **Given** `GET /datasets/{dataset_id}` for a Phoenix outage (HTTP 5xx / timeout from Phoenix), **then** 503 with `"reason": "dataset rows temporarily unavailable"` AND the index metadata in the body — so the page can still render the header + dataset name + a "rows temporarily unavailable" banner instead of a hard error.
- **Given** `DELETE /datasets/{dataset_id}`, **then** uploaded datasets owned by the user are removed from Phoenix AND the Firestore index in that order — Phoenix delete is best-effort (log on failure but proceed) because the Firestore-index delete is what hides the dataset from the user. The response is 204. Battery datasets respond 409 (`"reason": "battery datasets are read-only"`). Regression datasets respond 409 (`"reason": "regression datasets are managed by the system — delete the underlying agent to remove"`). Finished audits that referenced the deleted dataset keep their signed PDFs intact (the `RunRecord.dataset_name` field is a string snapshot; the linked slug may dangle).
- **Given** an audit completes with one or more failing probes against a target agent owned by `uid`, **then** those failing rows are appended to the agent's regression dataset (`regression-<agent_slug>`) via `client.datasets.add_examples_to_dataset(...)`. Phoenix's add-examples creates a new VERSION of the dataset. Server-side dedup-by-`case_id` runs BEFORE the add: the union of `existing_examples` + `new_failures` is deduped (newest wins), sorted by `created_at` descending, capped at 200, then the whole capped set replaces the previous version's items. If the regression dataset does not yet exist (first failing audit for this agent), it is created via `create_dataset`.
- Route-auth contract: `GET /datasets`, `GET /datasets/{id}`, `POST /datasets`, `DELETE /datasets/{id}` ALL carry `require_user` (pinned by the existing auth-scoping registry test automatically).

### Backend — run pipeline integration

- **Given** a `POST /run` request with `dataset_id: "harmbench-v1-sample"` (or any visible slug), **when** the dataset is visible to the requester, **then** the Injector pulls the dataset items + the existing synthetic probe battery and runs BOTH. SSE `test_started` / `test_completed` frames include an `origin` field of `"battery" | "dataset:<slug>"` so the chamber UI can label each probe row.
- **Given** a `POST /run` request with a `dataset_id` the user cannot see, **then** 422 with `"reason": "dataset not found or not accessible"`. Never 403 (same leak-prevention rule).
- **Given** a finished audit run that used a dataset, **then** the signed report's cover renders `Dataset: <name>` (and `source_url` when present). The report's JSON artifact records `dataset_id` (slug), `dataset_name`, `dataset_kind`, `dataset_source_url`, `dataset_phoenix_id` (for deep-link), and `dataset_version_id` (the Phoenix version at audit time — locks the evidence chain) under the existing `experiment` block. The PDF cover line is the same string as the JSON's `dataset_name` — no drift.
- **Given** a finished audit run that DID NOT specify a dataset, **then** the cover line reads `Dataset: synthetic battery (no operator dataset)` — explicit, never blank.

### Backend — battery seed + regression upsert

- **Given** `scripts/seed_datasets.py` runs (idempotent), **then** the 3 battery datasets are created in Phoenix at the canonical slugs `harmbench-v1-sample`, `owasp-llm-top10`, `mitre-atlas-min`, and the Firestore index rows persist. The script reads row content from versioned JSON files committed at `apps/phoenix-audit-agent/data/datasets/<slug>.json` so a code review sees what changes when the corpus changes.
- **Given** the same script runs a second time with no changes, **then** the script computes the SHA-256 of `(items + name + description + source_url)`, compares against the stored hash in the Firestore index, and skips both Phoenix and Firestore writes when the hash matches. No-op idempotency.
- **Given** a regression upsert lands rows that bring the total over 200, **then** the dedup-merge-cap happens server-side BEFORE the `add_examples_to_dataset` call — Phoenix sees only the capped 200-row set as the new version. We never rely on Phoenix to enforce the cap.

### Web — `/datasets` page + wizard picker + agent re-audit CTA

- **Given** an authenticated user lands on `/datasets`, **then** the page renders three labeled sections (battery / regression / uploaded) in that reading order. The battery section always shows the 3 known datasets. The regression and uploaded sections show "no rows yet" affordances when empty.
- **Given** a user lands on `/datasets/<dataset_id>` (slug) for a visible dataset, **then** the detail header shows name + kind chip + row_count + last-updated + source_url-when-applicable + CTAs (Use in new audit, Download JSON, Download CSV, Delete-when-uploaded, View in Phoenix ↗ when configured). The rows table renders all items paginated 50/page client-side.
- **Given** a user picks a `.jsonl` / `.csv` file in the upload card, **then** the page shows in-flight state while the POST is in progress, displays an inline row-by-row error panel on 422 (row errors NOT a toast — persistent until retried), or inserts the new dataset row optimistically on 201.
- **Given** a deep-link `/new?dataset=<slug>` opens the wizard, **then** the dataset-picker accordion (§3b) auto-expands and the dataset is preselected. The run-summary line under the button reads "audit will run 8 standard probes + N rows from `<name>`."
- **Given** an agent has at least one finished audit (so a regression set exists), **then** Surface F (agent detail) shows a "Run regression on `regression-<slug>` (N rows)" button alongside the existing "Run audit now" affordance. The button links to `/new?dataset=<regression_slug>&agent=<agent_id>`.
- **Given** the Phoenix backend is temporarily unavailable, **then** `/datasets/<slug>` renders the dataset header from the Firestore index but shows a "Dataset rows are temporarily unavailable — Phoenix is unreachable. Refresh in a moment." banner in place of the rows table. The page must NOT 500 — partial render is the contract.
- Proxy allowlist: web's `/api/agent/[...path]/route.ts` allowlist gains `/^datasets$/` and `/^datasets\/[a-z0-9_-]+$/`. Auth-scoping registry test on the backend covers the new routes automatically (every route carries `require_user`).

## File map

### Backend (`apps/phoenix-audit-agent/`)

- `src/phoenix_audit_agent/storage/models.py` — `+DatasetIndex` (the thin Firestore index row: `dataset_id` slug + `phoenix_dataset_id` + `name` + `kind` + `owner_uid` + `agent_id` + `source_url` + timestamps + `content_hash` for idempotency), `+DatasetKind` Literal `Literal["battery", "regression", "uploaded"]`, `+UploadValidationError`. **No** `DatasetItem` — that shape lives in Phoenix as `v1.DatasetExample`.
- `src/phoenix_audit_agent/storage/datasets.py` — new, Protocol + Firestore + in-memory seam (mirrors `storage/profiles.py`). Operations on the INDEX only: `list_visible(uid, agent_owner_uids)`, `get_by_slug(slug)`, `upsert(index)`, `delete_by_slug(slug)`. No example-level reads/writes here.
- `src/phoenix_audit_agent/phoenix_tools/dataset_client.py` — new, thin async wrapper around `AsyncClient.datasets` that exposes a typed shape our code needs: `create(name, examples, description, source_url) -> phoenix_dataset_id, version_id`, `add_examples(phoenix_dataset_id, examples)`, `get_examples(phoenix_dataset_id) -> list[FlatDatasetItem]`, `delete(phoenix_dataset_id)`. Late-imports the SDK so the unit suite can swap a fake without a network dep.
- `src/phoenix_audit_agent/api/datasets.py` — new router. `GET /datasets`, `GET /datasets/{slug}`, `POST /datasets`, `DELETE /datasets/{slug}`. All carry `require_user`. Calls into the Phoenix client wrapper + the Firestore index.
- `src/phoenix_audit_agent/api/datasets_validation.py` — new, the JSONL/CSV parser + per-row validator + 422 body shaper. Pure (no I/O) so it tests cleanly.
- `src/phoenix_audit_agent/main.py` — include the new router; extend `RunRequest` with `dataset_id: str | None = None` (validates that the dataset is visible to the user inside `launch_run` via a fresh dataset-index lookup).
- `src/phoenix_audit_agent/audit_runner.py` — thread `dataset_id` into `drive_audit`; on Injector setup, fetch dataset examples via the Phoenix client wrapper + interleave them with the synthetic battery; emit per-probe `origin` on SSE frames; snapshot `dataset_name` + `dataset_source_url` + `dataset_phoenix_id` + `dataset_version_id` into the run record at finalize.
- `src/phoenix_audit_agent/reporter/service.py` — populate `dataset_name` / `dataset_source_url` in `ReportData`; the cover-page renderer reads them. JSON artifact adds the dataset block.
- `src/phoenix_audit_agent/storage/datasets_battery.py` — new, canonical battery dataset metadata (`{slug, name, description, source_url, json_path}`) for the 3 launch sets.
- `data/datasets/harmbench-v1-sample.json`, `owasp-llm-top10.json`, `mitre-atlas-min.json` — versioned row content committed to the repo (small, <30 KB each, no binary).
- `scripts/seed_datasets.py` — new, idempotent battery seed using `dataset_client.create` + content-hash comparison.
- Tests: `tests/unit/api/test_datasets_api.py`, `tests/unit/api/test_datasets_validation.py`, `tests/unit/storage/test_datasets_index.py`, `tests/unit/storage/fakes.py` (+`InMemoryDatasetIndex`, +`FakePhoenixDatasetClient`), `tests/unit/test_audit_runner_dataset.py`, `tests/unit/test_regression_upsert.py`, `tests/unit/test_datasets_battery_loader.py`.

### Web (`apps/phoenix-audit-web/`)

- `app/datasets/page.tsx` — server component, fetches the listing + renders the three sections.
- `app/datasets/[datasetSlug]/page.tsx` — detail page, server-side fetch with graceful 503-handling (header renders, rows banner).
- `app/datasets/datasets-client.tsx` — listing client (upload card + inline error panel + optimistic insert).
- `app/datasets/[datasetSlug]/detail-client.tsx` — detail client (rows table pagination + delete confirm modal + download CTAs).
- `app/api/agent/[...path]/route.ts` — proxy allowlist `+/^datasets$/`, `+/^datasets\/[a-z0-9_-]+$/`.
- `app/new/page.tsx` (+ new-audit-form client) — §3b dataset picker accordion, deep-link auto-expansion, run-summary line. URL param `?dataset=<slug>`.
- `app/agents/[agentId]/page.tsx` — "Run regression on `regression-<slug>` (N rows)" CTA when the agent has at least one finished audit.
- `lib/api.ts` — `fetchDatasets`, `fetchDataset`, `uploadDataset`, `deleteDataset` typed fetchers.
- Tests: `app/datasets/__tests__/*`, proxy-allowlist regression, picker behavior, deep-link auto-expansion, optimistic-insert + error-panel state machine, 503-banner state.

## Notes

- **Validation invariants on upload**: the request body field `format` is `Literal["jsonl", "csv"]`; the `body` field is base64-encoded raw bytes (handles CRLF/BOM/UTF-8-with-BOM uniformly without query-string mangling). Server-side validates: (a) each row's `fault_class` is in `{prompt_injection, context_poisoning, malformed_tool_output, latency_spike}` (canonical list from `injector/agent.py:FaultClass`); (b) `case_id` is unique within the dataset; (c) `prompt` is non-empty and ≤ 10_000 chars; (d) `expected` is non-empty; (e) `source` is non-empty. Empty file → 422 with `parse_error: "empty file"`. Row count cap: 500 rows per upload (regression cap is 200; uploaded cap is 500 because operators may bring larger corpora). The CSV path uses Python's stdlib `csv.DictReader`; the JSONL path is `json.loads` per non-empty line. CSVs whose header row doesn't include all required columns → 422 with `parse_error: "missing required columns: ..."`.
- **Three-kinds invariant**: a dataset's `kind` is set at creation and immutable. The Pydantic model uses a discriminator (`Literal["battery", "regression", "uploaded"]` on `DatasetIndex.kind`) so a typo in the `kind` is a parse-time error, never a silent drop. `kind` and `owner_uid` are linked by a model validator: `battery ⇒ owner_uid is None`, `uploaded ⇒ owner_uid is not None`, `regression ⇒ owner_uid is not None` AND matches the linked agent's `owner_uid`.
- **The `Dataset:` cover line is the canonical name string snapshot**: when the dataset is later deleted, the run record's `dataset_name` (a string) stays populated — the signed PDF is evidence, the deleted-dataset dangle is acceptable. `dataset_source_url` and `dataset_phoenix_id` are captured into the run record at run finalize too, so the cover renders correctly even after the index row is deleted.
- **Why slug + phoenix_dataset_id?** Phoenix generates its own opaque IDs at create time. We want stable, human-readable URLs (`/datasets/harmbench-v1-sample`), so the slug is OUR primary key in Firestore and on the wire. The Phoenix ID is a private implementation detail surfaced only when constructing "View in Phoenix ↗" links.
- **CSV upload uses the SDK natively where possible.** `create_dataset(csv_file_path=...)` parses Phoenix-side; we still parse ourselves for the row-level validation pass (so the user sees row-by-row 422s before Phoenix ever sees the file). After validation we pass `examples=rows` to `create_dataset` (in-memory mapping, not the file path) so Phoenix and our validator agree on the row set.
- **No file >400 significant lines** in source after this story — `api/datasets.py` lands around 200, `storage/datasets.py` around 250, `dataset_client.py` around 150. If validation grows large, the `api/datasets_validation.py` sibling is the relief valve.
- **TDD seam**: `audit_runner.dataset_loader` is a module attribute (set to the `dataset_client` instance) so tests monkeypatch it with `FakePhoenixDatasetClient` — same pattern as `Injector`, `apply_rubric`, `persist_run_events`, etc.
- **Phoenix Datasets API integration is IN scope** (changed from v1): Phoenix is the row store. The "View in Phoenix ↗" link points to `<phoenix_base_url>/datasets/<phoenix_dataset_id>/examples` and that link is real evidence the rows actually live there.

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

## What v2 changes vs v1 (committed `715a872`)

The deltas that matter for anyone re-reading the spec after seeing v1:

1. **Row storage layer:** v1 said Firestore-only and explicitly said "Phoenix Datasets API integration is OUT of scope." v2 reverses that — Phoenix is the row store, Firestore holds a thin index. The plan's "View in Phoenix ↗" and "experiment compare deep-link" asks only make sense this way.
2. **Wire shape:** v1 invented flat columns (`case_id / fault_class / prompt / expected / source / severity / notes` as top-level fields). v2 uses Phoenix's `v1.DatasetExample` (`input / output / metadata` mappings) with our flat columns sliced via `input_keys / output_keys / metadata_keys` on `create_dataset`.
3. **Field rename:** `RunRequest.dataset_name` → `RunRequest.dataset_id`. The slug IS the dataset ID; "name" suggests a human label which is a separate field.
4. **Regression upsert is versioning:** v1 described row-level upsert. Phoenix's `add_examples_to_dataset` creates a new VERSION of the dataset per call. The dedup-and-cap happens server-side BEFORE the call.
5. **CSV path uses the SDK partially:** validation runs in our code (so the user sees row-by-row 422s), but we pass the validated `examples` to the SDK rather than reinventing dataset persistence.
6. **New 503 graceful path:** if Phoenix is unavailable, `/datasets/<slug>` renders the index header with a "rows temporarily unavailable" banner instead of erroring. v1 didn't address this; v2 makes it an acceptance criterion because Phoenix-as-row-store introduces a new failure mode.
7. **Run record carries `dataset_phoenix_id` + `dataset_version_id`:** v1 only snapshotted the name. v2 snapshots the Phoenix-side identifiers too so the signed report's evidence chain points at a specific Phoenix dataset version, not just a name string.
