# story-9.14 — onboarding-wizard: first-login welcome flow on the A2 profile

**Epic:** 9 · **Depends on:** story-9.12 (user-profile)
**Decided with Abu 2026-06-10** (Unified Finish A3): a fresh sign-in lands today on an empty `/audits` page with sample chips and no guidance — the user has no clear first action and no way to set the org / default framework they were going to set in `/settings` anyway. The wizard converts a cold landing into a guided first action, persisting through the server-side profile (story-9.12) so it shows EXACTLY ONCE per account.

## Why

The profile already carries `onboarded: false` by default; nothing reads it. Each fresh-sign-in user (judges included) sees a sample-loaded audits page with no welcome and no "what does this do" framing — easy to mistake for a public demo. The wizard is the missing first surface.

## BDD acceptance criteria

- **Given** an authenticated user whose profile has `onboarded: false`, **when** they navigate to `/audits`, **then** they are server-side-redirected to `/onboarding` (the wizard is unmissable, not a dismissable banner).
- **Given** an authenticated user whose profile has `onboarded: true`, **when** they navigate to `/onboarding`, **then** they are server-side-redirected to `/audits` (the wizard never reappears).
- **Given** the wizard, **then** it has four steps in this order: **Welcome / what this is** · **Org name (skippable)** · **Default framework** · **GitLab pointer (honest "coming next")**, followed by a final **CTA** panel offering "Run your first audit" → `/new` and "Browse sample audits" → `/audits`.
- **Given** the user clicks "Skip" on a step, **then** that step's field is NOT included in the PATCH (per-step skip = field omitted from the final upsert), and the user advances.
- **Given** the user clicks "Finish" on the final CTA, **then** `PATCH /profile` is called ONCE with the accumulated fields plus `onboarded: true`; the wizard then routes to the chosen destination (`/new` or `/audits`).
- **Given** the PATCH fails, **then** the user is NOT routed away; a visible error notice surfaces and a Retry control sends the same request — never a fire-and-forget that leaves the user thinking they're onboarded when the server says they aren't.
- **Given** a user signs in but the profile fetch fails (registry unreachable), **then** `/audits` does NOT redirect to `/onboarding` (we don't trap users in a forced wizard on a transient outage); the live-error notice on `/audits` discloses the problem instead.
- **Given** the wizard's framework step, **then** the 5 options are the same set the `/new` page uses (EU AI Act / NIST AI RMF / HIPAA / SOC 2 + AI / Custom) and the choice updates `framework_default` on the profile, which `/new` then preselects.

## File map

- Web: `app/onboarding/page.tsx` (new — server-side gate + render), `components/onboarding/onboarding-client.tsx` (new — multi-step state machine + PATCH on Finish), `components/onboarding/steps/{welcome,org,framework,gitlab,cta}.tsx` (new — one file per step, ≤ 100 lines each), `app/audits/page.tsx` (add server-side onboarding-redirect check — same fetch as the welcome page so we don't double-roundtrip), `lib/onboarding.ts` (new — shared `needsOnboarding(profile)` predicate + `fetchProfileForGate()` server util), `tests/onboarding.test.ts` (new), `docs/stories/story-9.14-onboarding-wizard.md` (this file).
- Backend: none (profile API + onboarded field are already on the wire from story-9.12).
- Assets: `docs/assets.md` (new — designer request for wizard step illustrations, progress idiom, empty-state art; no prescriptive colors).

## Notes

- The wizard renders inside the existing `PageShell` (TopBar + PageFoot) so the user sees they ARE signed in — it's not a modal hijacking the page.
- Per-step "Skip" omits the field from the PATCH; "Next" includes it (PATCH is partial via `extra='forbid' + exclude_unset` from story-9.12 — unknown fields are 422'd, omitted fields keep their stored defaults).
- The GitLab step is a teaser, not a connect flow — Wave C delivers the real OAuth. The step says so honestly ("Coming with GitLab MR filing — Wave C"), the wizard advances, and the user is NOT blocked.
- `onboarded: true` is only set on Finish. Closing the browser mid-wizard leaves the user re-entering the wizard on next sign-in (correct UX: incomplete is not done).
