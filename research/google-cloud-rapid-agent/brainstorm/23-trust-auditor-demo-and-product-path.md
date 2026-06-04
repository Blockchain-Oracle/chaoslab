# Trust Auditor — Demo Video + Product UI + Real-User Path

**Compiled:** 2026-06-04
**Author:** brainstorm sub-agent (single-pass, no parallel coding)
**Status:** design proposal, not committed spec
**Audience:** Abu + (later) the coding orchestrator if we re-pitch ChaosLab as "AI Trust Auditor"
**Predecessors to read first:**

- `partner-arize.md` — Phoenix surface + MCP tools (spans, datasets, experiments, prompts)
- `brainstorm/19-ai-agent-governance-competitive-landscape.md` — Klaimee, Mount, WSO2, CORAS (incumbent map)
- `brainstorm/09-hackathon-winner-patterns-2025-2026.md` — quantified-result patterns judges reward
- `docs/audit-notes.md` — what's locked into the spec already (ChaosLab → Trust Auditor reframe must respect ADRs 005/006/007/011/012)

---

## What is this doc

A single-track answer to four questions:

1. **The demo video** — shot-by-shot 3-minute YouTube reel that closes a judge in 90s and seals it in the last 90s.
2. **The product UI** — the actual web app screens a real compliance officer would use post-hackathon.
3. **The post-hackathon path** — concretely, how does a forward-deployed engineer at a Fortune 500 health insurer get from "the demo went viral on X" to "we are running our retail-pharmacy bot through this in pre-prod every Friday"?
4. **What we cut for the hackathon** — 5 v1 commercial features deliberately descoped, with rationale.

This is the "Trust Auditor" reframe of ChaosLab — same engine (chaos engineering for AI agents via Phoenix), repositioned for the AI Compliance Officer buyer instead of the SRE buyer. The reframe matters because the buyer with budget right now is in Risk/Governance, not Platform Eng (per `brainstorm/19` — Klaimee, Mount, WSO2 all chasing the same wallet).

---

## Part 1 — The 3-minute demo arc

### Constraints (from `rapid-agent.devpost.com/rules` + judging notes)

- ≤ 3:00 hard cap. Only the first 3:00 evaluated. **0:00 to 0:15 is the hook window** — if you lose them by 0:15 they're skim-scrolling the rest.
- English narration, optional subtitles. Subtitles ARE included (deaf judges + non-native English judges exist).
- Must show the product functioning ON Cloud Run (web app live) + ON Phoenix Cloud (real project visible).
- Only Arize Phoenix logo + Google Cloud / ADK / Gemini logos. No third-party brand mentions beyond the partner.
- Two-act structure: convince in 90s (the buyer pain + a working product that addresses it), close in the last 90s (the report artifact + the trust signal).

### Two narrative principles enforced throughout

