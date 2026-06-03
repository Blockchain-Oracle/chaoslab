# 05 — BDD Acceptance Criteria + BMad Story Format

> **Methodology note:** Written directly after sub-agent retries hit Anthropic API "Overloaded" errors. Focused on the actually-load-bearing patterns for ChaosLab. Cross-reference `/Users/abu/.claude/skills/sahil-spec-writer/SKILL.md` and `/Users/abu/.claude/skills/sahil-hackathon-orchestrator/SKILL.md` for the literal target format.

---

## 1. BDD + Gherkin canonical format

Behavior-Driven Development scenarios use the **Given / When / Then** triad:

```gherkin
Feature: Fault injection for malformed tool output

  Background:
    Given a deliberately-naive customer-support agent is running
    And Phoenix Cloud is reachable
    And the target agent emits OpenInference traces

  Scenario: Injecting a malformed-tool-output fault causes the target to fail
    Given the target agent has 3 tools: lookup_order, refund, escalate
    When ChaosLab injects a malformed-output fault on the lookup_order tool
    And the target agent is invoked with "what's the status of order #1234"
    Then the target agent's response contains "error" or "unable"
    And a Phoenix span with status_code != OK appears within 30s
    And the span's attributes["tool_call.function.name"] equals "lookup_order"

  Scenario Outline: All four MVP fault classes produce visible failures
    Given the target agent is in baseline-naive configuration
    When ChaosLab injects a <fault> fault
    Then the target's pass rate drops below 50%
    And the Phoenix trace shows the <expected_signature>

    Examples:
      | fault                | expected_signature         |
      | malformed_tool_output | status_code=ERROR          |
      | prompt_injection     | unexpected_tool_call       |
      | context_poisoning    | groundedness_eval=0.0      |
      | latency_spike        | duration_ms > 30000        |
```

**Key constructs:**
- **Feature** — high-level capability
- **Background** — shared Given for all scenarios in the feature
- **Scenario** — one behavior
- **Scenario Outline + Examples** — parameterized scenarios (run N times with table rows)
- **Tags** (e.g., `@slow`, `@online`, `@integration`, `@p0`) — filter at execution time
- **And** / **But** — additional Given/When/Then steps
- One `When` per scenario is ideal; two is acceptable; three or more = split

Cite: https://cucumber.io/docs/gherkin/

---

## 2. Writing GOOD acceptance criteria

**Heuristics:**

| Bad | Good |
|---|---|
| "Then the system works" | "Then the response includes a `runId` field matching `^run_[a-z0-9]{12}$`" |
| "Then ChaosLab finishes" | "Then a Phoenix experiment with name `chaoslab-run-{runId}` exists with a non-empty `metrics.tool_invocation` field" |
| "Then the user sees the result" | "Then the page contains an element with `data-testid='attack-matrix'` containing exactly 25 children" |
| "Then performance is acceptable" | "Then the p95 response time is < 2000ms over 10 consecutive requests" |
| "Given the system is configured" | "Given the env vars `PHOENIX_API_KEY` and `AGENT_BACKEND_URL` are set" |

**The INVEST checklist** (Bill Wake) — every story should be:
- **I**ndependent — doesn't block-or-require sibling stories
- **N**egotiable — implementation isn't fixed
- **V**aluable — produces user-visible (or system-observable) value
- **E**stimable — work amount is knowable
- **S**mall — fits in a single PR (half-day to two-day)
- **T**estable — has falsifiable Then clauses

**Anti-patterns to ban:**
1. Implementation leakage in Given: ❌ "Given a Python function called `inject_fault`..." ✅ "Given ChaosLab is configured to inject malformed tool output"
2. Multi-behavior scenarios — split them
3. Brittle exact-string assertions — use regex or structural assertions
4. Coupled scenarios — never "Then save state X used by next scenario"
5. Vague time expressions — "soon", "fast", "responsive" — replace with concrete thresholds

---

