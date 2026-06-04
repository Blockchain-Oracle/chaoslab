# UX Spec — Phoenix Audit

**Status:** DRAFT — pending Abu approval (LOCKS upon approval)
**Anchor source:** `research/google-cloud-rapid-agent/architecture/05-ux-and-demo.md` + `research/google-cloud-rapid-agent/best-practices/04-nextjs-production.md` + `research/google-cloud-rapid-agent/brainstorm/23-trust-auditor-demo-and-product-path.md` (2026-06-04 demo arc spec)
**Last updated:** 2026-06-04 (rebranded from ChaosLab; demo arc updated to Phoenix Audit cascade-flip moment — "3 failures, 1 root cause, patch in 4 seconds")

---

## Product framing (read first)

The user is **Maya / Priya** — a Director of AI Governance at a health-insurance carrier (or any regulated org). She's the named buyer persona per `brainstorm/22-ai-trust-auditor-buyer-persona.md`. Her CRO / CISO is the economic signer one level up — every artifact Phoenix Audit produces must work both for Maya's daily workflow AND her boss's board-ready 1-pager.

The 3-min demo's cascade-flip moment happens at **1:30-2:15** when 47 adversarial tests complete (44 pass, 3 fail) and the 3 failures collapse into ONE root cause via Phoenix MCP trace-tree clustering. A "Generate hardening recipe" button produces a markdown patch in 4 seconds. Headline metric the voiceover lands: _"3 failures, 1 root cause, patch in 4 seconds."_

---

## Anchor product

**No single anchor product.** ChaosLab's UX combines patterns from multiple references:

