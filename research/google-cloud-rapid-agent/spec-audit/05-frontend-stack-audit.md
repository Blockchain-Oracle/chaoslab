# Frontend Stack Audit — ChaosLab Epic 7

**Audit date:** 2026-06-03
**Auditor:** spec-audit sub-agent (fresh context, Opus 4.7)
**Scope:** Epic 7's 12 frontend stories (`docs/stories/story-7.*.md`) — claims about Next.js 15, Tailwind 4, shadcn/ui, visx, Framer Motion v12, Zustand v5, TanStack Query v5, nuqs, Playwright, `output: 'standalone'`, and the `sahil-visual-loop` skill integration.

---

## Verdicts at a glance

| #   | Claim                                                                                                                 | Verdict                                                                                                                           | Severity     |
| --- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------ | --- | --- | -------------------------------------------------------------------------- | ------------------------- |
| 1   | Next.js 15 is shipping (not beta)                                                                                     | ⚠️ **STALE — Next.js 16 is the `latest` tag (16.2.7, 2026-06-01); 15.5.19 is `backport` only**                                    | **BLOCKING** |
| 2   | Tailwind 4 is shipping (not beta)                                                                                     | ✅ PASS — Tailwind 4.3.0 is `latest`, CSS-first `@theme` is canonical                                                             | none         |
| 3   | `@tailwindcss/postcss` is the correct PostCSS plugin name                                                             | ✅ PASS — `@tailwindcss/postcss@4.3.0`, exact plugin name spec'd                                                                  | none         |
| 4   | shadcn/ui CLI works with Tailwind 4                                                                                   | ✅ PASS — shadcn CLI ships Tailwind-4-aware templates since 2.x; current `latest` = 4.10.0                                        | none         |
| 5   | `pnpm dlx shadcn@latest init` is canonical install                                                                    | ✅ PASS — confirmed against shadcn docs                                                                                           | none         |
| 6   | shadcn "New York" style exists                                                                                        | ✅ PASS — one of two officially documented styles (default + new-york)                                                            | none         |
| 7   | `@visx/*` packages exist + co-versioned                                                                               | ⚠️ \*\*CAVEAT — all at v3.12.0 (`latest`); v3.x peerDeps DO NOT list React 19 (`^16                                               |              | ^17 |     | ^18` only). v4.0.0-alpha.11 adds React 19. Stable v4 not yet released.\*\* | **BLOCKING for React 19** |
| 8   | `framer-motion` v12 is shipping; `motion.div`, stagger via per-index delays, `useReducedMotion()` are stable v12 APIs | ✅ PASS — `framer-motion@12.40.0` (2026-05-21) is `latest`; all three APIs documented in v12                                      | none         |
| 9   | `zustand` v5 exists + API stable                                                                                      | ✅ PASS — `zustand@5.0.14` is `latest`, React 18+ peer                                                                            | none         |
| 10  | `@tanstack/react-query` v5 + `nuqs` exist                                                                             | ✅ PASS — `@tanstack/react-query@5.101.0`, `nuqs@2.8.9` (note: nuqs peer is `next>=14.2.0`, fine for 15+ and 16)                  | none         |
| 11  | `@playwright/test` current + `toHaveScreenshot()` API stable                                                          | ✅ PASS — `@playwright/test@1.60.0`, `toHaveScreenshot()` is GA since 1.31                                                        | none         |
| 12  | `output: 'standalone'` in `next.config.ts` produces `server.js` for Cloud Run                                         | ✅ PASS — documented in Next.js docs; pattern unchanged from 15 → 16                                                              | none         |
| 13  | `sahil-visual-loop` skill exists + integration path matches                                                           | ✅ PASS — `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md` exists; all 8 templates present; S7.12 file map matches verbatim | none         |

**Totals:** 11 PASS, 2 BLOCKING amendments needed.

---

## Live npm verification (2026-06-03)