## 3. BMad-Method overview

[BMad-Method](https://github.com/bmad-code-org/BMAD-METHOD) (Breakthrough Method for Agile AI-Driven Development) is the spec methodology `sahil-spec-writer` uses.

**The artifact pipeline:**
```
Brief → PRD → Architecture → UX Spec → Epics → Stories
                                       ↘
                                        Coding Agent (one story at a time)
```

**Agent personas in BMad:**
- **Analyst** — produces the Brief
- **PM (Product Manager)** — produces the PRD
- **Architect** — produces architecture.md
- **UX Expert** — produces ux-spec.md
- **Scrum Master** — produces epics and decomposes into stories
- **Dev** — implements one story per session
- **QA** — validates against acceptance criteria

For a hackathon, one human (Abu) + AI agents play all roles. `sahil-spec-writer` runs the SM persona to produce stories; `sahil-hackathon-orchestrator` runs the Dev persona via coding agents; `sahil-pr-audit` runs the QA persona.

**The key BMad principle:** "context-engineered stories" — each story file contains ALL the context a fresh-context coding agent needs to implement it. No tribal knowledge.

---

## 4. The BMad story file format

Each story lives at `docs/stories/story-<slug>.md`:

```markdown
---
id: STORY-007
title: ChaosLab injects malformed tool output into target ADK agent
status: ready          # one of: draft, ready, in-progress, review, done
priority: p0
estimate: 1d
epic: EPIC-002         # fault injection
tags: [backend, p0, parallel-safe]
blocks: [STORY-011]    # patcher generation depends on this
blocked-by: [STORY-003, STORY-004]  # target agent + Phoenix instrumentation
owner: null            # claimed by coding agent at start
---

# Story: ChaosLab injects malformed tool output into target ADK agent

## User Story
As a **ChaosLab orchestrator**,  
I want to **inject malformed tool output into a target agent's tool calls**,  
so that **the target's failure under bad tool data is observable in Phoenix traces**.

## Background

The target agent (deliberately-naive customer-support) has three tools: `lookup_order`,
`refund`, `escalate`. ChaosLab must wrap these tools with a decorator that, when the
fault is active, returns malformed JSON instead of the real result. The original tool
must remain untouched (we wrap, not patch).

The Injector is an in-process sub-agent of the orchestrator (per `architecture/03`).
The fault decorator must be configurable: which tool to corrupt, what kind of malformation
(invalid JSON, missing required field, type mismatch, exception).

Phoenix auto-instrumentation already wraps every tool call into a TOOL span. The
fault must surface in that span via `status_code` and `output.value`.

## Acceptance Criteria (Gherkin)

```gherkin
Background:
  Given the target ADK agent is running on Cloud Run at $TARGET_AGENT_URL
  And the agent emits OpenInference traces to Phoenix Cloud
  And ChaosLab can call the target via A2A (RemoteA2aAgent)

Scenario: Malformed JSON output causes target failure
  Given ChaosLab's malformed_tool_output fault is enabled for tool "lookup_order"
  And the malformation type is "invalid_json"
  When the target agent is invoked with prompt "what's the status of order #1234"
  Then the target's response contains "error" OR contains "unable to" OR has length < 20
  And within 30s a Phoenix TOOL span with name="lookup_order" appears
  And that span has status_code != OK
  And that span's output.value is not valid JSON

Scenario: Missing required field causes target to retry
  Given ChaosLab's malformed_tool_output fault is enabled for tool "lookup_order"
  And the malformation type is "missing_required_field"
  When the target agent is invoked
  Then the target makes between 1 and 3 retry attempts (visible as parallel tool spans)
  And the final response is graceful (contains "I couldn't" or "sorry")

Scenario: Fault is configurable per tool
  Given ChaosLab is running
  When the orchestrator sets fault target to "refund" instead of "lookup_order"
  Then injecting a fault only affects the "refund" tool
  And spans for "lookup_order" calls have status_code=OK
```

## Implementation Tasks
- [ ] Create `chaoslab/faults/malformed_tool_output.py` (≤400 lines)
- [ ] Implement `MalformedToolOutputFault` class with `inject(tool, malformation_type)` method
- [ ] Implement 4 malformation modes: `invalid_json`, `missing_required_field`, `type_mismatch`, `exception`
- [ ] Wire into Injector sub-agent's `before_tool_callback`
- [ ] Add OpenInference span attribute `chaoslab.fault.type = "malformed_tool_output"` to corrupted calls
- [ ] Write pytest unit tests in `tests/unit/faults/test_malformed_tool_output.py`
- [ ] Write integration test in `tests/integration/test_malformed_against_target.py`
- [ ] Update `docs/PRD.md` § "Fault Class F1" with implementation notes

## Test Plan
- **Unit:** mock target tool, assert each malformation_type returns the expected shape
- **Integration:** real target on local Cloud Run, real Phoenix Cloud, assert traces materialize
- **Trace-as-assertion:** load the Phoenix span via MCP, assert structural properties (not content)

## Notes
- Vendored from `deepankarm/agent-chaos`'s `tool_mutate` primitive (Apache-2.0, MIT-compatible)
  with attribution in NOTICE file. See `context/01-agent-shapes-taxonomy.md` and 
  `architecture/01-reference-implementations.md` §2.
- This story is `@parallel-safe` because the F1 fault is self-contained — no state shared
  with F2/F3/F4 stories.

## Definition of Done
- [ ] All acceptance criteria pass in CI
- [ ] No new ruff or `ty` errors
- [ ] No file exceeds 400 lines (the script-enforced check passes)
- [ ] Code coverage delta ≥ 0
- [ ] PR description includes a screencap of one trace in Phoenix Cloud showing the fault
- [ ] Story status updated to `done` in YAML front-matter
```

**Critical structural elements:**
- **YAML front-matter** carries machine-readable metadata for the orchestrator
- **User Story** in classic "As X, I want Y, so that Z" form — preserves Why
- **Background** explains context a fresh-context coding agent needs
- **Acceptance Criteria** are Gherkin (the falsifiable contract)
- **Implementation Tasks** are sequential, granular, fit in one PR
- **Notes** carry references to corpus + earlier research files
- **Definition of Done** is the gate — orchestrator's `sahil-pr-audit` verifies each box

---

## 5. Story sizing

**Heuristic:** one story = one PR = half-day to two-day work.

**Signs a story is too big:**
- More than 6 acceptance criteria scenarios
- Touches more than 5 files
- Requires more than 2 new dependencies
- The User Story has compound "and" in the want clause

**Splitting strategies:**
- **By workflow stage:** "Injector injects fault" / "Judge evaluates" / "Patcher generates recipe" — 3 stories
- **By interface layer:** "Backend API endpoint" / "Frontend component" / "E2E wiring" — 3 stories
- **By fault class:** F1 / F2 / F3 / F4 — 4 stories
- **By happy/sad path:** "Happy path works" / "Error handling works" — 2 stories

**Atomic stories enable PARALLEL EXECUTION** by multiple coding agents. The orchestrator dispatches all parallel-safe stories in independent worktrees simultaneously.

---

## 6. Acceptance criteria for AGENT code (non-deterministic LLM)

This is the load-bearing question. LLM outputs are stochastic — you can't assert exact strings.

**The trace-as-assertion pattern** (from `best-practices/06-test-strategy.md` §5.1):

Instead of asserting on the agent's natural-language output, **assert on the Phoenix span tree the agent produced**:

```gherkin
Scenario: The Patcher emits a structured hardening recipe
  Given the Judge has clustered failures into ≥2 categories
  When the Patcher sub-agent is invoked with that cluster set
  Then a Phoenix CHAIN span named "patcher.generate_recipe" appears
  And that span has a child LLM span with `output.value` containing JSON
  And that JSON validates against the HardeningRecipe pydantic schema
  And the span's `attributes.recipe.patch_count` is ≥ 1
```

**Don't:**
- ❌ "Then the agent says 'I have generated a hardening recipe'"
- ❌ "Then the response includes the word 'fix'"

**Do:**
- ✅ "Then the structured output validates against schema X"
- ✅ "Then the trace contains span Y with attributes Z"
- ✅ "Then the LLM-as-judge eval score is ≥ 0.75"

**LLM-as-judge as acceptance criterion:**
```gherkin
Scenario: The Patcher's recipe is judged as 'plausible' by Phoenix eval
  Given a patch has been generated for fault cluster X
  When the Phoenix `tool_invocation` evaluator runs on the recipe
  Then the eval score is ≥ 0.7 on a 0-1 scale
```

**Deterministic-tool stories** (no LLM judgment needed):
- Parsing functions
- Schema validation
- HTTP route handlers
- Math/transformation utilities
- These get standard unit-test assertions; reserve LLM-as-judge for the agent layer.

---

## 7. Acceptance criteria for FRONTEND code

Use Playwright + data-testid + visual regression:

```gherkin
Scenario: Attack Matrix renders 25 cells with correct colors
  Given a canonical demo run is loaded with 15 fails, 10 passes
  When the page reaches state="attack-complete"
  Then the element [data-testid="attack-matrix"] is visible
  And it has exactly 25 children with [data-testid^="attack-cell-"]
  And 15 cells have computed background color matching --color-attack-red
  And 10 cells have computed background color matching --color-pass-green
  And the Playwright screenshot matches "attack-matrix-canonical.png" within 2% pixel diff
```

**Patterns:**
- Always use `data-testid` over CSS selectors (CSS classes change; data-testids don't)
- Visual regression for the hero shot
- Accessibility via `axe-core` integration

---

## 8. Acceptance criteria for INFRASTRUCTURE code

CI/CD and Cloud Run config — test via the artifact:

```gherkin
Scenario: GitHub Actions deploys chaoslab-agent on push to main
  Given a commit is pushed to main that changes chaoslab-agent/
  When the GitHub Actions workflow "deploy-cloud-run" runs
  Then it completes with exit code 0 within 8 minutes
  And `gcloud run services describe chaoslab-agent --region=us-central1` shows the new revision serving 100% traffic
  And `curl https://chaoslab-agent-xxx.run.app/health` returns 200

Scenario: Deploy workflow respects path filters
  Given a commit changes only docs/*.md
  When the workflow runs
  Then it completes within 30s without building any container
```

---

## 9. Story dependencies + ordering

Stories declare relations in YAML front-matter:
```yaml
blocks: [STORY-011, STORY-012]
blocked-by: [STORY-003, STORY-004]
```

The orchestrator builds the DAG and dispatches ready stories (no unresolved `blocked-by`).

**Critical path:** the longest chain of blocked-by relations. Identify it; assign more attention there.

**Parallel-safe tag:** stories with `tags: [..., parallel-safe]` can run in parallel even if they share `blocked-by`. The orchestrator opens worktrees.

---

## 10. Tag conventions

Priority: `p0` (must ship), `p1` (should ship), `p2` (stretch)  
Layer: `backend`, `frontend`, `infra`  
Type: `feature`, `bug`, `spike`, `docs`, `test`  
State: `blocked`, `parallel-safe`  
Domain: `injector`, `judge`, `patcher`, `target`, `orchestrator`, `phoenix`, `cicd`, `ux`

---

## 11. Definition of Done (universal across stories)

- [ ] All acceptance criteria pass (BDD scenarios green)
- [ ] CI is green (lint, type-check, tests, 400-line check)
- [ ] Coverage delta ≥ 0
- [ ] No new ruff / ty / ESLint errors
- [ ] Story PR description includes any new acceptance criteria as Gherkin in the description
- [ ] If the story changes UX: a Playwright visual regression test exists and passes
- [ ] If the story changes infra: a successful staging deploy is referenced
- [ ] Docs updated where applicable (PRD, architecture, README)
- [ ] Story status YAML changed to `done`
- [ ] Vendored code (if any) has attribution in NOTICE
- [ ] `sahil-pr-audit` returns ✅ on all categories

---

## 12. Mapping stories → GitHub issues

`sahil-hackathon-orchestrator` automates this:

```bash
gh issue create \
  --title "STORY-007: ChaosLab injects malformed tool output" \
  --body "$(cat docs/stories/story-007-malformed-tool-output.md)" \
  --label "backend,p0,parallel-safe,fault-injection" \
  --milestone "MVP"
```

**Conventions:**
- Issue title = `<STORY-ID>: <title from front-matter>`
- Issue body = full story file contents (so the issue is self-contained)
- Labels = `tags` from front-matter, plus epic name
- Milestone = epic
- Assignee = `null` initially; orchestrator's coding agent claims via `gh issue edit --add-assignee`

Issue → Branch → PR mapping:
- Branch name: `story/<slug>` e.g. `story/malformed-tool-output`
- PR title: `feat(STORY-007): malformed tool output fault` (conventional commits)
- PR description: link back to the story file with `Closes #<issue-id>`

---

## 13. Sample stories (templates the spec-writer copies)

### Template A — Backend story
```markdown
---
id: STORY-NNN
title: <imperative-mood description>
status: draft
priority: p0|p1|p2
estimate: <half-day|1d|2d>
epic: EPIC-XXX
tags: [backend, ...]
blocks: []
blocked-by: []
---

# Story: ...

## User Story
As a <persona>,
I want <capability>,
so that <outcome>.

## Background
<≤200 words, references to corpus files where relevant>

## Acceptance Criteria
```gherkin
Background:
  Given ...
  
Scenario: ...
  Given ...
  When ...
  Then ...
```

## Implementation Tasks
- [ ] ...

## Test Plan
- Unit: ...
- Integration: ...
- Trace-as-assertion: ...

## Notes
<corpus refs, vendoring attribution>

## Definition of Done
<copy from §11>
```

### Template B — Frontend story
Same shape, with `acceptance criteria` using DOM/data-testid assertions and Playwright visual regression.

### Template C — Infrastructure story
Same shape, with `acceptance criteria` using artifact assertions (deploy succeeded, health check passes, etc.).

---

## 14. BDD anti-patterns to ban

| Anti-pattern | Why it's bad | Fix |
|---|---|---|
| "Then the system works" | Untestable, vague | Replace with specific assertion |
| "Given the user is logged in (implementation: hits /login with username 'admin')" | Implementation leakage | Just "Given an authenticated user" |
| "When X happens AND Y happens AND Z happens, Then A AND B AND C" | Multi-behavior scenario | Split into 3 scenarios |
| "Given scenario 1 ran successfully" | Coupling between scenarios | Use Background instead |
| "Then the response equals 'Welcome, John'" | Brittle string assertion | Assert on regex or structure |
| "Then performance is acceptable" | Vague | "Then p95 latency < 2s over 10 reqs" |

---

## 15. Sources

- https://cucumber.io/docs/gherkin/reference/
- https://martinfowler.com/bliki/GivenWhenThen.html
- https://github.com/bmad-code-org/BMAD-METHOD
- https://specflow.org/learn/gherkin/
- `best-practices/06-test-strategy.md` §5 (trace-as-assertion pattern for non-deterministic agent code)
- `/Users/abu/.claude/skills/sahil-spec-writer/SKILL.md` (literal consumer of this format)
- `/Users/abu/.claude/skills/sahil-hackathon-orchestrator/SKILL.md` (literal consumer of the issue mapping)
- `/Users/abu/.claude/skills/sahil-pr-audit/SKILL.md` (validates PRs against the BDD criteria)
