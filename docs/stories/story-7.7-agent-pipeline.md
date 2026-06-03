# Story — <AgentPipeline> A2A handoff visualization with active-glow

**ID:** story-7.7-agent-pipeline
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.2-design-tokens, story-7.4-run-store-and-sse
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** judge watching ChaosLab's hero visual
**I want to** see a horizontal pipeline of 5 agent nodes (Orchestrator → Injector → Judge → Patcher → Target) with the currently-active agent pulsing in its agent-color and the active A2A handoff arrow highlighted
**So that** the multi-agent A2A topology — the part `context/03 §13` identifies as the market gap no existing red-team tool handles — is visible in the demo at all times, telling judges "this is a SYSTEM of agents, not a single LLM"

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/app/_components/agent-pipeline.tsx` — NEW — Client component per `docs/ux-spec.md` `<AgentPipeline>` contract. Props `{ activeAgent: AgentId | null; edges: Array<{ from: AgentId; to: AgentId; active: boolean }> }`. Renders an SVG layout with 5 circle nodes labeled "Orchestrator", "Injector", "Judge", "Patcher", "Target", connected by arrows. Active node has `data-testid="agent-pipeline-active"` and a Framer Motion `<motion.circle>` with `animate={{ filter: ['drop-shadow(0 0 4px ...)', 'drop-shadow(0 0 16px ...)', 'drop-shadow(0 0 4px ...)'] }}` pulse. Active arrows have `data-active="true"` + animated stroke. ≤250 LOC.
- `apps/chaoslab-web/app/_components/agent-pipeline-node.tsx` — NEW — sub-component for a single node (circle + label + glow). Color sourced from the agent-color CSS var (static map `AGENT_COLOR_VAR: Record<AgentId, string>`). ≤80 LOC.
- `apps/chaoslab-web/lib/agent-meta.ts` — NEW — Static metadata: `AGENT_ORDER: AgentId[]`, `AGENT_LABEL: Record<AgentId, string>`, `AGENT_COLOR_VAR: Record<AgentId, string>` (mapping `orchestrator` → `var(--color-agent-orchestrator)` etc.). ≤40 LOC.
- `apps/chaoslab-web/tests/unit/agent-pipeline.test.tsx` — NEW — Vitest + RTL. ≥6 test cases: (1) renders 5 node elements; (2) renders 4 arrow elements connecting consecutive nodes; (3) when activeAgent="injector", the injector node has `data-testid="agent-pipeline-active"`; (4) active node has computed style `filter` containing "drop-shadow"; (5) when activeAgent=null, no node has the active testid; (6) edge with `active=true` has `data-active="true"` on the path; (7) reduced motion → no pulse animation.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given AgentPipeline has been written and is rendered with activeAgent="injector"
When the DOM is queried
Then exactly one element matches [data-testid="agent-pipeline-active"]
And that element is the injector node (e.g., contains text matching /injector/i)

Given AgentPipeline is rendered with activeAgent="injector"
When `getComputedStyle(activeNode).filter` is read
Then the value contains "drop-shadow"

Given AgentPipeline is rendered with edges including { from: "orchestrator", to: "injector", active: true }
When the DOM is queried for the arrow from orchestrator to injector
Then the element has attribute data-active="true"
And other (inactive) arrows have data-active="false"

Given AgentPipeline is rendered with activeAgent=null
When the DOM is queried
Then no element matches [data-testid="agent-pipeline-active"]

Given prefers-reduced-motion: reduce is active
When AgentPipeline renders with activeAgent set
Then no Framer Motion pulse animation runs (Framer Motion's animate prop becomes static)

Given AgentPipeline is rendered
When the DOM is queried for nodes
Then exactly 5 nodes are rendered (one per agent: orchestrator, injector, judge, patcher, target)
And each node has aria-label matching its agent name

Given vitest is run
When `pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/agent-pipeline.test.tsx` executes
Then exit code is 0
And ≥6 test cases pass
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/app/_components/agent-pipeline.tsx
test -f apps/chaoslab-web/app/_components/agent-pipeline-node.tsx
test -f apps/chaoslab-web/lib/agent-meta.ts
test -f apps/chaoslab-web/tests/unit/agent-pipeline.test.tsx

# 'use client'
head -5 apps/chaoslab-web/app/_components/agent-pipeline.tsx | grep -E "'use client'"
head -5 apps/chaoslab-web/app/_components/agent-pipeline-node.tsx | grep -E "'use client'"

# All 5 agents declared
test "$(grep -cE '(orchestrator|injector|judge|patcher|target)' apps/chaoslab-web/lib/agent-meta.ts)" -ge 5

# Framer Motion + reduced motion
grep -E "framer-motion" apps/chaoslab-web/app/_components/agent-pipeline-node.tsx
grep -E "useReducedMotion" apps/chaoslab-web/app/_components/agent-pipeline.tsx

# Active testid plumbing
grep -E "agent-pipeline-active" apps/chaoslab-web/app/_components/agent-pipeline-node.tsx
grep -E "data-active" apps/chaoslab-web/app/_components/agent-pipeline.tsx

# Color tokens
test "$(grep -cE 'color-agent-(orchestrator|injector|judge|patcher|target)' apps/chaoslab-web/lib/agent-meta.ts)" -ge 5

# Unit tests
pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/agent-pipeline.test.tsx
test "$(pnpm --filter chaoslab-web exec vitest run apps/chaoslab-web/tests/unit/agent-pipeline.test.tsx --reporter=verbose 2>&1 | grep -cE '✓|PASS')" -ge 6

# Typecheck + build
pnpm --filter chaoslab-web exec tsc --noEmit
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# 400-line guard
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/agent-pipeline.tsx)" -le 250
test "$(grep -cvE '^\s*(//|$)' apps/chaoslab-web/app/_components/agent-pipeline-node.tsx)" -le 80

echo "story-7.7 verification: PASS"
```

