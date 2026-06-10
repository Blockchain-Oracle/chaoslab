# Story 9.10 — UX truth pass: the signed-in app tells no lies

**Epic:** Epic 9 — product surfaces real
**Status:** IN PROGRESS
**Depends on:** story-9.4-firebase-auth

## Why

Abu's live staging walk + an 11-finding read-only audit (2026-06-10) found the
signed-in app blending fixtures with real data until neither is trustworthy:
a seeded agent registered at `http://localhost:8001` fires real (failing)
runs with one un-confirmed click; fixture verdicts animate over real failed
runs; "signed PDF" links exist for runs with no report; /settings shows a
fake "connected" GitLab and a fictional operator. For a compliance product,
every one of these is a credibility wound. Plan: jazzy-churning-koala Wave 0.

## BDD acceptance criteria

1. **Demo seed points at the real target.** `DEMO_TARGET_URL` setting
   (default `http://localhost:8001` for local dev); the deploy workflow
   resolves it to the live target-agent URL like `AGENT_URL`. The seeded
   record's url reflects it.
2. **No one-click live runs.** Every "Run audit now" CTA (agent cards, agent
   detail, audits empty rows) navigates to `/new?agent=<id>` with the
   agent's URL prefilled — the wizard is the single confirm surface. Sample
   agents' CTAs do the same (their detail pages are SAMPLE-chipped; their
   historical audits link to clearly-sample views).
3. **The live run page tells the truth.** A real run renders ONLY real SSE
   frames: real run id in the header, no fixture verdict animation, the
   error frame terminates the battery display honestly.
4. **Artifact links are earned.** "signed PDF"/"recipe"/"MR ↗" render only
   when the record carries them (`report_available`, `recipe_id`, real
   `mr_url`). A real run without a report gets the honest empty state —
   never the sample preview.
5. **Own-data-first.** Signed-in /audits and /agents show the user's real
   records; the stat blocks compute from REAL rows only. Samples appear
   only via one labeled "Explore sample data" affordance (and /replay stays
   the public showcase). Sample DETAIL pages (report/recipe/agent) carry
   the SAMPLE chip; sample-only actions ("Sign and file") are disabled.
6. **Settings tells the truth.** Real account identity (email/uid from the
   session); fixture operator/org/KMS/GitLab-connected copy removed.
   Integrations show honest states ("configured via environment" / "not
   connected"); no dead Save/Reconnect buttons.
7. **No dead links.** `#mr`, `#phoenix-trace`, `#docs` eliminated: MR links
   only when real; span links to real Phoenix URLs on real runs (sample
   views label theirs as sample); docs links go to `/docs`.
8. **/docs exists** (public): register an agent, run an audit, read the
   report/recipe/MR, monitoring, datasets, auth + sample-vs-real policy.
   Real screenshots captured from the live app (script reusable for the
   Devpost gallery).
9. **No hydration errors** on authed pages (React #418 fixed at root).
10. **/monitoring loads the real registry** (the walk saw `agent API 404 on
/schedules` — diagnose and fix the path/contract drift).

## File map (representative)

- `apps/phoenix-audit-agent/src/phoenix_audit_agent/{config.py,storage/agents.py}` — DEMO_TARGET_URL
- `.github/workflows/staging-deploy.yaml` — `__RESOLVE_TARGET_URL__`
- `apps/phoenix-audit-web/components/agents/*`, `app/agents/*` — CTA rewiring
- `apps/phoenix-audit-web/app/run/[runId]/*`, `components/chamber/*` — real-frame truthfulness
- `apps/phoenix-audit-web/app/audits/*`, `lib/sample-merge.ts` — own-data-first + stats
- `apps/phoenix-audit-web/app/settings/*` — honest settings
- `apps/phoenix-audit-web/app/docs/page.tsx` (new) + `scripts/capture-docs-shots.ts` (new)
- tests: vitest per CTA/link/stat rule; pytest for seed URL setting