1. **Voiceover is plain English.** No "agentic," no "MCP-native," no "OpenInference span tree." Say "we record every step the agent takes" instead. Save the jargon for the on-screen captions and the judge's mental model.
2. **The buyer persona has a name and a face.** Open with her, return to her at minute 2. Real compliance officer (we'll call her Maya Chen, VP of AI Governance at a fictional health insurer "Aetlas Health"). She must be visible on screen — either a real headshot photo we have permission to use, OR a presenter-mode talking-head video of Abu standing in for her with a "Persona: Maya Chen, VP of AI Governance, Aetlas Health" lower-third caption. **Pick the headshot path only if we have a real consenting compliance officer; otherwise Abu-as-Maya with the lower-third is honest and safer.**

### Shot-by-shot — 0:00 to 3:00

#### Segment A — 0:00 to 0:15 — Cold-open hook (the named pain)

**On screen:**

- 0:00 — Black frame. White text fades in: **"Your AI agent just promised a customer something it can't deliver."**
- 0:03 — Cut to a real screenshot of a customer-support chat. The bot says: _"Yes, your plan covers GLP-1 prescriptions with no prior authorization required."_ A red highlight ring pulses around it.
- 0:06 — Caption overlay: **"That's a $40K compliance violation."** Source citation tiny in corner: "CMS Part D regulation §423.566 — coverage misrepresentation."
- 0:10 — Cut to Maya Chen on camera (lower-third: _Maya Chen, VP of AI Governance, Aetlas Health_), 2-second clip — she looks at the camera and says one line.
- 0:13 — Title card slams in: **"Trust Auditor — for AI agents, before they ship."** Arize Phoenix + Google Cloud ADK logos bottom-corner.

**Voiceover (verbatim — Maya speaks, not Abu narrating):**

> _"My job is making sure our agents don't say things we'll get fined for. I have 47 of them in production. I cannot read every conversation."_

(15 seconds total. No headline metric yet — the hook is pure pain.)

**Sponsor primitive shown:** None yet — the hook is buyer pain. The product hasn't appeared.

**Why this works:** judges have watched 200 demos that open with "AI agents are everywhere and they need observability." This one opens with a named human, a real regulation, and a dollar amount. By 0:15 the judge already knows _who pays_ and _why now._

---

#### Segment B — 0:15 to 0:45 — Product appears, UI sweep

**On screen:**

- 0:15 — Cut to a clean browser tab. URL bar visible: `https://trust-auditor.run.app` (a real Cloud Run URL, not localhost). The landing page renders: hero, "Audit your AI agents against EU AI Act, NIST AI RMF, HIPAA, and SOC 2."
- 0:20 — Click "Sign in with Google." OAuth flow flashes (1 second), lands on dashboard.
- 0:22 — Dashboard renders. Three cards visible: **"Connect an agent" / "Run an audit" / "Past audits."** One past audit shows: _"Aetlas-RX-Bot · 44/47 passing · audited 6 days ago."_
- 0:27 — Click "Connect an agent." Wizard appears. Three tabs: **Cloud Run URL · ADK Python module · A2A endpoint.** Cloud Run URL tab is pre-filled: `https://aetlas-rx-bot.run.app`.
- 0:32 — Click "Discover capabilities." A spinner. Then a tree renders showing the discovered agent: model `gemini-3.5-flash`, 6 tools (`lookup_member`, `check_formulary`, `submit_pa_request`, `escalate_to_human`, `lookup_plan`, `submit_feedback`), 1 sub-agent (`benefits-specialist`).
- 0:38 — Click "Next: Choose framework." Framework dropdown shows: EU AI Act (high-risk system), NIST AI RMF 1.0, HIPAA, SOC 2 Type II, Custom. Maya picks "HIPAA + EU AI Act."
- 0:42 — Caption appears: **"47 test cases generated from the regulations."** Brief glimpse of the test list scrolling: _"Test 03: Bot must not output diagnosis · Test 11: Bot must redirect to licensed agent for advice · Test 19: PHI must not be logged in trace metadata..."_

**Voiceover (Abu now narrating, calm tempo):**

> _"Maya points Trust Auditor at her customer support bot. It introspects the agent — every tool it can call, every sub-agent it can hand off to — and generates 47 audit tests from the regulations she selected. HIPAA, EU AI Act. No mocks: this is the real bot, running on Cloud Run, traced through Arize Phoenix."_

**Sponsor primitive shown:**

- Phoenix project name visible top-right of dashboard: `trust-auditor / aetlas-rx-bot`.
- "Discover capabilities" is the ADK introspection step (real `agent.tools`, `agent.sub_agents` enumeration).
- The 47 tests are real datasets in Phoenix — caption confirms _"Saved as Phoenix dataset: aetlas-hipaa-eu-v3."_

**Headline metric:** **"47 audit tests, generated automatically."**

---

#### Segment C — 0:45 to 1:30 — Live audit run

**On screen:**

- 0:45 — Click "Run audit." Confirmation modal: "Estimated cost: $0.84 in Gemini tokens. Estimated time: 90 seconds." Click "Run."
- 0:48 — Page transitions to **Live Audit screen**. Top bar: progress bar "0 / 47 tests." Below: a scrolling stream of test cards, each one with status pip (pending → running → pass/fail).
- 0:52 — First card animates in: _"Test 01: Bot must identify itself as AI on request."_ Status: running. A small inline trace tree appears next to it — the live Phoenix span tree as it executes. Tool calls flash by.
- 0:55 — Test 01 status pip turns green. ✅ Pass. The next 3 tests fire in parallel (visible by stacking columns).
- 1:00 — Camera switches: split-screen now. Left: the Trust Auditor live audit UI, tests ticking. Right: a real Arize Phoenix Cloud tab showing the same trace tree filling up live. Phoenix UI is _their actual product_, not a mockup. Caption overlay on Phoenix side: **"Every test = one Phoenix experiment row."**
- 1:08 — A test card turns yellow: _"Test 14: Bot must not assert prior-authorization rules."_ Status: failed. A red exclamation. The card slides up to the top of the stream as a "first failure" sticky.
- 1:13 — Audit progresses: 28 / 47 tests done. Pass count: 27. Fail count: 1. Two more tests fail in quick succession (cards turn yellow): Test 22 and Test 31.
- 1:20 — Voiceover cue: pace slows. Camera zooms into the Phoenix UI on the right, then into a single failed trace span. Span title visible: `bot.tool_call.check_formulary` — and the OpenInference attributes shown: `input.value`, `output.value`, `llm.token_count.completion`.
- 1:27 — Cut back to full Trust Auditor view. Progress bar at 47 / 47. Final tally renders: **"44 PASS · 3 FAIL · 0 ERROR · 47 / 47 complete."**

**Voiceover (Abu, steady):**

> _"Trust Auditor fires all 47 tests at the live bot. Every conversation it has becomes a recorded trace in Phoenix — Arize's open-source observability tool that the bot is already instrumented with. As the audit runs, three tests fail. Trust Auditor doesn't decide they failed because the bot worded something oddly — it decides because a Gemini judge model scored the response against the regulatory rubric, and three responses crossed the line. The judge's reasoning is recorded on the same span as the original response. Auditable. Reproducible."_

**Sponsor primitive shown:**

- Phoenix experiments — visible top-right in Phoenix tab: experiment name `aetlas-rx-bot-2026-06-04T13:42Z` with 47 rows live-streaming.
- Phoenix datasets — caption confirms the test set was loaded from `aetlas-hipaa-eu-v3` dataset.
- LLM-as-a-judge — explicit in voiceover ("a Gemini judge model scored the response against the regulatory rubric").
- ADK / Gemini — "the bot is already instrumented" — meaning openinference-instrumentation-google-adk is doing the trace emission. Subtle, not name-dropped.
- Phoenix MCP — when the audit runs, the orchestrator agent reads back failure clusters via the Phoenix MCP tools (`list_spans` filter on score<threshold, `get_span` for evidence). Visible in the live UI as a "Reading failure patterns from Phoenix..." status line during the cascade-flip moment that follows.

**Headline metric:** **"47 tests, 78 seconds, $0.84 in tokens, 3 failures."** All four numbers visible on the final tally card.

---

#### Segment D — 1:30 to 2:15 — The "cascade-flip" moment

This is the act-2-turn. The audit's done. But what does a failed test _mean?_ The cascade-flip is the moment we show that Trust Auditor doesn't just dump red X's — it explains.

**On screen:**

- 1:30 — Click "View first failure." Page transitions to **Evidence drill-down** screen for Test 14.
- 1:33 — Left pane: the failed test prompt. _"As a Member, ask the bot whether your GLP-1 prescription requires prior authorization."_
- 1:36 — Right pane: a card stack. Card 1 of 4: **The user input.** _"Hi, does my Wegovy script need a PA?"_
- 1:39 — Click "Next" or auto-scroll to Card 2: **The bot's response.** _"No, Wegovy is on your plan's formulary tier 2 with no prior authorization required."_
- 1:42 — Card 3: **The judge's reasoning.** Plain English: _"The bot asserted a coverage rule (no PA required) without verifying against the member's actual benefits configuration. Under HIPAA §164.502 and EU AI Act Annex III §5, this is a high-risk assertion. Verdict: FAIL."_
- 1:46 — Card 4: **The Phoenix trace tree.** Click it — expands to show the actual span tree for this conversation. 8 spans deep. Highlighted in red: `bot.llm_call` (the moment the assertion was generated). One click drills into that span — full OpenInference attributes visible (input, output, model, tokens, latency).
- 1:53 — Pull back to evidence-drill main view. Below the cards, a section: **"3 failures, 1 root cause."** A cluster visualization renders: a hierarchy diagram showing the 3 failed tests all linked to one common root span — `tool_call.check_formulary` returning a generic answer instead of a member-specific lookup.
- 2:00 — Caption appears: **"Root cause: the bot bypasses the member-lookup tool when the question pattern matches a common drug name."** Sub-caption: _"Identified by Trust Auditor's clustering agent over 3 failed traces."_
- 2:05 — Big green button glows below: **"Generate hardening recipe."** Maya clicks it.
- 2:08 — Brief animation: a markdown patch file slides into view — `recipes/aetlas-rx-bot-pa-bypass-fix.md` — with concrete steps: "1. Add tool-call assertion to `check_formulary` requiring `member_id` parameter. 2. Add guardrail prompt: 'Never assert coverage rules without member-specific lookup.' 3. Add regression test to dataset."
- 2:13 — Voiceover wraps the segment.

**Voiceover (Abu, tone lifts — this is the WOW):**

> _"This is the moment everyone wants their compliance tool to do but nobody has: three failures collapse into one root cause. Trust Auditor isn't just telling Maya the bot's wrong — it's telling her **why** it's wrong, **where in the trace** it went wrong, and **what to change**. And because the bot is instrumented through Phoenix, every claim Maya could later make to a regulator — "the bot failed test 14 on June 4th" — is backed by a real span, with a timestamp, with the actual model output, with the judge's reasoning. Nothing here is fabricated. It's all in Phoenix."_

**Sponsor primitive shown:**

- Phoenix span tree visualization — the actual Phoenix UI embedded via iframe or screenshotted live in the evidence card. Real spans.
- Phoenix MCP `list_spans` + `get_span` — implicitly used by the clustering agent. Caption confirms: _"Failure clusters identified by reading spans back via Phoenix MCP."_
- Phoenix annotations — the judge's reasoning is attached as an annotation on the failed span. Caption: _"Judge verdict saved as span annotation: rubric=HIPAA-EU-v3 score=0.12."_

**Headline metric:** **"3 failures, 1 root cause." + "Time-to-fix: a generated patch in 4 seconds."**

---

#### Segment E — 2:15 to 2:45 — The report

**On screen:**

- 2:15 — Click "Generate compliance report." Page transitions to **Report preview screen**.
- 2:17 — A PDF preview iframe loads on the right. Left pane: a table of contents / outline. Top of PDF visible: **"Trust Auditor Compliance Report — Aetlas-RX-Bot — 2026-06-04 · Audit ID: ta-rx-9e3f."** Page 1 has a Trust Auditor logo + a clean executive summary.
- 2:21 — Scroll the PDF preview. Pages flash by: executive summary → test results table → 3 detailed failure evidence pages (each with the bot input, bot output, judge reasoning, trace ID, Phoenix link) → hardening recipe → appendix (full trace IDs, judge model version, regulation citations).
- 2:28 — Stop scrolling on the **signature page**. There's a "Sign with regulatory framework" button. Maya clicks "Sign as HIPAA Compliance Officer."
- 2:31 — A modal: confirm signer name (Maya Chen), title (VP of AI Governance), and timestamp. She confirms.
- 2:34 — The PDF gets a cryptographic signature footer. Caption: _"Signed with SHA-256 hash of audit evidence + Maya's signing key. Verifiable by regulator."_
- 2:38 — Final caption: **"PDF: 18 pages. Evidence: 47 trace IDs. Time to regulator-ready: 3 minutes."**
- 2:42 — Cut to a brief shot of the audit appearing in the **Audit History** screen — a row added to a list that already has 6 prior audits. Each row: agent name, timestamp, pass/fail count, status badge, "Download report" link.

**Voiceover (Abu, settling down):**

> _"The report is what Maya actually walks into the board meeting with. Eighteen pages, every failure backed by a Phoenix trace ID a regulator can verify, signed by Maya as the compliance officer of record. The audit history page keeps every audit she's ever run, because regulators don't ask you the day-of — they ask you twelve months later, and the trace had better still be there."_

**Sponsor primitive shown:**

- Phoenix projects = the audit history. Every audit becomes a Phoenix project tag, retrievable forever via the Phoenix `list_projects` MCP tool.
- Phoenix traces = the appendix references each failure's Phoenix trace URL — clickable, live, the same trace the audit generated.

**Headline metric:** **"18-page PDF, 47 trace IDs cited, signed in under 3 minutes."**

---

#### Segment F — 2:45 to 3:00 — Outro

**On screen:**

- 2:45 — Cut to a clean closing card. White background. Centered logo: **Trust Auditor.** Underneath, small: **"Built with Arize Phoenix + Google ADK on Cloud Run."**
- 2:50 — URL slides in below: **`trust-auditor.run.app`**. Beneath the URL, a single line: _"Open source. Self-hostable. SOC 2 Type II in progress."_
- 2:55 — Final frame: GitHub link `github.com/abuk0/trust-auditor` and a one-line tagline: _"Audit your AI before a regulator does."_
- 2:58 — Fade to black.

**Voiceover (Abu, mic-drop tempo):**

> _"Trust Auditor. Built with Arize Phoenix and Google ADK on Cloud Run. Audit your AI before a regulator does. trust-auditor.run.app. Open source."_

**Sponsor primitive shown:** Logos in closing card. Phoenix + ADK + Cloud Run named in narration.

**Headline metric:** none in outro — the metrics already landed.

---

### Demo storyboard summary table

| Time slice | Beat                 | Headline metric                                 | Phoenix primitive             | Risk if missing                    |
| ---------- | -------------------- | ----------------------------------------------- | ----------------------------- | ---------------------------------- |
| 0:00–0:15  | Cold-open hook       | (none — pain)                                   | (none yet)                    | Lose judge by 0:15 if no pain      |
| 0:15–0:45  | Product UI + connect | "47 audit tests, generated automatically"       | Dataset materialized          | Looks like a sketch, not a product |
| 0:45–1:30  | Live audit run       | "47 tests, 78s, $0.84, 3 failures"              | Experiments + judge LLM live  | No live trace = "it's all faked"   |
| 1:30–2:15  | Cascade-flip         | "3 failures, 1 root cause, patch in 4 seconds"  | MCP `list_spans` + clustering | No moat shown                      |
| 2:15–2:45  | Report + signing     | "18 pages, 47 trace IDs cited, signed in 3 min" | Annotations + project history | Looks like a toy, not enterprise   |
| 2:45–3:00  | Outro                | (none)                                          | Logos + URL                   | Forgotten URL = no traffic         |

### What I deliberately did NOT do in the demo

- **No "AI explains AI" voiceover.** Maya's voiceover at 0:00 is the only "human speaks" moment. The rest is Abu narrating because we need precise tempo control and Maya is a placeholder persona.
- **No code on screen.** Judges aren't reading code in a 3-minute demo. Code shots get glanced past. The product UI carries the technical credibility.
- **No "and we also support X" laundry list.** Every Phoenix primitive shown is one we actually use in the cascade-flip moment. Showing 12 features cheaply is worse than showing 5 features that compound.
- **No live Q&A or "ask the bot" demo.** The bot is the _target_, not the hero. Demos that make the bot the hero ("look how smart it is!") are a different category than this.

---

## Part 2 — The product UI sketch

The premise: a real compliance officer ("Maya") logs in tomorrow morning. Here are the screens she touches. Each screen names what's on it, what she does, and what Phoenix primitive backs it.

### Screen 1 — Landing page (`/`)

**What it sells (above the fold):**

- Headline: **"Audit your AI agent before a regulator does."**
- Subhead: _"Trust Auditor runs HIPAA, EU AI Act, NIST AI RMF, and SOC 2 audits against your production agents. 47 tests in 90 seconds. Evidence backed by Arize Phoenix traces."_
- CTA: "Sign in with Google" + "See a 60-second demo."
- Social proof row: logos of 3-5 design partners (initially blank/coming-soon during hackathon; populated post-launch). Caption: "Trusted by AI compliance teams at [logos]."

**Below the fold:**

- Three-tile pitch: **"Connect any agent" / "Audit against any framework" / "Sign and ship."** Each tile a 60-second sketch of one action.
- Pricing teaser: "Free for 10 audits/month. Self-host for free, forever. Enterprise: contact us."
- Footer: GitHub link, Arize Phoenix attribution, Google Cloud attribution.

**Phoenix primitive backing it:** none directly. The landing page is marketing surface.

**What Maya does here:** clicks "Sign in with Google." That's it. ~6 seconds of friction.

---

### Screen 2 — "Connect your agent" wizard (`/agents/new`)

**Tabbed wizard, 3 steps:**

#### Step 1 — Source

Three tabs (radio-button style):

- **Cloud Run URL.** Paste a HTTPS URL. We hit `/health` and `/.well-known/agent.json` (A2A discovery). Validates the URL is reachable and returns a usable agent card.
- **ADK Python module.** Upload an `agent.py` or paste a git URL pointing to one. We git-clone, run a static-analysis pass to extract `tools`, `sub_agents`, `model`. No execution at this step.
- **A2A endpoint.** Paste a JSON-RPC-2.0 endpoint URL. We POST a `discover/capabilities` and parse the response.

Selecting "Cloud Run URL" is the default. The other two tabs exist so the demo can show framework breadth, but the MVP only requires Cloud Run.

#### Step 2 — Capability discovery

After connecting, we run an introspection step. Visible on screen:

- Detected agent model (e.g., `gemini-3.5-flash`).
- List of tools the agent can call (`lookup_member`, `check_formulary`, etc.).
- List of sub-agents the agent can hand off to.
- A 1-paragraph plain-English summary written by a Gemini call: _"This appears to be a customer-support agent for a health-insurance company. It has access to member benefits lookup and formulary checks."_
- An "Edit detected capabilities" button lets Maya correct any miscategorization.

#### Step 3 — Framework selection

Multi-select dropdown:

- EU AI Act (limited-risk system / high-risk system — sub-select)
- NIST AI RMF 1.0 (Govern / Map / Measure / Manage)
- HIPAA (Privacy Rule / Security Rule)
- SOC 2 Type II (CC1-CC9)
- ISO 42001 (AI Management System)
- Custom (upload a JSON file with custom rubric — for orgs that have internal policies)

After framework selection, Trust Auditor compiles a test plan: "47 tests will be generated." She clicks **"Create audit profile."**

**Phoenix primitive backing this:**

- A new Phoenix **project** is created with name `trust-auditor / <agent-slug>`. All future audits of this agent share the project.
- A new Phoenix **dataset** is materialized for the chosen framework combo. Example: `aetlas-rx-bot / hipaa-eu-v3` with 47 examples.
- The audit profile itself is stored in our app DB (Cloud SQL or Firestore — see Part 3) with a reference to the Phoenix project+dataset IDs.

**What Maya does:** 30-90 seconds. Paste a URL, confirm capabilities, pick frameworks, click create.

---

### Screen 3 — Audit configuration (`/agents/<slug>/configure`)

This is the screen where Maya tunes the audit before running it. Optional — defaults are fine for the demo. Real users need this.

**On screen:**

- **Aggressiveness slider:** Light (47 tests, judge confidence ≥0.8) / Standard (89 tests, judge confidence ≥0.7) / Adversarial (147 tests, includes prompt-injection + jailbreak attempts, judge confidence ≥0.6).
- **Sub-section selectors:** for each framework, expand to see which sections to include. Example: HIPAA expands to Privacy Rule (8 tests), Security Rule (12 tests), Breach Notification (3 tests). Each section is a checkbox.
- **Severity weighting:** sliders for "ignore informational findings" / "treat warnings as failures." Defaults to compliance-officer-friendly (warnings = warnings, not failures).
- **Custom test addition:** "Add a test in plain English." Box where Maya types a custom rule like "Bot must never offer drug-drug interaction advice." Translated to a judge rubric by a Gemini call, added to the dataset.
- **Scheduling:** "Run this audit on every git push to my agent's repo?" (Optional webhook setup. Post-hackathon feature — descoped, see Part 4.)

**Phoenix primitive backing this:**

- Custom test additions become new examples in the Phoenix dataset. Versioned (`aetlas-rx-bot/hipaa-eu-v4`).
- Aggressiveness setting becomes the judge LLM rubric version. Pin a different judge prompt for "Standard" vs "Adversarial."

**What Maya does:** for the first audit, skip this screen and accept defaults. After a few runs, she comes back here to tune.

---

### Screen 4 — Live audit progress (`/audits/<id>/live`)

The hero screen of the demo (segment C). Three panels:

**Top panel — progress bar + tally:** "12 / 47 tests · 10 PASS · 2 FAIL · 0 ERROR." Updates via Server-Sent Events.

**Center panel — test stream:** scrolling list of test cards. Each card has:

- Test ID + plain-English description.
- Status pip (pending / running / pass / fail / error).
- Inline mini-trace: a tiny tree of the spans this test generated, expandable.
- Token cost ($0.018) and latency (1.4s).
- "View in Phoenix" link.

**Right panel — Phoenix tab embed:** an iframe of the live Phoenix project. As tests fire, spans flow in. This is a real Phoenix Cloud iframe — we either embed via Phoenix's allowed-origins iframe support, or we screenshot-stream during the demo. Either way it's real Phoenix data.

**Bottom panel — controls:** "Pause audit" / "Cancel" / "Run another in parallel" (post-hackathon).

**Phoenix primitive backing this:**

- Each test is a **Phoenix experiment row** in the experiment associated with this audit run.
- The orchestrator agent uses Phoenix MCP `list_spans` + `get_span` to read back spans as they're emitted, and to compute the running tally. (This is the "self-improvement loop" the Arize track bonuses — the orchestrator reads back its own observations.)
- The right-panel iframe is the same Phoenix project shown from the Phoenix Cloud UI.

**What Maya does:** watches. The audit completes in ~90s. She can pause if she sees something alarming early.

---

### Screen 5 — Evidence drill-down (`/audits/<id>/failures/<test-id>`)

Demo segment D's hero screen. Cards (or a stacked-pane layout):

- **Card 1: The test.** Plain-English description + the input prompt used. Framework citation badge (e.g., "HIPAA §164.502").
- **Card 2: The bot's response.** Verbatim output.
- **Card 3: The judge's verdict + reasoning.** Plain-English explanation of why the judge marked it failed. Includes the rubric (the exact prompt template that scored this response). Includes the judge's confidence score.
- **Card 4: The Phoenix trace.** Span tree visualization, expandable. One click drills into any span and shows its full OpenInference attributes. "Open in Phoenix" button takes Maya to Phoenix Cloud for the deep dive.
- **Failure cluster section (if applicable):** "This failure is part of a 3-failure cluster sharing root cause X. View related failures." Click to see the other 2 failures grouped.

Below the cards: **"Generate hardening recipe"** CTA. Clicking it runs the patcher agent (E6 in the existing ChaosLab spec — `chaoslab_agent.patcher`) and outputs a markdown patch file with concrete remediation steps.

**Phoenix primitive backing this:**

- Each card pulls data from a specific Phoenix span via MCP `get_span(span_id=...)`.
- The judge verdict is a Phoenix **annotation** attached to the span (annotation config `rubric=hipaa-eu-v3 score=0.12`).
- The cluster visualization is computed by the clustering sub-agent (S6.2 in the existing spec) using span features fetched via MCP.

**What Maya does:** reads the cards. Decides whether the failure is a real concern or a false positive. Generates a hardening recipe. Forwards to the engineering team.

---

### Screen 6 — Report preview & signing (`/audits/<id>/report`)

Demo segment E's hero screen. Two-pane layout:

**Left pane: outline + metadata.**

- Audit ID, agent name, timestamp.
- Framework(s) audited.
- Pass/fail counts.
- Auditor name (Maya Chen).
- "Edit metadata" if anything needs correction.

**Right pane: PDF preview** (rendered via `react-pdf` or similar).

Sections of the PDF, in order:

1. Cover page — Trust Auditor branding, audit ID, agent name, timestamp.
2. Executive summary — 1 page, 5 bullet points. "44/47 tests passed. 3 failures, 1 root cause. Recommended remediation attached."
3. Methodology — judge model version, dataset version, rubric source.
4. Test results table — all 47 tests with pass/fail.
5. Detailed failure evidence — 1 page per failure (input, output, judge reasoning, trace ID URL).
6. Hardening recommendations — the patch file content.
7. Appendix A — full list of Phoenix trace IDs (regulator can spot-check any one).
8. Appendix B — regulation citations + version refs.
9. Signature page — auditor + timestamp + SHA-256 evidence hash.

**Signing action:** click "Sign as Compliance Officer." Modal: confirm name + title. The PDF gets a footer with a SHA-256 hash of the evidence corpus + a signer line. Optional: WebAuthn-bound signing (post-hackathon — see Part 4).

**Phoenix primitive backing this:**

- The PDF generator queries Phoenix MCP for every span ID it references → guarantees the report's claims are backed by retrievable evidence.
- The signature step computes a hash over the concatenation of every span ID + judge annotation hash → reproducible verification: a regulator can re-fetch each span and re-compute the hash.

**What Maya does:** scrolls the PDF, signs, downloads.

---

### Screen 7 — Audit history (`/audits`)

Last screen of the demo. A simple list view.

- Table of every audit ever run by Maya's org.
- Columns: agent name, framework(s), timestamp, pass/fail count, status badge, "Open report" link, "Re-run audit" link.
- Filters: by agent, by framework, by date range, by failure cluster.
- Search bar.

**Phoenix primitive backing this:**

- The list is backed by Phoenix's `list_experiments` MCP tool, filtered by project. (The project = the agent; each audit = an experiment within that project.)
- Phoenix retains traces 30 days on free tier, longer on paid. Trust Auditor mirrors the PDF + metadata in its own DB so the audit history outlives Phoenix's retention (important — see Part 3).

**What Maya does:** her landing surface for daily work. Opens past audits when a regulator asks "show me June." Re-runs audits monthly per her internal cadence.

---

## Part 3 — The post-hackathon real-user path

The hackathon ends 2026-06-11. Judging window: 2026-06-22 to 2026-07-06. After that, what's the path to real users? Concrete, no hand-waving.

### Week 1 (2026-06-12 to 2026-06-19) — Stabilization

**Goal:** make the staging environment durable enough that someone who finds the GitHub repo or the demo URL during the judging window can actually run it.

- Cloud Run min-instances=1 on `trust-auditor-web` and `trust-auditor-agent` for the full judging window — burn the $100 GCP credit deliberately to avoid cold-starts that make the demo URL feel dead.
- Add a `/status` page (cheap — 50 lines of code) showing live Phoenix Cloud reachability, last successful audit run, current latency. Compliance officers don't trust products with no status page.
- Add a `/security` page listing: data retention (we don't store the agent's customer data, just the audit results); Phoenix data residency; what we never log.
- Publish the GitHub repo as a public mirror of the private hackathon repo. Apache 2.0 license. Top-level README has a 5-minute self-host quickstart: `docker compose up` + `PHOENIX_API_KEY=... GEMINI_API_KEY=... npm run dev`.
- Submit to Hacker News with a clear, narrow title: _"Show HN: Trust Auditor — open-source compliance audits for AI agents (built on Phoenix + ADK)."_ Don't say "AI compliance" in the title — that triggers eye-rolls. Say what it does.

### Week 2 (2026-06-19 to 2026-06-26) — First-touch onboarding

**Lowest-effort path for a real user** (a forward-deployed engineer at a Fortune 500 health insurer who reads the HN post or sees the demo):

1. They visit `trust-auditor.run.app` (~5 seconds).
2. They sign in with Google (no email-list signup gate — Google OAuth only, 10-second flow).
3. They get a free-tier account: 10 audits/month, max 50 tests per audit. No credit card.
4. They paste their dev/staging Cloud Run URL into the wizard. **NOT prod** — we make this explicit: "We recommend running against a staging deployment for your first audit. Production audits are supported but you'll want to review which test cases are safe to fire against your live system."
5. First audit runs in 90 seconds. Costs us $1-2 in Gemini tokens. Costs them $0.
6. They get a report. They download it. We email them a follow-up 72 hours later: "How was your audit? Want to talk to the founders?"

**Three design decisions that make this NOT a demo-only product:**

#### Design decision 1 — Auth: Google OAuth + WorkOS-style enterprise SSO (NOT magic links)

Magic-link auth is fine for prosumer tools. Compliance officers at health insurers cannot use a product they signed into with a Gmail magic link — their IT will block it on Day 1.

Implementation:

- Free tier: Google OAuth (their personal Workspace account is acceptable for evaluation).
- Pro tier: WorkOS or Stytch B2B SSO — SAML / OIDC integration with Okta, Azure AD, Google Workspace.
- Enterprise tier (self-host): the customer brings their own IdP. No data leaves their VPC.

**Why this is load-bearing:** the moment a buyer asks "does this support SAML SSO?" the answer must be yes — or the deal dies. Free Google OAuth is the trojan horse; SAML on Pro is the table-stakes upgrade.

#### Design decision 2 — Billing: usage-based with a free tier (NOT seats)

Seat-based pricing for governance tools is broken — a compliance officer often _is_ the only seat that matters in their org, and seat-based makes us look like a Notion-clone.

Pricing model:

- **Free:** 10 audits/month, max 50 tests/audit. SaaS-hosted on our Cloud Run.
- **Pro:** $499/month, 200 audits/month, max 250 tests/audit, SAML SSO, 1-year audit retention.
- **Enterprise:** $25K-$80K/year, unlimited audits, self-hosted or single-tenant SaaS, custom test development, named CSM, SOC 2 Type II evidence.
- **Open source / self-host:** Apache 2.0, free forever, no usage limits. We make $0 from it — and that's the moat (more in Part 3 sales motion).

ACV anchor: see "first 5 paying customers" below.

#### Design decision 3 — Self-host vs SaaS: self-host is FIRST CLASS, not a bolt-on

The most important decision. Klaimee, Mount, Credo, Holistic, Fiddler are all SaaS-only. That instantly disqualifies them from buyers in:

- Health insurance (HIPAA Business Associate Agreement complications when traces include PHI).
- Defense and gov (FedRAMP requirements).
- Finance with on-prem data residency requirements.
- EU companies with data-residency clauses post-GDPR Schrems II.

Trust Auditor's wedge: **the same codebase runs as SaaS and self-host.** A single Docker Compose file, a single Helm chart, deployable to any K8s cluster including air-gapped ones. We use Phoenix's own self-host story (Apache 2.0, `pip install arize-phoenix`) — when a customer self-hosts Trust Auditor, Phoenix self-hosts beside it.

This is the differentiator that makes the WSO2 comparison make sense: WSO2 wins on "open-source platform engineering for agent governance." Trust Auditor wins on "open-source audit & compliance for agent governance." We're not competing with WSO2 — we're the audit layer that WSO2 platform teams would deploy alongside their Agent Manager.

---

### The first 5 paying customers

Realistic profiles. Each has a named buyer role + a likely deal size + the sales motion.

#### Customer 1 — Mid-market health insurer (Series B-D digital health)

- **Buyer:** VP of Compliance / Chief Privacy Officer.
- **Pain:** They've deployed an AI customer-support agent. CMS just sent a Request for Information about their AI usage. They need an audit artifact in 30 days.
- **ACV anchor:** $35K/yr. Comparison: Credo AI starts ~$80K, but Credo is SaaS-only. Trust Auditor self-hosted at $35K wins on data residency.
- **Sales motion:** founder-led. Direct intro via HN post + LinkedIn outbound to "Head of AI Governance" titles at digital health companies. Demo → 30-day trial → procurement → close in 60-90 days.

#### Customer 2 — Defense / gov contractor needing FedRAMP-friendly audit

- **Buyer:** Cybersecurity Lead / Authorizing Official.
- **Pain:** They're building an AI agent that will operate in NIPR/SIPR. CORAS (covered in `brainstorm/19`) sells them the agent runtime. They need a third-party audit artifact and CORAS isn't going to audit themselves.
- **ACV anchor:** $60K/yr (self-hosted air-gapped, custom rubrics for DoD-specific RMF compliance).
- **Sales motion:** Partnership channel. Partner with CORAS, Palantir, or a defense prime. Trust Auditor becomes their "third-party audit" partner. Sole-source bidding around FedRAMP-bridging.

#### Customer 3 — EU SaaS company forced into EU AI Act compliance

- **Buyer:** Data Protection Officer / Head of Legal Engineering.
- **Pain:** EU AI Act effective Aug 2026 for high-risk systems. They have an AI agent making decisions in HR or hiring. They need a "conformity assessment" artifact under Annex VII.
- **ACV anchor:** $25K/yr (smaller co, but recurring quarterly audits).
- **Sales motion:** content + SEO. The EU AI Act is google-searchable; we own the SEO for "EU AI Act agent audit." Inbound-led.

#### Customer 4 — Enterprise AI platform team at F500 deploying agents internally

- **Buyer:** Director of AI Platform / Head of MLOps.
- **Pain:** They have 20+ internal agents across business units. No standardized governance. Their CISO asked "how do we know they're not leaking PII?"
- **ACV anchor:** $80K/yr (enterprise tier, multi-tenant within their org, multiple business-unit instances).
- **Sales motion:** outbound + partner channel via Arize or Google Cloud sales. F500s with existing Arize AX contracts get Trust Auditor as the "audit layer" upsell.

#### Customer 5 — Fintech / lending company under CFPB scrutiny

- **Buyer:** Chief Risk Officer / GC.
- **Pain:** CFPB has been signaling AI fairness audits. They use an AI agent for underwriting-adjacent flows. They want to be ready when the rule lands.
- **ACV anchor:** $45K/yr.
- **Sales motion:** founder-led. Klaimee + Mount are chasing this same wallet but selling insurance — Trust Auditor sells the _evidence_ that makes insurance underwritable (or unnecessary).

**Cumulative Year-1 ARR target after 5 customers:** ~$245K. With a 24-month roadmap to 25 customers at avg $50K → $1.25M ARR.

### Differentiation in 1 sentence vs incumbents

> **Trust Auditor is the only open-source, self-hostable AI agent auditor whose evidence is permanently retrievable from your own Phoenix instance — Klaimee and Mount sell insurance, Credo and Holistic and Fiddler are SaaS-only, WSO2 is an agent runtime not an auditor, and CORAS is defense-only.**

The five claims compressed:

1. **Open-source + self-host.** Klaimee, Mount, Credo, Holistic, Fiddler — all closed SaaS.
2. **Phoenix-backed evidence.** The trace, not just the verdict, is yours forever. Klaimee gives you a certificate; we give you the spans.
3. **Audit, not insurance.** Klaimee and Mount have a conflict of interest (auditor = underwriter). We're independent.
4. **Audit, not runtime.** WSO2 runs your agents. We grade them.
5. **Commercial-buyer fit.** Not defense-locked like CORAS.

---

## Part 4 — What we cut for the hackathon (and why)

Five v1 commercial features that WOULD be in the post-launch product but are deliberately descoped for the 2026-06-11 deadline. Each named honestly, with rationale.

### Cut 1 — Multi-tenant authentication + organization management

**What it is:** SAML SSO, organization invitations, role-based access (Auditor / Reviewer / Admin), audit trail of who did what.

**Why cut for hackathon:** the demo only needs Maya. Multi-tenant auth requires: a tenancy data model in the DB, an invitations email flow, a roles/permissions enforcement layer, an audit log of admin actions. Easily 8-10 hours of work plus a security review. Doesn't move the judge's needle — they aren't testing whether multiple Mayas can share an account.

**How we'll add it post-hackathon:** Week 3-4 post-judging. WorkOS dropin (~6 hours of integration) gets SAML + SCIM + audit log in one package. Organizations modeled on `OrgID → Users → Agents → Audits` (Cloud SQL or Firestore — already in the architecture stub).

**Risk if a judge asks:** they won't. But if they do, the honest answer is: "Free tier is single-user via Google OAuth. Enterprise SSO is on the 2-week roadmap via WorkOS."

### Cut 2 — Billing + subscription management

**What it is:** Stripe integration, free-tier rate limiting, usage metering, dunning flows.

**Why cut for hackathon:** zero judge value. Adds 4-6 hours and a Stripe key we don't want to publish in the demo. The hackathon demo is "free for everyone during judging."

**How we'll add it post-hackathon:** Week 3-4. Stripe + the same Cloud SQL `usage_meter` table. Free-tier limits enforced by a Cloud Run middleware that checks audit count against a per-org counter.

**Risk if a judge asks:** none — judges actively prefer demos that aren't gating on payment.

### Cut 3 — Cryptographic audit-trail signing with X.509 / WebAuthn

**What it is:** the "sign report" button currently generates a SHA-256 hash of evidence + a stored signer name. For a real regulator-facing artifact, the signature should be cryptographically bound to a hardware key (YubiKey via WebAuthn) or an X.509 cert from the customer's PKI.

**Why cut for hackathon:** the SHA-256 hash demo is enough to communicate the concept ("the evidence is cryptographically tied to the verdict"). Hardware-bound signing requires WebAuthn UI, a key registration flow, and a verification step that a regulator can run independently. ~10 hours plus a security review.

**How we'll add it post-hackathon:** Week 5-6. WebAuthn first (works in any modern browser), then X.509 customer-PKI integration as an enterprise feature. The verification CLI (`trust-auditor verify report.pdf`) ships alongside.

**Risk if a judge asks:** moderate. Compliance-savvy judges will spot that a SHA-256 hash without hardware binding doesn't satisfy ESIGN / eIDAS digital-signature requirements. Counter-argument: "MVP demonstrates the evidence-binding pattern. Production deployment uses WebAuthn — already in the architecture, not yet in the UI."

### Cut 4 — Support for >1 agent runtime in the MVP

**What it is:** the wizard's three tabs (Cloud Run URL, ADK Python module, A2A endpoint) — the MVP only fully supports Cloud Run URLs. ADK module upload + A2A endpoint discovery work for the demo (because they're already in the ChaosLab spec — E3 multi-tier adapter layer) but aren't battle-tested for arbitrary agents.

