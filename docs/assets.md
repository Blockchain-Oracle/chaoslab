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

## Story-9.20 — Docs page upgrade (Surface D)

**What ships:** /docs grows from a single-column scroll into a navigable manual: sticky sidebar TOC + four new sections (datasets, GitLab connect + MR review, email reports, auth & privacy) + per-section screenshots captured from the live app.

### D-1 — Sticky sidebar TOC

- ≥1040px: a left rail listing every section (§1–§11), anchor-linked, active section tracked on scroll (the etched mono register — same idiom as the report page's page rail). ≤1040px: the rail collapses to a horizontal scroller pinned under the header, or simply disappears (designer's call — the page reads fine linearly).
- Designer owns: rail typography/active treatment, the scroll-position indicator idiom.

### D-2 — New sections (content provided, layout yours)

- §Datasets: upload your own test cases (JSONL/CSV), run audits with them, regression sets that accumulate per agent.
- §GitLab: per-user OAuth connect, review-first MR filing — the "we only ADD files under phoenix-audit/" promise rendered prominently.
- §Email: scheduled summaries + "Email me this report" with the signed PDF attached.
- §Auth & privacy: accounts, data residency paragraph, what's public (landing, /replay) vs private.

### D-3 — Screenshots

- Existing `scripts/capture-docs-shots.ts` captures from the live app; new sections each get a slot. Same treatment as today (hairline border, r-lg corners). Mobile captures NOT required — the page itself is responsive post-S9.19.

### D-4 — Favicon (shipped with the story, not a designer ask)

- `app/icon.svg` now ships the brand glyph (diamond + ember spark on paper) — the favicon 404 is closed. If you want a richer mark (e.g., the seal), deliver an SVG and it drops in.

---

## Story-9.15 — Datasets surface (Surface S)

**Where it lives:** A new top-level page at `/datasets`, plus a new picker inside the existing `/new` audit wizard (Surface B), plus a single button on Surface F (target agent detail). The dataset record is also referenced by the signed PDF cover page and the report's experiment block, both of which already exist as designed surfaces — adding a line, not redesigning the layout.

**The user moment.** Maya already ran her first audit. She got a verdict — one cluster says "the agent obeyed a prompt-injection on three out of eight probes." She wants two things the product doesn't have yet:

1. **Regression evidence.** She wants tomorrow's audit to re-run _the same eight probes_ — plus those three failing probes again — so she can show the regulator "the same battery on the same agent, before-and-after the fix." Today, the next audit's probes are sampled from scratch and the regulator can't tell whether the fix held under the SAME conditions.
2. **Her own cases.** Her organization has its own corpus of "things our agents must refuse" — pulled from prior incidents, internal red-team exercises, the OWASP LLM top-10 mapped against her domain. She wants Phoenix Audit to run those alongside the synthetic battery, not instead of it. Upload a JSONL or CSV, give it a name, run audits against it from then on.

What we are building: a single feature that names, persists, lists, runs, and downloads three KINDS of datasets, all surfaced in the same place.

### The three dataset kinds Maya sees

The designer should treat these as three categories on the same listing page, distinguished visually so Maya never confuses "the product gave me this" with "I uploaded this."

1. **Battery datasets.** Read-only, ship with the product, every user sees the same rows. There are 3 of them at launch — `harmbench-v1-sample` (50 rows curated from HarmBench), `owasp-llm-top10` (one canonical adversarial case per OWASP LLM-Top-10 category), and `mitre-atlas-min` (a small MITRE ATLAS coverage map). Maya can **view** + **download** + **use in a new audit**. She cannot edit or delete. The "View in Phoenix ↗" link opens Phoenix's dataset detail page in a new tab — Phoenix's own tool, not ours.
2. **Regression datasets.** One per registered target agent, named `regression-<agent_slug>`. Auto-populated: every audit run upserts its failing probe rows into this dataset (one row per failing probe, capped at the most-recent 200). Maya can view, download, and re-run any audit with this set selected. She cannot edit individual rows — they are evidence the system produced from her real audits. The visible affordance is a **"Re-audit with this set"** button (lives both on the dataset detail and on the agent detail page).
3. **Uploaded datasets.** Maya's own corpus. Upload a JSONL or CSV; name it; pick a category list it covers (the same `prompt_injection / context_poisoning / malformed_tool_output / latency_spike` taxonomy the rest of the product uses, so it composes cleanly into a run). She can rename or delete an uploaded dataset (the others not). Validation runs server-side on upload — see Notes.

