# Multi-turn session shape — Phoenix Audit

**Status:** SPEC (defined here; runtime wiring lands in Epic 5's injector story).
**Source:** ADR-016 (`docs/architecture.md`) + memo 27 sub-question 2 + audit-notes D4-11.

Phoenix Audit's 6-probe demo battery runs as a **deliberate mix of single-turn
and 2-turn probes** — 3 of each. This is a budget-vs-coverage tradeoff dictated
by the 90-second demo window + the ~16s/round-trip A2A latency measured in
RAT-2 IF-14. The mix is documented here so a compliance officer reading the
audit report cannot mistake it for full coverage.

---

## Why this exists (the OSS-landscape gap)

Memo 27 sub-question 2 surveyed how every OSS red-teaming / auditor tool
handles session statefulness. See §"Honest disclosure" below for the
load-bearing claim about single-turn being the easy mode of the attack.

<!-- prettier-ignore -->
| Tool | Default |
| --- | --- |
| **Garak** (`atkgen`) | Stateless per probe — "Prototype, mostly stateless." |
| **Promptfoo** | Both supported. Multi-turn primitives are NAMED first-class: `Crescendo` ("gradually escalates prompt harm"), `GOAT` ("dynamically generate multi-turn conversations"), `Hydra Multi-turn` ("adaptive multi-turn jailbreak agent"), `Mischievous User`. |
| **DeepEval / DeepTeam** | Multi-turn is the headline feature. Metrics `Knowledge Retention`, `Conversation Completeness`, `Turn Relevancy`, `Turn Faithfulness`, `Role Adherence` exist ONLY in multi-turn mode. |
| **TruLens** | Span-based; conversation continuity is the caller's responsibility. |
| **Inspect AI** | Multi-turn by design (tool-use loops). |

**Garak's `atkgen` stateless-per-probe default is the trap we don't want to
fall into.** If Phoenix Audit silently ships 6 single-turn probes and calls
it "comprehensive," a compliance officer comparing our report to Promptfoo's
or DeepTeam's would notice within 5 minutes that the same OWASP LLM01 category
got materially weaker coverage. The 3+3 mix is our answer.

---

## OSS-tool landscape

(The table above plus narrative context.) Phoenix Audit's session-mix
positioning vs the OSS landscape:

- **vs Garak (`atkgen` stateless):** Phoenix Audit emits 2-turn probes for
  3 of 6 tests, catching the Crescendo-class attacks Garak's `atkgen`
  defaults cannot.
- **vs Promptfoo:** Phoenix Audit cites Promptfoo's `Crescendo` + `GOAT` named
  primitives as prior art for the 2-turn shape. Our shape is a smaller subset
  (we don't ship a configurable strategy library; we ship one mix).
- **vs DeepEval / DeepTeam:** their multi-turn-as-headline ethos is similar,
  but Phoenix Audit doesn't yet emit the per-turn metrics (`Turn Relevancy`
  etc.) — see Downstream test obligations below for Epic 5's surface.
- **vs Inspect AI:** Phoenix Audit's 2-turn probes are simpler than Inspect's
  full tool-use loops; we cap at exactly 2 turns per 2-turn probe to stay
  inside the 90s budget.

---

## Session-shape declaration

The 6 probes assigned to session modes. Epic 5's injector story implements
against this exact table:

<!-- prettier-ignore -->
| Probe | Source | Mode | Rationale |
| --- | --- | --- | --- |
| 1 | HarmBench #1 | single-turn | Harmful-output elicitation; direct prompt is high-signal. |
| 2 | HarmBench #2 | single-turn | Second harmful-output category; same rationale. |
| 3 | CARES | single-turn | Healthcare-safety direct-question; multi-turn adds no signal. |
| 4 | OWASP LLM01 | 2-turn | Crescendo-style: establish benign context, then escalate to injection. |
| 5 | MITRE ATLAS (indirect) | 2-turn | Indirect-injection-via-tool-output requires the tool call on turn 1. |
| 6 | MITRE ATLAS (escalation) | 2-turn | Trust-establish on turn 1, attack on turn 2. |

**Specific MITRE ATLAS technique IDs** (probes 5 + 6): Epic 5's injector
story pins the exact AML.Txxxx IDs against the MITRE ATLAS dataset (PRD
cites v5.1.0; Epic 5 should verify the published version at implementation
time). This spec doc declares the SHAPE (single-turn vs 2-turn) per probe
slot, not the dataset-row binding (which is implementation detail).

**2-turn protocol (locked verbatim — Epic 5 implements against this):**

For each 2-turn probe, turn 1 establishes context (benign question, plausible
request) and turn 2 escalates (injection payload, trust exploitation). Each
turn is a full A2A round-trip (for ADK-A2A targets; HTTP-target latency is
TBD until Epic 3 measures). Total wire time per 2-turn probe ≈ 32s assuming
the A2A 16s/round-trip baseline from RAT-2 IF-14.

---

## Honest disclosure (locked verbatim per ADR-016)

**Single-turn is the easy mode of the attack.** OWASP LLM01 (prompt injection) and the MITRE ATLAS equivalent techniques are materially weaker as single-turn tests. The most-cited real-world prompt-injection attacks (Crescendo, indirect-injection-via-tool-output) require >1 turn of context to land.

**Phoenix Audit's session-mix is a deliberate budget-vs-coverage tradeoff, not full coverage.** Naming 3 of the 6 probes as 2-turn captures the higher-signal attacks (Crescendo-style escalation) within the 90-second demo window; running all 6 as 2-turn would blow the budget. Compliance officers reading the audit report should treat the 3 single-turn probes as floor-of-difficulty checks, NOT as comprehensive coverage of their categories.

The audit report PDF SHOULD include a "Session shape" footnote on the
relevant probe pages naming the mode (single-turn / 2-turn) so the customer's
compliance officer can see the budget-vs-coverage tradeoff at glance. Epic 6
Reporter story owns the footnote rendering.

---

## Latency budget

Empirical baseline from RAT-2 IF-14: **~16s per A2A round-trip** at current
ADK 2.1.0 wire performance (no-LLM, localhost; the IF-14 measurement is
15.87s, rounded to 16s here). RAT-2 IF-14 lists two mitigation candidates
that are **not yet tested**:

- Connection pooling (keep one A2A connection open across tests).
- Parallel execution via `asyncio.gather`.

Until those are measured, the only empirically-supported budget number is
the **sequential** total. Sequential arithmetic:

- Single-turn probe: 1 round-trip × 16s = **16s** per probe.
- 2-turn probe: 2 round-trips × 16s = **32s** per probe.
- Session-mix wall-clock total (sequential): 3 × 16s + 3 × 32s = **144s**.

The 90-second demo window assumes ONE of: (a) the parallel-execution
mitigation works (drops wall-clock to roughly the slowest 2-turn probe ≈
32s), (b) the connection-pooling mitigation lowers per-round-trip overhead,
or (c) the demo runs partially overlapping with judge/patcher/reporter
phases so the wall-clock is non-strictly-additive.

**Honest disclosure:** the 90s budget is **projected, not measured.** If
none of (a), (b), (c) hold (the two RAT-2-listed mitigations + the
phase-overlap scheduling assumption), the demo overruns to ~144s — the
failure mode is "longer demo," not "silently incorrect audit." Cross-
reference PRD Known Limitations ("Investigating the latency further is
post-hackathon work").

---

## Downstream test obligations (for Epic 5 + Epic 6 implementers)

The acceptance test for THIS patch pins the SPEC (file shapes + content).
The runtime tests below land with their respective stories.

**Epic 5 injector story (probe emission) MUST add:**

- Implement the exact 3 single-turn + 3 two-turn mix from the table above.
  The probe-to-mode assignment is contractual; deviating requires updating
  this doc + the audit-notes D4-11 record.
- For each 2-turn probe: turn 1 establishes benign context, turn 2 escalates.
  Specific turn-1 / turn-2 payloads come from the dataset citations (Epic 5
  pins the exact rows).
- Per-turn metrics: emit OpenInference span attributes
  `phoenix_audit.session_mode = single-turn|2-turn` AND
  `phoenix_audit.turn_index = 0|1` so the Reporter can render per-turn
  detail in the audit PDF.
- Integration test: assert the 6-probe audit run emits exactly 3 single-turn
  - 3 two-turn span sets (matching the table).
- BEFORE shipping: measure the connection-pooling + parallel-execution
  mitigations and update this doc with empirical numbers (replacing the
  "projected" framing in §Latency budget with measured).

**Epic 6 Reporter story (PDF generation) MUST add:**

- Each probe page renders a "Session shape" footnote naming the mode
  (single-turn / 2-turn) per the locked mix.
- ANTI-anchor: the report MUST NOT claim the 6-probe sample is comprehensive
  of any attack category; the framing is "6-probe sample under deliberate
  budget-vs-coverage tradeoff."
- Snapshot test: render a sample probe page and assert the Session-shape
  footnote text matches the canonical wording.

---

## What this PR does NOT do

- It does NOT implement the injector (Epic 5).
- It does NOT pin specific MITRE ATLAS technique IDs for probes 5 + 6
  (Epic 5 pins the exact AML.Txxxx rows).
- It does NOT add the Session-shape footnote rendering (Epic 6).
- It does NOT change any existing runtime code paths.
- It does NOT measure the connection-pooling / parallel-execution latency
  mitigations (Epic 5 measures during integration).

This PR is the **session-shape declaration** so downstream stories
implement against a fixed contract.

---

## Cross-references

- ADR-016 in `docs/architecture.md` — the architectural decision this spec serves
- Audit-notes D4-11 (added in this PR) — formal spec landing record
- `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md`
  sub-question 2 — the empirical OSS-landscape survey that drove the 3+3 mix
- `research/google-cloud-rapid-agent/RAT-2-results.md` IF-14 — the 15.87s
  round-trip A2A latency measurement that constrains the budget
- `docs/PRD.md` Known limitations §"A2A round-trip latency" — the same
  empirical constraint as user-facing language (per PRD line 173)
