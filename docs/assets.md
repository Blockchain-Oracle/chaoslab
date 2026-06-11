# Phoenix Audit — Designer Asset Requests

> Companion to `docs/DESIGNER-BRIEF.md`. The main brief describes the product and persona; **this document is a punch-list of concrete asset requests** the designer turns into delivered visuals. Each request gives a surface, the user moment, what the asset has to do, and the data context — no colors, no fonts, no library suggestions. The designer owns the visual answer.
>
> Two ground rules carried from the main brief:
>
> 1. Maya is a Director of AI Governance. She's senior, compliance-fluent, not an engineer. Every asset should read as "regulator-ready" not as "developer tooling."
> 2. Honesty over polish: real flows, real failures, real "this feature is coming next" disclosures. Nothing in here should look like a marketing site for a product that doesn't exist yet.

---

## Story-9.14 — Onboarding wizard (Surface O)

**Where it lives:** `/onboarding`. The user lands here exactly once, immediately after their first sign-in. The wizard writes `onboarded: true` on the `users/{uid}` profile when they finish; from then on they're routed straight to `/audits` and never see this surface again.

**The user moment:** Maya has just minted her account. She doesn't know what Phoenix Audit looks like inside yet, she has no audits, no agents registered, and the only data she'll see if we drop her straight on `/audits` is the two seeded sample runs (which would read like a public demo). The wizard's job is the 60-second framing — what Phoenix Audit is, what Maya can set up now (org + default framework), what's coming next (GitLab connect), and which direction to point her: run a real audit, or open a sample one first.