```
next                       latest=16.2.7  backport=15.5.19  beta=16.0.0-beta.0  canary=16.3.0-canary.38
                           Recent stable releases: 16.2.7 (2026-06-01), 15.5.19 (2026-06-01), 16.2.6, 15.5.18, 16.2.5...
tailwindcss                latest=4.3.0   v3-lts=3.4.19  next=4.0.0
                           Recent: 4.1.x → 4.2.x → 4.3.0 (2026-06-02). CSS-first `@theme` is stable since 4.0.0.
@tailwindcss/postcss       latest=4.3.0   next=4.0.0
shadcn                     latest=4.10.0  rc=4.10.0-rc.674ae44   (CLI version, not the project version)
framer-motion              latest=12.40.0 (2026-05-21)  beta=5.5.6-beta.0 (deprecated v4 branch)
@visx/group                latest=3.12.0  next=4.0.0-alpha.11   peerDeps: react ^16 || ^17 || ^18 (NO 19!)
@visx/group@4.0.0-alpha.11 peerDeps: react ^16.14 || ^17 || ^18 || ^19
@visx/{scale,shape,grid,axis,responsive,text,curve}  all latest=3.12.0   ✓ co-versioned
zustand                    latest=5.0.14  peer: react>=18
@tanstack/react-query      latest=5.101.0 peer: react ^18 || ^19
nuqs                       latest=2.8.9   peer: next>=14.2.0, react>=18.2.0
@playwright/test           latest=1.60.0
```

---

## Detailed findings

### Claim 1 — Next.js 15 ⚠️ BLOCKING

**Spec says:** Next.js 15 (App Router), pin `next@15.x`, `react@19.x`. (architecture.md L14, L184; story-7.1 L24/L157.)

**Reality (2026-06-03):**

- `npm view next dist-tags` → `latest=16.2.7`, `backport=15.5.19`, `beta=16.0.0-beta.0`.
- Next.js 16 has been the default `latest` since 2025-Q3 (16.0.x). 16.2.7 shipped 2026-06-01.
- Next.js 15 is in long-term backport mode. The `next-15-5`, `next-15-3`, `next-15-2`, `next-15-0` dist-tags are all pinned to old patches.
- `pnpm add next` today **resolves to 16.2.7, not 15.x.** Story-7.1's verification step `node -e "...p.dependencies.next..."` only checks presence, not major — it will silently install 16.

**Impact:**

- The spec's package pin `^next@15.x` is a _downgrade_ requirement against the registry default. The coding agent must explicitly request `next@^15` (or `next@~15.5`) — otherwise `pnpm add next` writes `"next": "^16"`.
- App Router shape is broadly compatible 15→16, but breaking changes exist (async `cookies()`/`headers()`/`params`/`searchParams` enforced; `next/dynamic` defaults; Turbopack default for `dev` and `build`). Specifically:
  - `params` and `searchParams` props in pages MUST be `await`ed in 16 (already enforced).
  - `cookies()`, `headers()`, `draftMode()` are async in 15+ (carried into 16).
  - `next.config.ts` `experimental.dynamicIO` flips to `cacheComponents`-related options.
  - Several `experimental.*` flags removed/renamed in 16.

**Required amendment (architecture.md + story-7.1):**

Either:

- **Option A (recommended for hackathon scope):** Bump to Next.js 16 throughout. Rationale: 16 has been `latest` for ~8 months, ecosystem is on it, React 19 fully supported, Turbopack default speeds up the visual loop. Spec is stale, not the registry.
- **Option B:** Keep 15 explicitly. Then story-7.1's install command must be `pnpm add next@~15.5 react@~19 react-dom@~19` and verification must `grep -E '"next":\s*"~?\^?15'`. Risk: 15.5.x is in maintenance mode, not feature mode — no new App Router improvements, slower bug fixes.

**Recommendation: take Option A and bump every "Next.js 15" reference to "Next.js 16."** The `output: 'standalone'`, `headers()`, `next/font`, `next/image`, route-handler streaming patterns all work identically in 16 — no rewrite needed.

---

### Claim 2 — Tailwind 4 stable ✅

`tailwindcss@4.3.0` is `latest`. CSS-first config (`@theme { ... }` directive inside `globals.css`, no `tailwind.config.ts` required) is the documented canonical approach since 4.0.0 (2025). `tailwind.config.ts` is still SUPPORTED as a JS-extension escape hatch but `@theme` is the primary path.

**Note:** `docs/coding-standards.md` line 244 still references `tailwindConfig: './tailwind.config.ts'` in the Prettier config. With CSS-first Tailwind 4, that file doesn't exist. The `prettier-plugin-tailwindcss` v0.6+ auto-discovers `@theme` from `globals.css`. **Minor fix:** drop the `tailwindConfig` option from `prettier.config.mjs` OR point it to `./app/globals.css`.