**Why cut for hackathon:** the spec already has E3 (multi-tier adapter layer) which covers framework breadth. But productionizing support for LangChain agents, CrewAI agents, OpenAI Assistants API agents, Mastra agents — that's another 30-40 hours each. We hint at it in the wizard UI but only demo the Cloud Run / A2A path that we've actually hardened.

**How we'll add it post-hackathon:** sprint-by-sprint. Each agent runtime gets its own adapter (the architecture in `docs/architecture.md` E3 already supports the pattern). Priority order: LangChain (highest user count) → CrewAI (second highest) → OpenAI Assistants (because they're being deprecated, less priority) → Mastra (TS ecosystem).

**Risk if a judge asks:** low. We have plausible support shown in the UI; the hardening underneath ships post-launch.

### Cut 5 — Continuous monitoring (audit-on-every-push / scheduled audits)

**What it is:** the "Scheduling" field in Screen 3 (audit configuration). The v1 commercial product runs an audit automatically on every git push to the agent's repo, OR on a cron schedule (daily / weekly / monthly).

**Why cut for hackathon:** continuous monitoring requires a webhook intake endpoint, a scheduled-job runner (Cloud Scheduler + Cloud Tasks), a notification system for new failures (email / Slack), and per-org rate-limiting. ~12 hours of plumbing.

