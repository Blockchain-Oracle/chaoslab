# Story — sahil-visual-loop integration (anchors + hook + reviewer)

**ID:** story-7.12-visual-loop-integration
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.5-attack-matrix (need ≥1 real component rendered to capture meaningful anchor screenshots)
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** coding agent writing more `.tsx` files in Epic 7 (and as Abu reviewing future PRs)
**I want to** install the sahil-visual-loop scaffold (Playwright config, PostToolUse hook, anchor capture script, fresh-context Opus 4.7 vision reviewer, CLAUDE.md addendum) and capture the 4 anchor screenshots
**So that** every subsequent `.tsx` edit fires the visual loop, produces a structured `slop_score` + `blocking_count` verdict, and the coding agent CANNOT silently ship slop — making the 25% Design judging score defensible

---

## File modification map

Exact files the coding agent creates or modifies for this story (per `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md`):

- `apps/chaoslab-web/playwright.config.ts` — NEW — From template `playwright-config.ts`. 3-viewport projects (desktop / tablet / mobile), `webServer: { command: 'pnpm dev', url: 'http://localhost:3000', reuseExistingServer: !CI }`. ≤80 LOC.
- `apps/chaoslab-web/tests/visual/pages.spec.ts` — NEW — From template `visual-pages-spec.ts`. `toHaveScreenshot()` against canonical states with `maxDiffPixelRatio: 0.02`. Covers: `/`, `/replay` mid-state, `/replay` complete, `/attack` mid-cascade. ≤150 LOC.
- `apps/chaoslab-web/.claude/hooks/visual-check.sh` — NEW — From template `visual-check.sh`. PostToolUse hook entrypoint, fires Playwright + invokes the Python vision reviewer. Exits 0 ALWAYS (never blocks Claude) but writes verdict to `.claude/last-review.json`. Executable (`chmod +x`).
- `apps/chaoslab-web/.claude/hooks/visual_reviewer.py` — NEW — From template `visual_reviewer.py`. Uses `anthropic` Python SDK directly (NOT Claude Code's Read tool — per skill `Hard rules`). Sends current screenshot + anchor screenshot, gets structured JSON verdict `{ status, slop_score, blocking_count, deltas[] }`. Writes to `.claude/last-review.json`.
- `apps/chaoslab-web/.claude/agents/visual-reviewer.md` — NEW — From template `visual-reviewer-agent.md`. Fresh-context Opus 4.7 reviewer subagent definition with the 7-tells slop-detection criteria.
- `apps/chaoslab-web/.claude/commands/visual-review.md` — NEW — From template `visual-review-command.md`. Manual `/visual-review` slash command for ad-hoc checks.
- `apps/chaoslab-web/scripts/capture-anchor.ts` — NEW — From template `capture-anchor.ts`. One-time anchor capture script (Playwright + headless Chromium). Captures the 4 anchor screenshots into `apps/chaoslab-web/screenshots/anchor/`.
- `apps/chaoslab-web/screenshots/anchor/home--desktop.png` — NEW — Anchor for `/` at 1440×900. Captured via `pnpm exec ts-node scripts/capture-anchor.ts`. LOCKED — immutable after this story.
- `apps/chaoslab-web/screenshots/anchor/attack--mid-attack.png` — NEW — Anchor for `/replay` paused at the 1:00 frame (matrix 60% populated red, curve dropping). Captured via the same script using `?freezeAt=1m` query param the orchestrator honors. LOCKED.
- `apps/chaoslab-web/screenshots/anchor/attack--cascade-flip.png` — NEW — Anchor for `/replay` paused at the 1:55 frame (cells mid-flip red → green, patch line visible). LOCKED.
- `apps/chaoslab-web/screenshots/anchor/attack--receipt.png` — NEW — Anchor for `/replay` at the 2:45 frame (receipt card visible). LOCKED.
- `apps/chaoslab-web/screenshots/.gitignore` — NEW — gitignores `baseline/` and `current/` subfolders (anchor/ is committed).
- `apps/chaoslab-web/CLAUDE.md` — NEW — From template `claude-md-addendum.md`. Project-specific Claude memory: anchor URLs, design constraints, "stop shipping if `.claude/last-review.json` reports needs-fix or slop" rule.
- `apps/chaoslab-web/.claude/settings.json` — NEW — registers the PostToolUse hook for `Edit|Write` matching `app/**`, `components/**`, `*.tsx`. Exact JSON:
  ```json
  {
    "hooks": {
      "PostToolUse": [
        {
          "matcher": "Edit|Write",
          "hooks": [
            { "type": "command", "command": ".claude/hooks/visual-check.sh" }
          ]
        }
      ]
    }
  }
  ```
- `apps/chaoslab-web/package.json` — UPDATE — add devDeps: `@playwright/test`, `odiff-bin`, `ts-node`
- `apps/chaoslab-web/.gitignore` — UPDATE — add `.claude/last-review.json`, `screenshots/current/`, `playwright-report/`, `test-results/`

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the sahil-visual-loop templates have been copied verbatim
When `test -f apps/chaoslab-web/playwright.config.ts && test -f apps/chaoslab-web/.claude/hooks/visual-check.sh && test -f apps/chaoslab-web/.claude/hooks/visual_reviewer.py` runs
Then exit code is 0

Given the visual-check.sh hook exists
When `test -x apps/chaoslab-web/.claude/hooks/visual-check.sh` runs
Then exit code is 0 (executable bit set)

Given the .claude/settings.json registers the hook
When `node -e "const s=require('./apps/chaoslab-web/.claude/settings.json'); process.exit(s.hooks.PostToolUse[0].matcher.includes('Edit') && s.hooks.PostToolUse[0].hooks[0].command.includes('visual-check.sh') ? 0 : 1)"` runs
Then exit code is 0

Given the anchor capture script ran successfully
When `ls apps/chaoslab-web/screenshots/anchor/*.png | wc -l` runs
Then output is ≥ 4

Given the 4 anchor images exist
When `file apps/chaoslab-web/screenshots/anchor/home--desktop.png apps/chaoslab-web/screenshots/anchor/attack--mid-attack.png apps/chaoslab-web/screenshots/anchor/attack--cascade-flip.png apps/chaoslab-web/screenshots/anchor/attack--receipt.png` runs
Then each line contains "PNG image"

Given Playwright is installed and the visual spec exists
When `pnpm --filter chaoslab-web exec playwright test apps/chaoslab-web/tests/visual/pages.spec.ts` runs (with anchors as baseline on first run via --update-snapshots)
Then exit code is 0

Given a .tsx file has been edited (e.g., a no-op space-then-undo in apps/chaoslab-web/app/_components/attack-matrix.tsx)
When the PostToolUse hook fires
Then `.claude/last-review.json` is produced within 60 seconds
And the JSON contains keys: status, slop_score, blocking_count

Given the visual loop has produced a verdict for the canonical landing page state
When `.claude/last-review.json` is read
Then status equals "ok"
And slop_score is ≤ 2
And blocking_count equals 0

Given CLAUDE.md addendum exists
When `grep -E "(anchor|visual-loop|slop)" apps/chaoslab-web/CLAUDE.md` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Templates copied
test -f apps/chaoslab-web/playwright.config.ts
test -f apps/chaoslab-web/tests/visual/pages.spec.ts
test -f apps/chaoslab-web/.claude/hooks/visual-check.sh
test -f apps/chaoslab-web/.claude/hooks/visual_reviewer.py
test -f apps/chaoslab-web/.claude/agents/visual-reviewer.md
test -f apps/chaoslab-web/.claude/commands/visual-review.md
test -f apps/chaoslab-web/scripts/capture-anchor.ts
test -f apps/chaoslab-web/CLAUDE.md
test -f apps/chaoslab-web/.claude/settings.json

# Hook is executable
test -x apps/chaoslab-web/.claude/hooks/visual-check.sh

# Settings register the hook
node -e "const s=require('./apps/chaoslab-web/.claude/settings.json'); \
  process.exit(s.hooks.PostToolUse[0].matcher.includes('Edit') && \
  s.hooks.PostToolUse[0].hooks[0].command.includes('visual-check.sh') ? 0 : 1)"

# 4 anchor screenshots exist + are valid PNGs
test "$(ls apps/chaoslab-web/screenshots/anchor/*.png 2>/dev/null | wc -l)" -ge 4
for f in apps/chaoslab-web/screenshots/anchor/home--desktop.png \
         apps/chaoslab-web/screenshots/anchor/attack--mid-attack.png \
         apps/chaoslab-web/screenshots/anchor/attack--cascade-flip.png \
         apps/chaoslab-web/screenshots/anchor/attack--receipt.png; do
  file "$f" | grep -E "PNG image"
done

# CLAUDE.md addendum referenced anchors + slop rule
grep -E "(anchor|visual-loop|slop)" apps/chaoslab-web/CLAUDE.md

# Playwright deps installed
node -e "const p=require('./apps/chaoslab-web/package.json'); \
  process.exit(p.devDependencies['@playwright/test'] && p.devDependencies['odiff-bin'] ? 0 : 1)"

# Anthropic SDK installed for vision reviewer (python side)
python3 -c "import anthropic" 2>&1 | grep -qvE "ModuleNotFoundError" || \
  pip3 install anthropic

# Trigger a no-op edit to fire the hook (touch then revert)
TOUCH_FILE=apps/chaoslab-web/app/_components/attack-matrix.tsx
cp "$TOUCH_FILE" "$TOUCH_FILE.bak"
echo "" >> "$TOUCH_FILE"
bash apps/chaoslab-web/.claude/hooks/visual-check.sh "$TOUCH_FILE" || true
mv "$TOUCH_FILE.bak" "$TOUCH_FILE"

# Verdict produced
test -f apps/chaoslab-web/.claude/last-review.json
node -e "const r=require('./apps/chaoslab-web/.claude/last-review.json'); \
  process.exit(r.status==='ok' && r.slop_score<=2 && r.blocking_count===0 ? 0 : 1)"

# 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/.claude apps/chaoslab-web/scripts apps/chaoslab-web/tests/visual

echo "story-7.12 verification: PASS"
```

---

## Notes for coding agent

- This story is THE invocation of the `sahil-visual-loop` skill. Do NOT reimplement templates from scratch — copy them verbatim from `/Users/abu/.claude/skills/sahil-visual-loop/templates/`. The skill's `Hard rules` section explicitly says "no autoVerify flag, route reviewer through Python anthropic SDK, anchors are immutable."
- ANCHORS ARE IMMUTABLE. Once captured by `pnpm exec ts-node apps/chaoslab-web/scripts/capture-anchor.ts`, NEVER overwrite. If the design needs to change, capture NEW anchors with new names — don't mutate existing files.
- The 4 anchor screenshots are the 4 named in `docs/ux-spec.md` §"Visual loop integration":
  - `home--desktop.png` — `/` at 1440×900
  - `attack--mid-attack.png` — `/replay` paused at the 1:00 frame (matrix 60% red, curve at 40%)
  - `attack--cascade-flip.png` — `/replay` paused at the 1:55 frame (cells mid-flip, patch line visible)
  - `attack--receipt.png` — `/replay` at the 2:45 frame (receipt card visible)
- The capture script must support a `?freezeAt=...` query param on `/replay` that pauses the orchestrator at a scripted ms timestamp. Add this to `replay-orchestrator.tsx` from story-7.10 if not already supported — the param halts further `setTimeout` callbacks.
- The visual reviewer is OPUS 4.7 via the Anthropic Python SDK. The model ID is `claude-opus-4-7[1m]` (long-context variant). The reviewer is given: (a) current screenshot, (b) anchor screenshot, (c) the 7-tells slop criteria. Returns structured JSON.
- Pass threshold from `docs/ux-spec.md` §"Visual loop integration": `slop_score ≤ 2 AND blocking_count == 0` → status="ok". Anything else blocks merges (per CLAUDE.md addendum).
- The hook NEVER hard-fails Claude (exits 0 always). It writes the verdict to `.claude/last-review.json`. The coding agent is RESPONSIBLE for reading that file and stopping if status != "ok".
- Install preconditions (run before this story's verification):
  ```bash
  pnpm add -D @playwright/test odiff-bin ts-node
  pnpm exec playwright install --with-deps chromium
  pip3 install anthropic
  ```
- `ANTHROPIC_API_KEY` env var must be set when the reviewer fires. Document this in CLAUDE.md addendum. For CI runs, it's a secret-injected env var. For local dev, the developer's existing `~/.anthropic` or env should work.
- The .claude/settings.json hook matcher MUST be `Edit|Write` (regex) — the `|` is the alternation operator, supported by Claude Code's matcher per skill docs.
- The hook should only run on file changes under `apps/chaoslab-web/app/**` or `apps/chaoslab-web/components/**` or `*.tsx`. The shell script handles the path filter; the matcher in settings.json fires for every Edit|Write, but `visual-check.sh` returns early if the changed file isn't in scope.
- CLAUDE.md addendum must include the anchor file paths, the slop-score thresholds, the "do not commit while status=needs-fix" rule, and pointers to the templates. Use the template `claude-md-addendum.md` verbatim, with `{PROJECT_NAME}` replaced by "ChaosLab".
- DO NOT install Playwright MCP server. The skill explicitly says "Playwright as CLI, not MCP, for test runs."
- After this story lands, every subsequent .tsx edit in Epic 7 (revisions to story-7.5–7.11 components) fires the loop automatically. If a coding agent gets a `needs-fix` or `slop` verdict, they fix the design before opening the PR.
- If `.claude/last-review.json` doesn't exist after the test edit, the hook never fired — diagnose: (a) is the hook executable? (b) is `.claude/settings.json` valid JSON? (c) is `ANTHROPIC_API_KEY` set? (d) is the Python `anthropic` package installed?
- Total LOC across this story: templates are <500 LOC total. The 400-line guard ignores anchor PNGs (binary files).
- For the BDD criterion "status equals ok, slop_score ≤ 2, blocking_count == 0" — this is the green-light verdict on the canonical landing page state. If the landing page LOOKS like AI slop (median-purple gradient, Inter everywhere, predictable card grid), the reviewer correctly returns "slop" or "needs-fix" and the test fails. That's the intended failure mode — the coding agent must improve the design until the reviewer passes.