**What the user cannot skip:** the wizard itself (it's the gate). Within the wizard, **every step is skippable** — anything the user skips keeps the profile default. Finishing always sets `onboarded: true` even if they skipped everything.

### Step content (what the designer is decorating)

The wizard is 5 logical screens. The data on each one is locked; the visual treatment is open.

1. **Welcome / what this is.**
   - Kicker: "Welcome"
   - Headline: "Phoenix Audit, the AI agent that audits other AI agents."
   - Body: 90-second adversarial battery → LLM-as-judge over Phoenix traces → root-cause clustering → signed audit report.
   - Subtle line confirming the signed-in email so Maya sees the wizard recognises her.
   - Promise: "Four short questions then you're looking at your first signed report. Each step is skippable."

2. **Org name (skippable).**
   - Kicker: "Your organization"
   - Headline: "Who's filing this?"
   - Body: Org name appears on the signed report cover and Annex IV documentation. Skipping is fine — Maya can set it in Settings later.
   - Field: single text input. No validation beyond non-empty-or-omitted.

3. **Default regulatory framework.**
   - Kicker: "Default framework"
   - Headline: "Which control set anchors your reports?"
   - Body: This is the framework whose articles Phoenix Audit cites on the report cover and the regulatory mapping appendix. Per-audit override on the `/new` page.
   - 5 options (radio): **EU AI Act** · **NIST AI RMF** · **HIPAA** · **SOC 2 + AI** · **Custom**. Each option carries a one-line sub.

4. **GitLab connection — coming next.**
   - Kicker: "GitLab connection · coming with Wave C"
   - Headline: "File hardening recipes straight into your repo."
   - Body explains the planned flow: per-account OAuth (no shared service token); review-first (button on the recipe page, never automatic); MR only adds files under `phoenix-audit/`; we never read or modify customer code.
   - Honest "coming next" treatment — not a connect button that pretends to work today. The wizard advances to the next step regardless.

5. **CTA — pick the landing.**
   - Kicker: "You're set"
   - Headline: "Where do you want to land?"
   - Two options:
     - **Run your first audit** → `/new` (the real new-audit flow against an HTTPS or A2A endpoint, ~90 seconds, ends with a signed PDF).
     - **Browse sample audits** → `/audits` (the seeded ownerless sample runs from story-9.11; full preview, replay, recipe, signature all signed).
   - On submit failure: visible error notice, the user is NOT routed away, a retry sends the same PATCH.

### Asset requests — Surface O

**O-1. Progress idiom for the 5-step wizard.**
The progress affordance has to read "you're 2 of 4 questions in", not "you're trapped in a 5-step flow." The progress affordance is the user's contract that we will let them out. Whether that's a horizontal step-strip with the current step labeled, a fractional counter, a journey map, or something else is the designer's call. Constraints: must work when one step is the "coming next" placeholder (the GitLab step has no input), must show that any step can be skipped, must not look like a sign-up funnel.

**O-2. Welcome step illustration.**
The Welcome step is the only screen where Maya sees zero data. It has to land the genre fast: this is a compliance audit machine, not a code-review tool. The illustration's job is to show the "agent auditing another agent" loop without resorting to literal robots-talking-to-robots clipart. Think: an audit seal, an evidence chain, a regulator's binder, a phoenix mark — any of those visual ideas is in scope. We need ONE primary illustration on this step plus a way the seal/logomark can carry through the rest of the wizard so the four screens read as a set.

**O-3. Org-name step state art.**
The org step is a single text input on a mostly empty card. Designer call on whether it gets a small spot illustration (e.g. a filing-folder mark) or stays minimal. If illustration, it must read as "this is paperwork that matters" not "fill out this form to claim your prize."

**O-4. Framework step radio rows.**
5 framework options as a vertical radio group. The selected row needs a clear, deliberate selection treatment (the current prototype uses an inset ember-deep bar; designer can replace). Each row carries a name + one-line description. EU AI Act is the default. Custom is "bring your own control mapping" — designer can mark this row as distinct from the four named frameworks.

**O-5. GitLab step "coming next" treatment.**
This step is the only one in the wizard where the user can't do the thing. The designer's job: a treatment that looks like a **promise** not a **broken button**. The card explains how the OAuth will work, the review-first discipline, the additive-only file scope. The Next button stays available so the user is never trapped. The "coming next" badge has to be honest (we say "Wave C" internally; the designer can rename the badge).

**O-6. CTA step destination cards.**
Two side-by-side option cards (current prototype uses `.opt-card`). One reads "Run your first audit" → `/new`, the other "Browse sample audits" → `/audits`. The designer's call whether they get cover illustrations (a probe icon vs a sample-document icon, say). Both cards must work when the submit is in flight (`submitting=true`) — they should look paused, not broken.

**O-7. Submit-failed state.**
When the PATCH to `/profile` fails (network outage, server 5xx), the CTA step shows an inline error. Designer: the affordance has to make it clear _the user is not onboarded yet_ and that clicking the same destination button again is the right next action. No silent "looks fine" recovery.

**O-8. Empty-state art for `/audits` after first onboarded landing.**
Maya finishes the wizard, picks "Browse sample audits" or "Run your first audit." Either way, the FIRST time she lands on `/audits` after onboarding, the only rows in the table are the seeded samples. That table currently labels them with `SAMPLE` chips. **Open question for the designer:** does that empty-personal / sample-only state need its own treatment (e.g. an inline "Once you run your first audit, your row lands above the samples" affordance), or does the sample chip alone do the work? Either answer is fine; if the answer is "give it a treatment", design the treatment.

### Behavior notes for the designer

- The wizard always opens on Welcome. There is no "resume where I left off" — closing mid-wizard means re-entering the wizard from the top on next sign-in (intentional UX: incomplete is not done).
- Profile values seed the form fields on entry (a user who pre-populated something via the API still sees their value).
- The PATCH is sent ONCE, on Finish. Per-step skip just marks the field as omitted; per-step Next includes it.
- The wizard renders inside the same `PageShell` (top bar + page foot) as every other product page. The user must see they're signed in — this is not a modal hijacking the screen.

---

## Story-9.16 — Docs page upgrade (Surface D) — placeholder

The full docs-upgrade brief lands when story-9.16 starts. Pre-allocating the heading so the designer knows it's coming and the index doesn't change later.

---

## Story-9.15 — Datasets surface (Surface S) — placeholder

The full datasets-surface brief lands when story-9.15 (B2 / phoenix-datasets) starts. Same reasoning as 9.16 — placeholder so the index is stable.