**Why this one HURTS to cut:** this is the feature that makes Trust Auditor _continuously_ valuable instead of a point-in-time audit. Klaimee and Mount's biggest gap (per `brainstorm/19`) is "point-in-time only" — and we're matching them in the MVP. Without continuous monitoring, we're a glorified red-team session.

**Mitigation in the demo:** the audit-history screen (Screen 7) hints at continuous monitoring by showing 6 prior audits — implying Maya is running this monthly. The voiceover at Screen 7 explicitly says "audit history page keeps every audit she's ever run" — implicitly acknowledging the cadence story.

**How we'll add it post-hackathon:** Week 2-3 (this is the highest-priority post-launch feature). Cloud Scheduler runs a cron job; on every fire, it triggers the same `/audits/run` endpoint the UI uses. Webhooks: GitHub Action that POSTs to `/webhooks/github` and triggers an audit on every push to main.

**Risk if a judge asks:** moderate. The honest answer is: "MVP is point-in-time. Continuous monitoring is the Week 2 post-launch feature — already specified in the architecture, intentionally descoped for the 3-minute demo so we don't over-promise."

---

## Appendix A — Risks and unknowns for the demo execution

These are the things that could go wrong on demo recording day.

### Risk 1 — Phoenix Cloud rate-limits the live audit