- **Trace-as-UI pattern** — Phoenix Spans view (https://phoenix.arize.com/) sets the bar for "the agent's own execution is the user-facing surface"
- **Plan View pattern** — Devin's signature surface (https://devin.ai/) for the multi-agent pipeline visualization
- **Multi-Agent Manager View** — AntiGravity's Manager View for cell-per-agent dashboards
- **Resilience curve precedent** — LitmusChaos's resilience-score reports (https://litmuschaos.io/) for the headline "60% → 92%" framing

**Why no single anchor:** ChaosLab's hero moment (the cascade-flip + curve hybrid) is custom. The interaction patterns are borrowed; the hero visual is original.

**Quality bar:** Pattern D production polish (per `brainstorm/05-prior-winners.md`). The demo must look like "v1 of a startup" not "hackathon prototype." That's a 25%-of-judging-score lever.

---

## Design tokens (LOCKED)

Defined in `apps/chaoslab-web/app/globals.css` via Tailwind 4 `@theme` (per `best-practices/04 §2`):

| Token                        | Value                                                    | Notes                                                 |
| ---------------------------- | -------------------------------------------------------- | ----------------------------------------------------- |
| `--color-background`         | `oklch(0.18 0.02 250)`                                   | Deep ink — the chart background                       |
| `--color-surface`            | `oklch(0.22 0.025 250)`                                  | Card backgrounds, modal                               |
| `--color-surface-raised`     | `oklch(0.27 0.03 250)`                                   | Hover states, focused cards                           |
| `--color-text-primary`       | `oklch(0.96 0.005 250)`                                  | Body text                                             |
| `--color-text-secondary`     | `oklch(0.72 0.02 250)`                                   | Helper text, axis labels                              |
| `--color-text-muted`         | `oklch(0.55 0.015 250)`                                  | Subtle metadata                                       |
| `--color-attack-red`         | `oklch(0.65 0.24 25)`                                    | Failed runs in the Attack Matrix                      |
| `--color-pass-green`         | `oklch(0.72 0.20 145)`                                   | Passed runs in the Attack Matrix                      |
| `--color-patch-line`         | `oklch(0.62 0.30 280)`                                   | The vertical PATCH marker — vivid violet, the "wedge" |
| `--color-agent-orchestrator` | `oklch(0.62 0.25 220)`                                   | Electric blue — primary action color                  |
| `--color-agent-injector`     | `oklch(0.60 0.20 30)`                                    | Warm orange — attack-coded                            |
| `--color-agent-judge`        | `oklch(0.65 0.18 285)`                                   | Royal purple                                          |
| `--color-agent-patcher`      | `oklch(0.70 0.22 145)`                                   | Emerald — fix-coded                                   |
| `--color-agent-target`       | `oklch(0.55 0.05 250)`                                   | Slate — neutral victim                                |
| `--font-display`             | "Geist", system-ui, sans-serif                           | Headlines, hero                                       |
| `--font-mono`                | "Geist Mono", ui-monospace, monospace                    | Trace IDs, code, command output                       |
| Spacing scale                | 4px base: 4/8/12/16/24/32/48/64/96                       | Tailwind default                                      |
| Border radius                | `0` for cells, `6px` for cards, `999px` for badges/pills | Sharp cells = grid look; soft cards = breathing       |

**OKLCH is mandatory** — perceptually uniform, gives consistent contrast across the red/green/violet trio of the Attack Matrix. RGB-coded reds and greens don't have matched perceived brightness.

**Color-blind safety:** every red/green cell ALSO carries an icon (✗ for fail, ✓ for pass) and a tooltip with the fault class name. Color is not the only signal.

---

## Route shape

| Route         | Purpose                                     | Notes                                                                                                                          |
| ------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `/`           | Demo landing                                | Header + footer required. Hero: title, one-line pitch, single "Run ChaosLab" CTA.                                              |
| `/replay`     | Canonical pre-recorded run                  | 22s autoplay. Used when judges want fast gratification. Pre-seeded Phoenix dataset.                                            |
| `/attack`     | Live attack run                             | 90-180s real-time run. Streams via SSE from chaoslab-agent. Used for the wow demo.                                             |
| `/agent/[id]` | Per-target-agent setup (Tier 1-3 selection) | Lets advanced users point ChaosLab at their own agent. Beta — included for completeness per Abu's "no MVP skipping" directive. |
| `/api/run`    | POST endpoint → starts a run                | Returns `runId` + SSE URL                                                                                                      |
| `/api/stream` | SSE endpoint → live trace updates           | Proxies chaoslab-agent's `/stream`                                                                                             |
| `/api/health` | Liveness probe                              | Returns 200 if chaoslab-agent reachable                                                                                        |

**Demo shape rule:** the canonical demo path is `/` → click "Run" → `/attack?runId=xxx`. The Devpost video shoots this exact flow. The wow frame at 2:15 is the cascade-flip moment on `/attack`.

---

## Structural requirements (§12)

**Header** (required on every route):

- Project logo "ChaosLab" (left) — wordmark in Geist Display, tracking-tight
- Centered: state pill (`idle`, `attacking`, `judging`, `patching`, `complete`) with current-agent-color background, brief animation when transitioning
- Right: GitHub link, "Run against your agent" CTA (links to `/agent/new`)
- Height: 64px desktop, 56px mobile

**Footer** (required on `/` only):

- "ChaosLab — built at Google Cloud Rapid Agent Hackathon, June 2026"
- License: Apache-2.0 link
- Vendoring attribution: "Fault primitives adapted from `deepankarm/agent-chaos` (Apache-2.0)"
- Built-with row: Gemini logo, Phoenix logo, Cloud Run logo

**Inner-route chrome:** `/replay` and `/attack` have NO header beyond the bare logo + state pill. Maximum vertical real estate for the hero visual.

---

## The hero visual (locked — Option D from `architecture/05`)

### Composition

```
┌────────────────────────────────────────────────────────────────┐
│ HEADER: ChaosLab    [ state: attacking ]    [Run yours ↗]      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  PHASE: ATTACK (run 14 / 25)                                   │
│                                                                │
│   Attack Matrix              Resilience Curve                  │
│  ┌─────────────┐            ─┬─────────────────────────────    │
│  │ ✓ ✗ ✓ ✗ ✓ │  ◄─stagger  │                                  │
│  │ ✗ ✗ ✓ ✗ ✗ │             │   ╱╲                  ╱─╮       │
│  │ ✓ ✗ . . . │  cascade    │  ╱  ╲    ─ ─ ─ ─ ─ ─╱  ╲       │
│  │ . . . . . │  flip       │ ╱    ╲──╱            ╲           │
│  │ . . . . . │             │             PATCH ➜ │           │
│  └─────────────┘            ─┴─────────────────────┴─────      │
│   25 fault runs              pass rate over time               │
│                                                                │
│  AGENT PIPELINE: [Orchestrator] → [Injector] → [Target] →      │
│                                  [Judge] → [Patcher]           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Behavior (timed for the 3-min demo)

| t (sec) | Phase               | Matrix state                                                                      | Curve state                                                      | What the judge sees                                                |
| ------: | ------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------ |
|    0:00 | idle                | empty 5×5 grid (placeholder dots)                                                 | empty                                                            | Landing → "Run ChaosLab" CTA                                       |
|    0:05 | baseline-check      | all cells green (24/25)                                                           | flat at 96%                                                      | "Baseline pass rate 96% ✓"                                         |
|    0:15 | attack-start        | cells flipping red one by one (Framer Motion stagger, ~0.04s delay between cells) | curve drops as cells flip                                        | "Attacking with 4 fault classes..."                                |
|    1:30 | attack-complete     | 5×5 grid mostly red (~15 fails, ~10 passes)                                       | curve sits at ~40%                                               | "15/25 attacks succeeded"                                          |
|    1:35 | judging             | cells get a slight purple outline (judging in progress)                           | unchanged                                                        | "Clustering failures..."                                           |
|    1:45 | patching            | small "patch generated" badge appears                                             | unchanged                                                        | "3 root causes identified, patch generated"                        |
|    1:50 | **THE PATCH FIRES** | **cascade-flip starts: cells flip red → green left-to-right, top-to-bottom**      | **vertical PATCH line drops at this x-position; curve jumps up** | THE WOW MOMENT                                                     |
|    2:00 | re-attack           | cells continue flipping (now mostly green)                                        | curve rises to ~92%                                              | "Re-running 25 attacks against patched agent..."                   |
|    2:15 | post-patch hold     | grid frozen at final state (22 green / 3 red)                                     | curve plateaus                                                   | THE DEVPOST COVER FRAME (1.5s held, slow zoom into the PATCH line) |
|    2:30 | receipt             | matrix fades to 30% opacity                                                       | curve persists at full opacity                                   | Receipt card slides up                                             |
|    2:55 | done                | all frozen                                                                        | all frozen                                                       | "Run against your own agent ↗" CTA                                 |

### Why this works

- **Same story told two ways simultaneously.** Matrix shows individual-run truth (binary pass/fail); curve shows aggregate-progress truth (pass rate). Same x-axis, same PATCH line. Two views, one moment.
- **The PATCH line is literally the wedge** in the chart. Visual pun + truthful representation of the value.
- **Cascade-flip cells communicate "everything got fixed"** in 1.5 seconds. No narration needed. The video can have music + no voiceover at this point and still land.
- **Frame at 2:15 is replayable** — judge can scrub the video, pause at 2:15, get the entire story.

---

## Component contracts

Components in `apps/chaoslab-web/app/_components/` and `apps/chaoslab-web/components/`.

### `<AttackMatrix>`

```tsx
interface AttackCell {
  idx: number; // 0-24
  passed: boolean; // true = green, false = red
  faultClass:
    | "malformed_tool_output"
    | "prompt_injection"
    | "context_poisoning"
    | "latency_spike";
  spanId: string | null; // Phoenix span ID for click-through
}

interface AttackMatrixProps {
  cells: AttackCell[];
  revealedCount: number; // 0-25, drives stagger
  phase:
    | "idle"
    | "baseline"
    | "attacking"
    | "judging"
    | "patching"
    | "reattacking"
    | "complete";
}

// data-testid="attack-matrix"
// each cell: data-testid="attack-cell-{idx}"
// cells clickable → open Phoenix span view in new tab
```

### `<ResilienceCurve>`

```tsx
interface ResiliencePoint {
  x: number;
  y: number;
  phase: "attack" | "reattack";
}

interface ResilienceCurveProps {
  attackPoints: ResiliencePoint[]; // pre-patch run sequence
  reattackPoints: ResiliencePoint[]; // post-patch run sequence
  patchX: number | null; // x-coordinate of the PATCH line (null until patch fires)
}

// uses visx LinePath, AxisBottom, AxisLeft, Grid, Marker
// PATCH line is a <Line> with stroke-dasharray + animated stroke-dashoffset
```

### `<AgentPipeline>`

Visualization of the 5 agents and their A2A handoffs. Active agent gets a pulsing glow in its color.

```tsx
interface AgentPipelineProps {
  activeAgent:
    | "orchestrator"
    | "injector"
    | "judge"
    | "patcher"
    | "target"
    | null;
  edges: Array<{ from: string; to: string; active: boolean }>;
}
```

### `<ReceiptCard>`

Final card. Slides up from bottom after re-attack completes.

```tsx
interface ReceiptCardProps {
  runId: string;
  attackCount: number;
  faultClasses: string[];
  rootCausesFound: number;
  recipeId: string;
  mrUrl: string | null; // GitLab MR URL if emitted
  markdownUrl: string; // GCS URL for the Markdown artifact
  costUsd: number;
  durationSeconds: number;
  baselinePassRate: number; // e.g., 0.96
  postPatchPassRate: number; // e.g., 0.92
  improvement: number; // post-patch - pre-patch attack pass rate
}
```

---

## Banned Tailwind classes

In addition to global bans (`from-purple-500 to-pink-500`, `text-gray-600`, `font-sans`):

- `rounded-full` on cards — cards use 6px radius only; pills/badges use full
- `bg-white` on backgrounds — use `bg-surface` token
- `text-blue-500` and similar named colors — use agent color tokens
- `shadow-md/lg/xl` — use custom subtle shadows: `shadow-[0_1px_3px_0_oklch(0_0_0/0.3)]`
- `space-y-*` for vertical stacks — use `flex flex-col gap-*` (more predictable)
- `text-center` for body copy — left-aligned only; center only for hero headlines

---

## Accessibility

- WCAG AA contrast on all text (OKLCH tokens chosen to hit this)
- Color + icon redundancy on every red/green cell
- All interactive elements keyboard-reachable (Tab order matches reading order)
- Visible focus rings (Tailwind default, never `outline-none`)
- Reduced motion: respect `prefers-reduced-motion`. The cascade-flip is the demo's wow moment, but for users with reduced motion: cells change color instantly without stagger, curve still animates but at 2× speed. Test: `useReducedMotion()` from framer-motion.
- ARIA: `<div role="grid" aria-label="Attack results, 25 fault injection runs">` for the matrix; each cell `aria-label="Run 3, malformed tool output, passed"`
- Screen-reader live region announces phase changes: `<div role="status" aria-live="polite">{phaseLabel}</div>`

---

## Devpost OG image

`public/og-hero.png` — 1200x630 PNG of the 2:15 frame (matrix mid-cascade, curve mid-jump, PATCH line visible). Generated via Playwright screenshot of the demo at the canonical state.

`generateMetadata()` in `app/page.tsx` references this for Open Graph + Twitter card.

---

## Visual loop integration

Per `best-practices/04 §15` + `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md`:

- After every `.tsx` edit, a PostToolUse hook fires Playwright + screenshot diff vs anchor
- Anchor screenshots stored at `apps/chaoslab-web/screenshots/anchor/`:
  - `home--desktop.png`
  - `attack--mid-attack.png` (1:00 frame state)
  - `attack--cascade-flip.png` (1:55 frame state)
  - `attack--receipt.png` (2:45 frame state)
- These are LOCKED — never overwrite. The coding agent updates the implementation to match anchors, not vice versa.
- Pass threshold: `slop_score ≤ 2 AND blocking_count = 0`
- Don't commit while `.claude/last-review.json` shows `needs-fix` or `slop`
