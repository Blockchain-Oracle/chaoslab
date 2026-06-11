# story-9.21 — officer-annotations: human review layer + Phoenix deep-links

**Epic:** 9 · **Depends on:** story-9.7 (phoenix-sessions), story-9.13 (report-presentation), story-9.20 (docs-v2)
**Source:** Wave C4 in the unified-finish plan (recovered S9.9) + issue #109 items 1 and 3 (PDF span hyperlinks, Attack Matrix deep-links). This is the demo narrative's "blockchain-explorer moment" (docs/demo-strategy.md): report → click → raw evidence in Phoenix.

## Why

A signed report is a summary; the Phoenix trace is the evidence. Today the two are disconnected — span IDs print as dead monospace text, the Attack Matrix cells go nowhere, and a compliance officer has no way to record "a human reviewed this cluster and confirmed it". The Arize judges' first auto-fail check is "Phoenix used as dashboard only (no eval loop)" — the annotation write-back closes the loop machine-side, and the officer verdict closes it human-side: a HUMAN annotation, written back onto the same spans, visible in the same Phoenix UI.

**Design decision (deviation from the recovered plan's wording, rationale recorded):** the plan said `PDF "reviewed-by-human" line`. A signed PDF is immutable — mutating it after an officer review would break the Ed25519 signature, the product's core promise. The review trail is therefore a SEPARATE, DATED layer: persisted on the run record, rendered alongside the signed artifact on the report page, exported in the run's JSON detail, and written into Phoenix as a human annotation. The signed PDF gains only what exists AT SIGNING TIME: clickable span links (stable Phoenix URLs, with the existing residency paragraph already disclosing the 24h trace-retention window they live in).

## BDD acceptance criteria

### Phoenix deep-links

- **Given** `PHOENIX_UI_BASE` is configured (e.g. `https://app.phoenix.arize.com/s/blockchainoracle-dev`), **then** `RunDetailResponse` carries `phoenix_ui_base` and `phoenix_project` (from `TARGET_PHOENIX_PROJECT`), and a pure web helper `phoenixSpanUrl(base, project, spanId)` builds `{base}/projects/{project}/spans/{spanId}`. **Given** the setting is empty, **then** the fields are `null` and every deep-link affordance is absent — never a dead link.
- **Given** an Attack Matrix cell whose probe carries a `spanId` and a non-null `phoenix_ui_base`, **when** clicked, **then** the Phoenix span view opens in a new tab. Cells without a spanId (transport failures) render exactly as today.
- **Given** the PDF renders at finalize with `PHOENIX_UI_BASE` set, **then** each probe row's span-id cell becomes `<a href="{span URL}">{span_id}</a>` (WeasyPrint emits real PDF link annotations) and the probes section gains one footnote line tying link lifetime to the residency window. Empty setting ⇒ today's plain text.

### Officer review (the human layer)

- **Given** the run's OWNER (sample runs are not reviewable — 422) calls `POST /runs/{run_id}/clusters/{cluster_id}/review` with `{"verdict": "confirmed"|"disputed", "note"?: ≤500 chars}`, **then** (a) the review persists onto the run record as `cluster_reviews[cluster_id] = {verdict, note, reviewer_email, reviewed_at}` (last-write-wins on re-review), and (b) a HUMAN span annotation (`annotator_kind="HUMAN"`, name `officer_verdict`, label = verdict, explanation = note) is written to Phoenix via the existing `write_annotation` path onto the cluster's exemplar span — CONTAINED: a Phoenix outage still persists (a) and the response discloses `{"phoenix_annotated": false}`.
- **Given** a `cluster_id` not on the run's recipe/clusters, **then** 422. Foreign run ⇒ 404. Unknown verdict ⇒ 422.
- **Given** a reviewed cluster, **then** the report page's cluster section shows `Reviewed by {email} · {date} · CONFIRMED/DISPUTED` (+ note) in place of the review control, plus a "Review in Phoenix ↗" deep-link (exemplar span) when deep-links are configured; `GET /runs/{run_id}` carries `cluster_reviews` so the registry JSON export includes the human trail.
- **Given** the staging annotation write-back failure (known issue), **then** the story's live verification diagnoses and fixes the machine-side write-back (judge-phase cluster annotations) — the SSE `annotation_writeback_failed` disclosure must read `false` on a fresh staging audit.

### Always

- Verdicts are a closed Literal; reviews are owner-scoped writes on owner-scoped runs; no token/email beyond the reviewer's own appears anywhere new. Offline tests via the established seams (fakes for run store; recording fake for the annotation client).

## File map

- `config.py`: `PHOENIX_UI_BASE: str = ""` (+ https-only validator like PUBLIC_WEB_URL).
- `storage/models.py`: `ClusterReview` model + `RunRecord.cluster_reviews: dict[str, ClusterReview]` (+ RunCompletion passthrough not needed — reviews write via a dedicated merge).
- NEW `api/runs_review.py`: the review endpoint (runs.py is near cap) — validation, persistence (`persist_run_completion`-style merge or a dedicated store method `merge_cluster_review`), contained Phoenix annotation via `phoenix_tools/write_annotation`.
- `api/runs.py`: `RunDetailResponse` gains `phoenix_ui_base` / `phoenix_project`.
- Web: `lib/phoenix-links.ts` (NEW, pure) + matrix cell click-through + report-page cluster review control (`components/report/cluster-review.tsx` NEW, thin shell over `lib/cluster-review.ts` request logic) + reviewed-state rendering; proxy allowlist `+ /^runs\/[id]\/clusters\/[id]\/review$/`.
- `reporter/_html.py`: probe span-id cell → anchor when configured; footnote line.
- Tests: backend `tests/unit/api/test_runs_review_api.py`, `tests/unit/test_report_links.py` (renderer), settings validator pin; web `tests/phoenix-links.test.ts`, `tests/cluster-review.test.ts`, allowlist extension.

## Notes

- Exemplar span for a cluster: the first failing probe span_id belonging to that cluster (clusters carry probe indices/span ids through tally → report.json; verify exact field at implementation and pin it).
- The machine write-back failure on staging is undiagnosed — first implementation step is reproducing it locally against real Phoenix (suspect: space-scoped base URL vs the annotations REST path). Fix lands in this story; if it turns out to be an Arize-side limitation, the disclosure stays and the story documents it.
- `PHOENIX_UI_BASE` is deliberately separate from `PHOENIX_COLLECTOR_ENDPOINT` (OTLP ingest ≠ UI origin; BYO customers may differ).
- Staging env addition (deploy workflow): `PHOENIX_UI_BASE=https://app.phoenix.arize.com/s/blockchainoracle-dev`.