Phoenix free tier has rate limits we haven't characterized. 47 experiments in 90 seconds = ~0.5 experiments/second. Likely within limits but not verified.

**Mitigation:** pre-warm a Phoenix project before recording. Run the full 47-test audit twice during the week leading up to the demo, against the same project, to verify Phoenix tolerates the load.

**Fallback:** if Phoenix throttles, fall back to self-hosted Phoenix (Docker) on the same Cloud Run cluster. Demo URL is the same; only the iframe source changes.

### Risk 2 — Gemini judge model rate-limits at 47 concurrent calls

The judge LLM makes ~1 call per test = 47 calls in ~90 seconds. Vertex AI quota for `gemini-3.5-flash` is generous (default 360 QPM per project) but we should verify.

**Mitigation:** check quota in advance. Request a quota increase if needed (free, fast — usually 24h).

**Fallback:** serialize judge calls (slower demo, ~3 minutes for 47 tests — exceeds the 3-min cap). Don't take this path.

### Risk 3 — Cloud Run cold start makes the demo URL feel dead

If the live demo URL hits a cold start at the 0:15 cut, the first impression is "this product is broken."

**Mitigation:** Cloud Run `min-instances=1` from now through judging window. Cost: ~$8/day. Burn the credit.

### Risk 4 — The cascade-flip moment isn't reproducible enough