---

### Claim 3 — `@tailwindcss/postcss` plugin ✅

Exact package name. Versioned in lockstep with `tailwindcss` (`4.3.0` matches). `postcss.config.mjs` snippet in best-practices/04 §2 is correct.

---

### Claim 4 + 5 + 6 — shadcn/ui CLI + New York style ✅

- CLI package: `shadcn@4.10.0` (a major-version-bumped CLI; not the same as "shadcn v4" the styling system). `shadcn-ui@0.9.5` is the deprecated old package — do not use.
- `pnpm dlx shadcn@latest init` is canonical (matches official docs).
- New York style is one of two ships: `default` and `new-york`. New York uses sharper borders + `lucide-react` icons. Compatible with Tailwind 4 CSS-first config — generated `components.json` carries `"tailwind": { "config": "", "css": "app/globals.css", "cssVariables": true }` (empty `config` = CSS-first mode).
- Generated `components/ui/*.tsx` components reference Tailwind 4 tokens via CSS variables (e.g., `bg-background`, `text-foreground`) — these resolve through the `@theme` block.

**Caveat for ChaosLab:** the ux-spec's `@theme` block introduces custom tokens (`--color-attack-red`, `--color-pass-green`, etc.) that DO NOT collide with shadcn's defaults (`--color-background`, `--color-foreground`, `--color-primary`, etc.). Both can coexist in one `@theme` block. Spec is fine.

---

### Claim 7 — visx versions ⚠️ BLOCKING (React 19 conflict)

**Spec says:** install `@visx/{group,scale,shape,grid,axis,responsive,text}` (architecture.md L188; story-7.6 L29).

**Reality:**

- All 7 packages at **3.12.0** (`latest`). Co-versioned, no version skew.
- **BUT:** visx 3.x peerDependencies are `react: ^16.0.0-0 || ^17.0.0-0 || ^18.0.0-0` — **React 19 NOT listed.**
- Spec also pins `react@19.x` (architecture.md L185).
- visx 4.0.0-alpha.11 adds React 19 to peerDeps (`^16.14 || ^17 || ^18 || ^19`) but it's **alpha** — `4.0.0` stable not yet released. The Airbnb visx repo has been in maintenance mode through 2026.

**Impact:**

- `pnpm install` with strict-peer-deps will WARN or FAIL on the visx + react@19 combination. `pnpm` defaults to `auto-install-peers=true` and `strict-peer-dependencies=false` in newer versions, so installs usually succeed but emit `WARN unmet peer dependency` — silent at install, a real risk in CI if `--strict-peer-dependencies` is on.
- At runtime visx 3.12.0 + React 19 works in practice (visx uses standard React APIs, no concurrent-rendering hazards). The community has run this combo on React 19 since late 2024. But it's UNDOCUMENTED COMPATIBILITY.

**Required amendment (architecture.md + story-7.6):**

Add an `.npmrc` override OR a `package.json#pnpm.overrides` entry to silence the peer warning, OR pin visx to `4.0.0-alpha.11` and accept alpha risk.

**Recommendation:** Use visx 3.12.0 and add to `apps/chaoslab-web/package.json`:

```json
"pnpm": {
  "peerDependencyRules": {
    "allowedVersions": {
      "react@^19": ["@visx/*"]
    }
  }
}
```

And document this in `architecture.md` ADR (or under "Required external libraries"). Story-7.6 should call out the override in "Notes for coding agent."

---

### Claim 8 — Framer Motion v12 ✅

- `framer-motion@12.40.0` (2026-05-21) is `latest`. Active.
- `motion.div` import path: `import { motion } from 'framer-motion'` — STABLE in v12. (Note: the project rebranded to `motion` package at `motion.dev` mid-2024; both `framer-motion` and the new `motion` package now resolve to the same `12.40.0`. `motion.dev` is the canonical website now, not `framer.com/motion`.)
- Stagger via per-cell `transition={{ delay: i * 0.04 }}` — STABLE pattern.
- `useReducedMotion()` — STABLE since v10, unchanged in v12.
- `motion.path` `pathLength` animation (used in story-7.6 PATCH marker) — STABLE.

**Minor note:** best-practices/04 §16 source link is `https://www.framer.com/motion/`. That redirects to `https://motion.dev/` now. Non-blocking.

---

### Claim 9 — Zustand v5 ✅

