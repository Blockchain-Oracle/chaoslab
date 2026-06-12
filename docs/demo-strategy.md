# Demo Strategy

---

## The Demo Narrative (locked)

**One-liner:** _"3 failures, 1 root cause, patch in 4 seconds."_

**Two-sentence pitch:**

> "On Friday we ran 6 adversarial tests. On Monday we ran the same scoring engine over live traffic. Here are both signed reports."

**Flow for non-developer judges / compliance officers:**

1. Click "Run Audit" → audit runs in ~90s
2. Attack Matrix shows live probe results (pass/fail per test)
3. Click any cell → opens signed report with cluster summary + hardening recipe
4. Click a span link in the report → Phoenix opens showing the raw agent conversation, the fault that was injected, and the judge's verdict written back as an annotation
5. **That's the blockchain-explorer moment** — fully verifiable evidence chain, not just a PDF

---

## Phoenix Sessions = The Explorer Moment (story-9.7)

Story-9.7 (current branch `story/phoenix-sessions`) is what creates this moment.

Without sessions: Phoenix shows a wall of ungrouped traces — confusing for a judge/regulator.

With `using_attributes(session_id=f"run_{run_id}")`:

- All spans from one audit (8 probes + judge + patcher) group under **one session ID**
- Phoenix Sessions tab shows the entire audit as a single narrative flow
- Anyone can land on that session URL and reconstruct exactly what happened, step by step

This is structurally identical to a blockchain explorer — one tx hash → all operations in sequence.

---

## What Arize Judges Are Screening For

These are the 4 auto-fail conditions (from research/partner-arize.md). We pass all four:

| Check                                         | Status                                           |
| --------------------------------------------- | ------------------------------------------------ |
| Phoenix used as dashboard only (no eval loop) | ✅ Run evals + write annotations back            |
| Fake/static traces                            | ✅ Real OpenInference spans, auto-instrumented   |
| Visual Agent Builder only                     | ✅ ADK native + Cloud Run                        |
| No actual MCP use                             | ✅ 27 read MCP tools + Python SDK write wrappers |

**Scoring dimensions (4 equal):**

1. Tech — Phoenix instrumentation + MCP + signed KMS report + self-improvement loop
2. Design — 16 designer surfaces
3. Potential Impact — Director of AI Governance at 5K+ company
4. Quality of Idea — only product with adversarial battery + judge-LLM + signed PDF combined

---

## Arize Tool Stack Summary (for telling judges)

| Tool                                       | Layer        | Used for                                                    |
| ------------------------------------------ | ------------ | ----------------------------------------------------------- |
| `openinference-instrumentation-google-adk` | Auto-tracing | Every ADK call captured automatically                       |
| Phoenix MCP (27 read tools)                | Read         | Judge reads existing trace spans                            |
| `run_experiment.py` custom FunctionTool    | Write        | Runs LLM-as-judge eval experiments (MCP has no write tools) |
| `write_annotation.py` custom FunctionTool  | Write        | Writes cluster IDs + verdicts back onto spans               |
| `using_attributes(session_id=...)`         | Grouping     | Groups all probes under one audit session                   |
| Named experiments `phoenix-audit-{run_id}` | Experiments  | Deep-linkable in Phoenix Experiments tab                    |