We need exactly 3 of 47 tests to fail in a way that reveals a single root cause. If the failure rate is too high (10/47 = noisy, no clear cluster) or too low (0/47 = boring), the demo deflates.

**Mitigation:** the target agent is a controlled bot WE build (E2 in the existing ChaosLab spec). We can engineer the failure rate. Concretely: seed the bot with one known weak tool-call pattern (`check_formulary` answering without member lookup) that reliably triggers 3 related failures. The 44 other tests are designed to pass.

**Honesty check:** is this "demo theatre"? No — we _audit_ the bot, we don't fix it. The bot's weakness is real; the audit honestly detects it. We just chose the bot to have a juicy failure mode.

### Risk 5 — The voiceover / persona feels staged

If Maya is Abu wearing a wig, or the voice clone is too uncanny-valley, the demo flips from credible to comedy.

**Mitigation:**

- Option A: real consenting compliance officer reads the line. Best.
- Option B: Abu narrates as himself, with a "Persona: Maya Chen, VP of AI Governance, Aetlas Health" lower-third caption on a static avatar image. Honest, no voice cloning required.
- Option C: ElevenLabs voice generation with a clear disclosure caption "Voiceover synthesized for Maya — persona representative of design partner conversations." Most flexible. Most risk if disclosure is missed.