`zustand@5.0.14` (`latest`). Peer: react >=18. Stable. `create()` API unchanged from v4 (no migration needed for the spec'd usage pattern in best-practices/04 §6).

---

### Claim 10 — TanStack Query v5 + nuqs ✅

- `@tanstack/react-query@5.101.0`. React 18/19 peer. Stable.
- `nuqs@2.8.9`. Peer: `next>=14.2.0`, React 18.2+. v2 introduced typed URL parsers — stable.

---

### Claim 11 — Playwright + `toHaveScreenshot()` ✅

- `@playwright/test@1.60.0` is `latest`.
- `toHaveScreenshot(name, { maxDiffPixelRatio })` API has been GA since 1.31 (2023) — fully stable.
- The `webServer: { command: 'pnpm dev', url, reuseExistingServer: !CI }` config pattern in best-practices/04 §14 is canonical.

---

### Claim 12 — `output: 'standalone'` + `server.js` ✅

Confirmed against Next.js docs (https://nextjs.org/docs/app/api-reference/config/next-config-js/output#automatically-copying-traced-files). `output: 'standalone'` produces `.next/standalone/server.js` (and copies `node_modules` traces). The Dockerfile in best-practices/04 §9 is correct (3-stage build → `CMD ["node", "server.js"]` on port 8080). This pattern is unchanged from Next.js 13 → 16.

---

### Claim 13 — `sahil-visual-loop` skill integration ✅

- Skill exists at `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md`.
- `templates/` directory contains all 8 files referenced in story-7.12:
  - `playwright-config.ts`, `visual-pages-spec.ts`, `visual-check.sh`, `visual_reviewer.py`, `visual-reviewer-agent.md`, `visual-review-command.md`, `capture-anchor.ts`, `claude-md-addendum.md`, plus `setup-visual.sh`.
- Story-7.12's file modification map matches the skill's documented `Output — what the skill produces` table exactly. The 4 anchor screenshot names in story-7.12 match the names referenced in `docs/ux-spec.md` §"Visual loop integration."
- The skill's "Hard rules" (anchor immutable, vision review via SDK not Read tool, Playwright as CLI not MCP, no `autoVerify` flag, hook exits 0 always) are all correctly mirrored in story-7.12's "Notes for coding agent."
- The 7-tells slop criteria + verdict thresholds (`slop_score ≤ 2 AND blocking_count == 0`) in the skill match ux-spec L260.

**One missing requirement in story-7.12 to add:** the skill says `ANTHROPIC_API_KEY` env must be set. Story-7.12's notes mention this but don't list it in the BDD acceptance criteria. Recommend adding a Given/When/Then verifying `ANTHROPIC_API_KEY` is set when the hook fires.

---

## Required amendments (consolidated)

1. **BLOCKING — architecture.md L14, L184; story-7.1 L24, L65, L157:** Replace "Next.js 15" with "Next.js 16" throughout. Update `pnpm add next` to `pnpm add next@^16 react@^19 react-dom@^19`. Update story-7.1 BDD `grep` checks to assert `"next":\s*"\^?16` (and `react` ^19). Verify breaking-change list: async `cookies()`, `headers()`, `draftMode()`, `params`, `searchParams`; Turbopack now default; `experimental.*` audit.
2. **BLOCKING — architecture.md TS table; story-7.6:** Add `pnpm.peerDependencyRules` override (or `.npmrc` `auto-install-peers=true` + `strict-peer-dependencies=false`) to permit visx 3.12.0 + React 19. Document the version skew + that we accept it (community-validated, alpha v4 not yet stable).
3. **MINOR — coding-standards.md L244:** Drop `tailwindConfig: './tailwind.config.ts'` from `prettier.config.mjs` (Tailwind 4 CSS-first has no JS config file). Plugin auto-discovers from `globals.css`.
4. **MINOR — best-practices/04 L523:** Update source URL `framer.com/motion` → `motion.dev`.
5. **MINOR — story-7.12:** Add a BDD criterion that `ANTHROPIC_API_KEY` env var is set when the visual-reviewer hook fires (or document the SDK call failure mode).

---

## One-line summary

**Spec is stale on Next.js (specced 15, registry is on 16 since 2025-Q3) and silently mis-pinned on visx peer deps for React 19 — fix both before Epic 7 starts, every other frontend pin is correct as of 2026-06-03.**
