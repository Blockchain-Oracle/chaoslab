# story-9.13 — report-presentation: restore the designed report/recipe experience on real artifacts

**Epic:** 9 · **Depends on:** story-9.11 (truth-pass-2)
**Decided with Abu 2026-06-10 (staging walk feedback):** PR #100's fixture purge deleted the designer's presentation layer along with the fake data — the PDF-style report preview with the Cloud-KMS signing stamp, verdict stamps, and the recipe's unified-diff rendering. The report page degraded to four raw-file buttons and a heading that wraps one word per line. Restore the experience, fed by the REAL artifacts (which now exist and are richer than the fixtures ever were).

## Why

The signed report is the product's money shot. Real `report.json` (probes, verdicts, scores, root causes), `signature.json` (real Ed25519 fingerprint, per-artifact SHA-256, KMS key version), and `recipe.md` (clusters, prompt patches, tool-validation diffs) are uploaded per run and served via fresh-signed URLs — everything the deleted components displayed from fixtures is now real.

## BDD acceptance criteria

- **Given** a finished run with `report_available=true`, **when** `/report/[runId]` loads, **then** the page renders the multi-page report preview (cover & attestation / executive summary / adversarial tests / failure clusters / hardening recipe / framework appendix) populated from the run's REAL `report.json` — real probe rows with verdict stamps, real counts, real root causes.
- **Given** `signature.json` loads, **then** the cover page's attestation block shows the REAL `public_key_fingerprint_sha256`, algorithm, KMS key version and `signed_at`, and the signing stamp renders (the "signed" seal animation).
- **Given** the recipe page of the preview, **then** the run's REAL `recipe.md` renders in-app: section structure preserved, fenced patch/diff content with diff-line styling (`+` add / `-` remove / `@@` hunk) — never a raw-text dump in a new tab.
- **Given** an artifact fetch or parse fails, **then** the page DISCLOSES which artifact failed and falls back to the download buttons — never a silent blank page.
- **Given** the page header, **then** the title renders on a normal line (the one-word-per-line wrap is fixed) and the download buttons remain available as secondary actions.
- **Given** a run without a report (`report_available=false`), **then** the honest "report not yet available" state remains.

## Additional criteria (scope confirmed with Abu: FULL restore, app + PDF)

- **Given** the downloadable `report.pdf`, **then** its cover carries the seal/stamp treatment and the REAL public-key fingerprint + KMS key version (not just "detached sidecar" text); the "Hardening recipe" page renders the recipe's clusters/patches/diffs content — NEVER the raw signed URL as body text; the "Regulatory mapping" page carries the full framework article table.
- **Given** the report page's signature affordances, **then** "Signed JSON"/"Signature sidecar" raw-tab buttons are replaced by an in-app verify panel ("Signed with Ed25519 via Cloud KMS · fingerprint `79e1…` · per-artifact SHA-256") with proper download actions beneath it.

## File map

- Web: `lib/report-doc.ts` (new — `parseReportDocument`, `parseSignatureDocument`, `parseRecipeMarkdown`, diff-line classifier), `lib/api.ts` (+artifact fetch helpers reusing the events.json server-fetch pattern), `app/report/[runId]/page.tsx` (server-fetch artifacts), `components/artifacts/report-pages.tsx` (restored from 1341cd1~1, fixture imports → props), `components/artifacts/report-preview.tsx` (restored rich layout + verify panel + fixed header grid), `components/artifacts/recipe-md-view.tsx` (recipe.md renderer with diff styling), tests (`report-doc.test.ts`).
- Backend: `reporter/` PDF template (cover seal + fingerprint block, recipe content page, regulatory mapping table) + renderer tests.

## Notes

- The old `/recipe/[recipeId]` route stays deleted — the recipe renders as a page INSIDE the report preview; the signed `recipe.md` URL remains the download.
- The appendix page's framework control mapping is presentation copy keyed off `framework_label`; findings counts come from real cluster data.
- The old recipe-view's "ships inside merge request !214" line was fixture fiction — real MR filing arrives with C2 (gitlab-oauth-connect); the restored recipe view must NOT fake it.
- The PDF is rendered BEFORE the sidecar is signed — the cover shows the signing KEY's fingerprint/version (known pre-render); `signed_at` lives only in the sidecar.