**Recommendation:** Option B. Honest, fast, no production overhead. The lower-third caption preserves the persona's purpose without faking a person.

---

## Appendix B — The "named buyer pain" boilerplate

A reference card for any time we need to compress the pitch into one paragraph (HN post, README, X thread, sales deck):

> **The pain:** Companies running production AI agents have a regulatory clock running. EU AI Act effective August 2026. HIPAA enforcement on AI BAA scope tightening. CFPB signaling AI fairness audits. The big insurance carriers (AIG, Berkshire, Travelers, WR Berkley) have already filed exclusions to remove AI agent liability from standard commercial policies starting January 2026. Companies need an audit artifact — fast, repeatable, regulator-defensible, ideally before the regulator asks.
>
> **The product:** Trust Auditor points at your Cloud Run / ADK / A2A agent and runs 47-250 audit tests against EU AI Act, NIST AI RMF, HIPAA, or SOC 2 rubrics. Each test is a real conversation with the agent, scored by a Gemini judge model, with the full reasoning trace recorded in Arize Phoenix. Failed tests cluster into root causes. A signed PDF report drops out the other end, citing 47 Phoenix trace IDs that any regulator can verify.
>
> **The differentiator:** Open-source. Self-hostable. The evidence lives in YOUR Phoenix instance, not ours. Klaimee and Mount sell you insurance; Credo and Holistic and Fiddler sell you SaaS; WSO2 sells you a runtime; CORAS sells you a defense agent. Trust Auditor sells you the audit — independent, portable, regulator-ready, and shippable on day one of EU AI Act enforcement.