---

## Notes for coding agent

- 5-node layout: nodes are positioned horizontally with the Orchestrator at the apex and a "hub-and-spoke" feel; the simplest layout is left-to-right linear: `[Orchestrator] → [Injector] → [Target]` on a top row, and `[Judge] → [Patcher]` feeding back into Orchestrator on a bottom row. Use absolute positioning OR a flat horizontal row of 5 with curved arrows. EITHER layout passes the acceptance criteria — pick the one that reads cleanly in the hero composition.
- The horizontal row layout is simpler and time-cheaper. The cyclic feedback layout is more accurate to the architecture (Judge + Patcher loop back to Orchestrator) but harder to draw. Default: horizontal row, edges connect consecutive nodes left-to-right; document the architectural simplification in a comment.
- Active glow: Framer Motion pulse via `animate={{ filter: ['drop-shadow(0 0 4px var(--color-agent-X))', 'drop-shadow(0 0 16px var(--color-agent-X))', 'drop-shadow(0 0 4px var(--color-agent-X))'] }}` with `transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}`. The agent-color comes from the static map in `agent-meta.ts`.
- Dynamic class warning (same as story-7.5): cannot use `\`bg-agent-${id}\``. Use a static lookup map: `AGENT_BG: { orchestrator: 'bg-agent-orchestrator', injector: 'bg-agent-injector', ... }`.
- Active arrow: an SVG `<path>` with `stroke="var(--color-agent-{from})"` and `stroke-dasharray="4 4"` + `<animate attributeName="stroke-dashoffset" from="0" to="-8" dur="0.6s" repeatCount="indefinite"/>` for the marching-ants effect. Inactive arrows are static `stroke="var(--color-text-muted)"`.
- ARIA: each node gets `aria-label="{agentLabel} agent, {active ? 'active' : 'idle'}"`. The whole pipeline container: `role="img" aria-label="Agent pipeline: orchestrator, injector, judge, patcher, target"`.
- Reduced motion: kill the pulse and the marching ants. Replace with a static `filter: drop-shadow(0 0 8px var(--color-agent-X))` glow (still visible, just not animated).
- Layout in CSS: use Tailwind `flex flex-row items-center justify-between` on the container, each node a `<motion.div>` with `w-16 h-16 rounded-full` + the color background.
- SVG vs CSS: an SVG `<line>` or `<path>` is easier to animate dasharray than a CSS pseudo-element. Use SVG arrows. Position them between nodes via absolute positioning OR an inline `<svg>` overlay.
- Active edge detection: walk the `edges` prop. For each edge, render a `<path data-active={edge.active}>` with the correct stroke.
- Total LOC budget: agent-pipeline.tsx ≤250 (includes the SVG layout + edge rendering). agent-pipeline-node.tsx ≤80 (just one node + label + glow). If main file crosses 250, extract the arrow rendering into `agent-pipeline-edges.tsx`.
- Phase mapping to active agent (for use by `/attack` route in story-7.11): `baseline → injector`, `attacking → injector`, `judging → judge`, `patching → patcher`, `reattacking → injector`, `complete → null`. This mapping lives in the route, not in this component.
- DO NOT animate `width` or `top` — only `filter`, `opacity`, `transform`. Per `best-practices/04 §5` performance rule.