### Data shape (what a dataset row IS — the designer needs this to design the table)

Every dataset row, regardless of kind, is one **adversarial test case**. The shape is:

```text
case_id        — short slug, unique within the dataset (e.g. "pi-001", "owasp-llm01-3")
fault_class    — one of: prompt_injection, context_poisoning, malformed_tool_output, latency_spike
prompt         — the actual adversarial input that gets sent to the target agent
expected       — short string describing what the agent SHOULD do (e.g. "refuse and offer the legitimate path")
source         — provenance string: "HarmBench/test:0042" / "OWASP LLM-Top-10:LLM01" / "internal-redteam-2026Q1" / "user-upload"
severity       — optional, low|medium|high (uploaded sets can leave blank — battery sets always have it)
notes          — optional free-text the operator can attach (uploaded sets only)
```

The dataset itself carries: a `dataset_id` (slug), a human-readable `name`, the `kind` (`battery` / `regression` / `uploaded`), `owner_uid` (`None` on battery, the user's uid on uploaded, the agent owner's uid on regression), a count of rows, a created-at and updated-at timestamp, and a `source_url` for the original artifact when applicable (HarmBench's GitHub URL, the OWASP doc URL, etc.).

The signed report's experiment block already has a `dataset_name` slot designed-in; this story finally populates it with a real value instead of "EU AI Act baseline."

### What the user can do, every state we need designed

The designer needs visual answers for the following discrete states. Each is a real moment in Maya's life with the product. None of these may collapse into "a generic empty state" — each has its own information.

**On the `/datasets` listing page:**

- **First-time landing (no uploads, no audits yet)** — only the 3 battery rows show. The page must make clear "these came with Phoenix Audit, you didn't upload them" without making them feel like ads.
- **Has uploaded datasets but never finished an audit** — battery rows + uploaded rows. No regression sets yet (those need a finished audit). The empty regression section needs a one-line affordance explaining where regression sets come from.
- **Returning operator, full populated state** — battery + 2 uploaded + 3 regression. The visual hierarchy should keep "what I made" close-by and "what shipped with the product" out of the way.
- **Upload in flight** — Maya picked a file; we're parsing + validating server-side. The upload card has a single in-progress state with the filename + a stoppable affordance.
- **Upload failed validation** — server-side rejection. Maya needs to see _which row_ failed and _why_ (e.g. "row 17: missing fault_class"). This must NOT be a toast that disappears — it has to be a persistent inline panel attached to the upload card with row-specific feedback, so she can fix her file and re-upload.
- **Upload succeeded** — the new dataset appears in the listing immediately (optimistic insert OK; the row should highlight briefly so she sees it landed).
- **Delete uploaded dataset** — confirmation modal warns that any audit referencing this dataset will lose the reference; finished audits keep their signed PDFs intact, but Maya can no longer re-run with the deleted set. The confirm copy must be clear about what's irreversible vs. what survives.

**On the dataset detail view (`/datasets/[dataset_id]`):**

- **Header** with the dataset name, kind chip (battery / regression / uploaded), row count, last-updated timestamp, source URL (when applicable, as a "View source ↗" affordance), and two CTAs: **"Use in new audit ↗ /new?dataset=<id>"** + **"Download (JSON | CSV)"**.
- **Rows table**, paginated client-side (50 per page), columns: `case_id` · `fault_class` chip · truncated `prompt` (with hover/click to expand to full text) · `expected` · `source` · `severity`. Uploaded rows have an extra "view notes" column when notes are set.
- **For battery datasets**, an extra "View in Phoenix ↗" link in the header points to Phoenix's own dataset URL.
- **For regression datasets**, a top-of-page banner reads "Auto-populated from N audits of <agent_name>" with a link back to that agent's detail page. There's a "Re-audit with this set" button that takes Maya to `/new?dataset=<id>&agent=<agent_id>` with both prefilled.
- **For uploaded datasets**, a "Delete" CTA appears in the header (with the confirmation modal). Uploaded datasets get a "Notes from operator" column where each row's optional notes are visible.

**Inside the `/new` audit wizard (Surface B):**

- A new section §3b — **"Use a specific dataset (optional)"** — appears between the framework picker and the overrides accordion. By default the section is collapsed; opening it reveals a single combobox listing all datasets the user can see, grouped by kind. When a dataset is selected, the dataset name shows under the run button alongside the row count: "audit will run 8 standard probes + 50 rows from `harmbench-v1-sample`." When deep-linked via `/new?dataset=<id>`, the section is auto-expanded and the dataset preselected. If `?agent=` is also present, both prefill.
- The wizard's "Run audit" affordance should not change shape when a dataset is selected — Maya already learned where that button is.

**On Surface F (target agent detail):**

- A new affordance — **"Re-audit with last regression set"** — appears next to the existing "Run audit now" button, but only when the agent has at least one finished audit. The button text changes to "Run regression on `regression-<agent-slug>` (N rows)" once the set exists. Clicking it goes to `/new?dataset=<regression_id>&agent=<this_agent_id>` so the wizard pre-fills both.

### Asset requests — Surface S

**S-1. Dataset kind chip.** Three distinct chip treatments — `BATTERY`, `REGRESSION`, `UPLOADED`. Must read as distinct categories at glance without relying on color alone (the existing `SAMPLE` chip on `/audits` is the visual reference for "system-provided"; uploaded sets should read as "this is mine"). The chip travels everywhere a dataset is named — listing rows, detail header, wizard combobox row, report cover.

**S-2. Datasets listing page layout.** The page is divided into three sections — battery / regression / uploaded — in that visual reading order. The designer decides whether they are stacked accordions, three card columns, three panels, or some other organization. Empty sections (no regression sets yet, no uploads) must still be visible, with the one-line "where regression sets come from" / "upload your own" affordance per section. The page must NOT look like an empty product when the user has only the 3 battery rows — those rows have to feel like real content the operator can act on.

**S-3. Upload card.** Lives at the top of the listing page (or inside the "uploaded" section — designer's call). Drop-zone affordance that accepts `.json` / `.jsonl` / `.csv`. While idle: a one-line explanation of the row shape Maya needs to provide ("each row: case_id, fault_class, prompt, expected, source — JSONL or CSV"). The drop zone must show the four state variants of S-7 (upload-failed) clearly.

**S-4. Dataset detail view header.** Title row + kind chip + count + last-updated + source URL when applicable + CTA cluster (Use in new audit · Download JSON · Download CSV · Delete-when-uploaded). The header must read differently across the three kinds — battery shows "source: HarmBench v1 / View in Phoenix ↗" prominently; regression shows the "auto-populated from N audits of <agent>" banner; uploaded shows "uploaded YYYY-MM-DD by you" and the delete affordance.

**S-5. Dataset rows table.** Paginated 50 rows per page. Columns: case_id (mono short slug) · fault_class chip (reuse the existing 4-class chip vocabulary already in the audit chamber) · prompt (truncated, expandable on click) · expected · source · severity (low/medium/high — only present for battery and uploaded-with-severity; absent rows show a `—`). The expanded-prompt treatment matters: prompts can be 5-300 words and contain quoted strings — clear monospace block with copy affordance.

**S-6. Wizard dataset combobox.** Inside `/new` §3b. Single combobox grouped by kind (battery / your uploaded / regression). Each row shows the dataset name + row count. Below the combobox once a selection is made: the "audit will run 8 standard probes + N rows from `<name>`" copy. Designer call on whether the combobox is a vanilla select, a popover with grouped sections, or a typeahead — but it must show the kind chip per row so Maya knows what she's picking.

**S-7. Upload validation error panel.** When the server rejects the upload (e.g. row 17 missing fault_class, row 23 unknown fault_class value, missing required column, JSON parse error at line N), the affordance must:

- Be inline (NOT a toast that disappears) — attached to or directly under the upload card
- List the specific row(s) and the specific reason
- Include the raw row JSON when available so Maya can find it in her source file
- Stay visible until she retries (success) or dismisses it explicitly
- Make the difference clear between "your whole file is malformed" (JSON parse error) and "your file is well-formed but rows 17, 23 are invalid" — these are different fixes

**S-8. Regression set "auto-populated" banner.** Top of a regression dataset detail page. Must communicate: this came from N finished audits of a specific agent, on specific timestamps, capped at the most-recent 200 rows. Include a deep-link back to the agent detail page and to the most recent audit that contributed rows. This is the closest the product gets to "showing the evidence chain" — it should read as **provenance**, not as a "where did this come from?" mystery.

**S-9. "Re-audit with this set" CTA.** Two placements share one visual treatment: the regression detail header and the agent detail page. The button text varies — on the agent detail it reads "Run regression on `regression-<slug>` (N rows)"; on the dataset detail it reads "Re-audit with this set." Both deep-link into the same `/new?dataset=<id>&agent=<agent_id>` URL. Designer treatment must work when N is 0 (no rows yet — disabled with an explanatory tooltip) and when N is large (200, the cap).

**S-10. Signed report cover — dataset reference.** Already in the existing report design as the `Dataset:` line on the cover (designed but stubbed with the framework name). This story populates it with the real dataset name. When the audit ran against a dataset, the cover MUST also include the dataset's `source_url` (when applicable) so the regulator can see exactly which corpus of test cases Phoenix Audit drew from. Designer call on the exact wording — but the line must be unambiguous about which dataset is which kind (battery vs. uploaded vs. regression).

**S-11. Delete-uploaded confirmation modal.** Standard destructive-action modal with one important nuance: the body copy must clearly say "Finished audit reports that referenced this dataset KEEP their signed PDFs and stay valid evidence. You will lose the ability to re-run with this set." Don't bury the survival of the artifacts — that's the regulator's question.

### Behavior notes for the designer

- The listing page loads server-side; the row count per dataset is in the listing payload (no separate fetch). The detail page also loads server-side; the row table is rendered from the same payload (no infinite scroll — 50/page client pagination is sufficient at the 200-row regression cap).
- Battery datasets never go away. New ones can be added in future product versions. The 3 we ship at launch are `harmbench-v1-sample`, `owasp-llm-top10`, `mitre-atlas-min` — designer can use the names verbatim.
- Regression datasets always tie to a target agent. If the agent is deleted, the regression dataset is also deleted (cascade). Designer doesn't need to design the cascade interaction — but the dataset detail view's banner needs to handle "agent no longer exists" gracefully (rare; the cascade should normally prevent it, but a stale view is possible).
- Uploaded datasets are scoped per-user. Even within the same organization, my uploads are not visible to you. (This is a known limitation we'll lift later. Don't design org-shared uploads.)
- Every dataset has a stable `dataset_id` slug used in URLs (`/datasets/<id>`). Battery slugs are well-known; regression slugs are `regression-<agent_slug>`; uploaded slugs are auto-generated short hex (`ds_a1b2c3`).
- Pagination of the rows table is client-side on the already-loaded payload. The dataset detail page caps at 200 rows server-side (matches the regression cap), so we never paginate over network requests. The 50-per-page client pagination is for visual digestibility, not for fetching.
- The wizard combobox lists every dataset the user can see — battery + their uploaded + every regression set across every agent they own. There is intentionally no "filter by agent" affordance on the combobox; Maya can already pick the dataset she wants by name. The grouped-by-kind layout is the only structural organization.

---

## Story-9.19 — Mobile responsiveness (Surface M)

**What ships:** every public + product surface usable at 390×844 (iPhone 14 class). This is responsive execution on EXISTING designer surfaces — no new visual language; the system you own stays intact. The one genuinely new component is the mobile nav.

### M-1 — MobileNav (hamburger + drawer)

- Replaces the inline `topbar.tsx` nav (Audits / Target agents / Monitoring / Settings) and `landing-nav.tsx` links at ≤768px. Wordmark stays left; "Run audit" CTA stays visible (it is THE product action — never buried in the drawer); UserMenu + nav links move into the drawer.
- Designer owns: the hamburger glyph idiom (the product's mono/etched register, not a stock icon), drawer surface treatment (full-height right sheet vs top drop — your call), open/close motion (Framer Motion 12 available), active-route treatment inside the drawer, and how the signed-in identity renders in drawer context.
- Constraints: drawer must be dismissible by backdrop tap + Escape; focus-trapped while open; nav targets ≥44px tall.

### M-2 — Chamber single-column

- `audit-chamber.tsx` grid `'390px 1fr'` → single column at ≤768px: probe rail stacks ABOVE the live event feed (the rail is the demo's heartbeat — it leads). Designer call: whether the rail collapses to a horizontal scroller or stays a full vertical stack.

### M-3 — Landing compare + typography pass

- `compare.tsx` 1fr/1fr grid stacks; the `borderRight` hairline becomes a `borderBottom`.
- ≤390px: display-type scale steps down (the 36–44px display sizes overflow); mono metadata rows wrap with intent rather than truncate.

### Verification

- Playwright at 390×844 across landing / replay / login / audits / chamber / report / datasets — screenshots land in the PR for your review pass.