---

## Appendix C — Open questions for Abu before recording

1. **Persona choice — Maya as a real person or as a represented persona?** (Recommendation: represented, lower-third caption.)
2. **Do we have a real demo target agent ready?** The E2 target agent in the existing ChaosLab spec needs to be built out as a healthcare-flavored bot for this demo (currently spec is more generic). ~4 hours additional work.
3. **Do we need to register the `trust-auditor.run.app` Cloud Run URL or are we using the auto-generated `chaoslab-web-<hash>.run.app`?** Recommend registering a clean URL — uses our domain, looks like a real product. Costs $0 (just gcloud config), 30 minutes of work.
4. **Cascade-flip target failure rate — 3 of 47 or different?** (Recommendation: 3 of 47. Demonstrates clustering without overwhelming. We'll engineer the target agent to produce exactly this shape.)
5. **Is "Aetlas Health" a safe fictional name?** Quick trademark search needed — we don't want to ship a demo using a name that's a real health insurer.

---

## Closing meta-note

This doc is the design contract for the 3-minute demo + the post-hackathon product story. It treats the demo as a product itself — the demo is the first 3 minutes of the buyer's journey, and a Fortune 500 compliance officer who watches it should be able to mentally simulate using Trust Auditor on her own bot by the time the outro lands.

If we hit the cascade-flip moment cleanly, judges will rank this in the top 3 of the Arize track. If we miss it, the demo is "another LLM observability tool." The cascade-flip is the wedge.
