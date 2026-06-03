# Story — README + LICENSE + NOTICE

**ID:** story-8.1-readme-license-notice
**Epic:** Epic 8 — README + Submission polish
**Depends on:** Should run AFTER all other epics (E1–E7) complete; technically stands alone but the demo URL it embeds requires Cloud Run deploys (E2.4 + E4.6 + E7) to exist
**Estimate:** ~1h
**Status:** PENDING

**Tags:** `[docs, p0, submission]`

---

## User story

**As a** Stage-1 Devpost automated screener AND a Stage-2 human judge (Arize / Google DevRel) opening the public repo cold,
**I want to** see (in this exact order) project name + one-line pitch → hosted demo URL → the cascade-flip hero screenshot → 3-command local run → cross-framework target matrix → Apache-2.0 license link, plus a discoverable LICENSE file and a NOTICE file that attributes the vendored `deepankarm/agent-chaos` primitives,
**So that** the §13 README-shape gate, the §14 vendoring-attribution gate, and the Apache-2.0 open-source detection check all pass on first scan and the human judge gets the entire ChaosLab story above the README fold before clicking anything

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `README.md` — UPDATE — rewrites the story-1.1 skeleton README into the final 6-section judging-grade artifact per `docs/PRD.md` §"README shape (§13 — required ordering)". Sections in order: (1) `# ChaosLab` H1 + one-line pitch (verbatim from `docs/PRD.md`: "ChaosLab — adversarial resilience testing for AI agents. Inject 4 fault classes, watch them fail, harden automatically."); (2) "## Demo" section with a single bullet `**Live demo:** https://chaoslab-web-<hash>-uc.a.run.app` (the Cloud Run URL from `infra/cloud-run-deploy.sh` output; story-1.1 leaves a `TBD` placeholder that this story replaces); (3) hero asset block — `![ChaosLab cascade-flip moment](apps/chaoslab-web/public/og-hero.png)` (story-8.3 lands the PNG; this story references the path); (4) "## Run locally in 3 commands" code block: `uv sync && pnpm install && make dev`; (5) "## Cross-framework target support" — a 4-row Markdown table (header + 3 tiers per `docs/architecture.md` ADR-002): Tier 1 ADK native | Tier 2 LangChain/CrewAI/OpenAI Agents SDK via OpenInference | Tier 3 HTTP black-box with AgentCard discovery; (6) "## License" section linking `LICENSE` and naming Apache-2.0, with a sub-bullet pointing at `NOTICE` for vendoring attribution. Total target ≤200 lines.
- `LICENSE` — UPDATE — verbatim Apache License Version 2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt` (story-1.1 already created this file; verify identical content; if not, overwrite with canonical text). First line MUST be `                                 Apache License`.
- `NOTICE` — UPDATE — adds the vendoring attribution block. Content:

  ```
  ChaosLab for Agents
  Copyright 2026 Abu Mostofa

  This product includes software developed by third parties:

  - deepankarm/agent-chaos (https://github.com/deepankarm/agent-chaos)
    Apache License 2.0
    Fault primitive library — copied into apps/chaoslab-agent/src/chaoslab_agent/injector/faults/_vendored/

  - Google Agent Development Kit (https://github.com/google/agent-development-kit)
    Apache License 2.0
    Multi-agent orchestration framework

  - Arize Phoenix (https://github.com/Arize-ai/phoenix)
    Elastic License 2.0
    LLM observability + evaluation substrate

  - GitLab MCP Server (https://gitlab.com/api/v4/mcp)
    MIT License (gitlab-org/gitlab)
    Official partner MCP endpoint used by the Patcher sub-agent for MR emission

  Thanks to Phoenix (Arize), GitLab DevRel, and Google Cloud Partner Engineering for the SDK access and partner-MCP endpoints used in this hackathon submission.
  ```

  Story-1.1 left this file with just the copyright header — this story extends it. Total ≤80 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given README.md exists at repo root
When `grep -E "^# ChaosLab" README.md` runs
Then exit 0 (project name H1 present)

Given README.md exists
When `grep -cE "(Live demo|Demo)" README.md` runs
Then output ≥ 1 (demo URL section present per §13.2)

Given README.md exists
When `grep -E "run.app|TBD" README.md` runs
Then exit 0 (a Cloud Run URL or explicit TBD placeholder is present — no naked localhost)
And `grep -E "localhost|127.0.0.1" README.md` returns nothing (anti-pattern from §13)

Given README.md exists
When `grep -E "og-hero.png" README.md` runs
Then exit 0 (hero screenshot referenced — story-8.3 lands the file)

Given README.md exists
When `grep -E "(uv sync|pnpm install|make dev)" README.md | wc -l` runs
Then output ≥ 3 (3-command local run present per §13.4)

Given README.md exists
When `grep -cE "(Tier 1|Tier 2|Tier 3)" README.md` runs
Then output ≥ 3 (cross-framework matrix present per §13.5)

Given README.md exists
When `grep -E "(Apache-2.0|Apache 2.0|Apache License)" README.md` runs
Then exit 0 (license attribution present per §13.6)

Given README.md exists
When `grep -E "(Demo|Run locally|License)" README.md` runs (the gate from the story brief)
Then exit 0

Given LICENSE exists at repo root
When `head -1 LICENSE` runs
Then output contains "Apache License"
And `grep -c "Version 2.0" LICENSE` returns ≥ 1
And `wc -l < LICENSE` returns ≥ 200 (verbatim Apache-2.0 is ~202 lines)

Given NOTICE exists at repo root
When `grep "deepankarm/agent-chaos" NOTICE` runs
Then exit 0 (vendoring attribution from the story brief gate)
And `grep -E "(ADK|Agent Development Kit)" NOTICE` returns exit 0
And `grep "Phoenix" NOTICE` returns exit 0
And `grep -E "GitLab.*MCP" NOTICE` returns exit 0

Given the three files exist
When `wc -l README.md NOTICE | awk '{print $1}'` runs
Then no value exceeds 400 (ADR-010 compliance; LICENSE is excluded by check_max_lines.py allowlist as vendored canonical text)
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# All three files present
test -f README.md
test -f LICENSE
test -f NOTICE

# README §13 ordering — sections appear in correct order
grep -n "^# ChaosLab" README.md
grep -n "^## Demo" README.md
grep -n "og-hero.png" README.md
grep -n "^## Run locally" README.md
grep -n "^## Cross-framework" README.md
grep -n "^## License" README.md

# Story-brief gate (verbatim from instructions)
grep -E "(Demo|Run locally|License)" README.md

# No localhost contamination
! grep -E "localhost|127.0.0.1" README.md

# LICENSE is canonical Apache-2.0
head -1 LICENSE | grep -q "Apache License"
grep -q "Version 2.0" LICENSE
[ "$(wc -l < LICENSE)" -ge 200 ]

# NOTICE has all 4 attributions
grep -q "deepankarm/agent-chaos" NOTICE
grep -qE "(ADK|Agent Development Kit)" NOTICE
grep -q "Phoenix" NOTICE
grep -qE "GitLab.*MCP" NOTICE

# Line count compliance (README + NOTICE only; LICENSE excluded per ADR-010)
[ "$(wc -l < README.md)" -le 400 ]
[ "$(wc -l < NOTICE)" -le 400 ]

# 400-line script doesn't trip
python3 scripts/check_max_lines.py --strict

echo "story-8.1 verification: PASS"
```

---

## Notes for coding agent

- The demo URL gets filled in from `gcloud run services describe chaoslab-web --region=us-central1 --format='value(status.url)'`. If the Cloud Run service isn't deployed yet, leave a `TBD — staging deploy pending` placeholder — the §13.2 gate still passes if the placeholder is explicit.
- Do NOT use any other Apache-2.0 text variant — judges' automated repo scanners check for the exact canonical wording from `apache.org/licenses/LICENSE-2.0.txt`. Story-1.1 should already have this; this story verifies + extends.
- The README hero screenshot reference `![...](apps/chaoslab-web/public/og-hero.png)` is RELATIVE — GitHub renders it correctly because the PNG lives in the repo. Do NOT use an absolute Cloud Run URL here (slows page load + breaks if Cloud Run is down).
- The 4-row Tier table must reference the actual adapter files from `docs/architecture.md` repo structure (`adk_adapter.py`, `langchain_adapter.py`, `crewai_adapter.py`, `openai_sdk_adapter.py`, `http_blackbox_adapter.py`) — link them as relative GitHub paths so judges can click through.
- The NOTICE attribution for Phoenix lists "Elastic License 2.0" — that IS the actual Phoenix license (Arize-ai/phoenix repo). Do not paraphrase it as Apache-2.0; Stage-1 scanners may flag the discrepancy.
- The cross-framework table is the ONLY place ChaosLab's market-gap moat (per `context/03 §13`) is communicated in the README — make it punchy, 1-line summaries per tier.
- `make dev` is the canonical 3-command end (from story-1.1's Makefile). If story-1.1's Makefile doesn't include a `dev` target, that's a story-1.1 bug to flag — do NOT invent the target here.
- This story is a DOCS-only PR. No source code, no tests added. The §14 mock-scan exempts docs files by default; verify the README has no `mock`/`fake`/`dummy` strings that could trip a naive scanner.
