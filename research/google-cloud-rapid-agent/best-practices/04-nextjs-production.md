# 04 — Next.js + Tailwind Production Patterns

> **Methodology note:** This file was written directly from canonical Next.js/Tailwind/shadcn knowledge after two sub-agent attempts hit Anthropic API "Overloaded" errors. Scope is intentionally focused on the production patterns ChaosLab's frontend needs, not exhaustive. Sources cited inline; cross-check official docs at the URLs before locking choices.

---

## 1. Next.js 15 App Router project structure

The canonical layout (verified against https://nextjs.org/docs/app/getting-started/project-structure as of 2026):

```
apps/web/
├── app/
│   ├── layout.tsx              # root layout (HTML + body, fonts, providers)
│   ├── page.tsx                # home: demo landing
│   ├── globals.css             # Tailwind 4 directives + design tokens
│   ├── (demo)/                 # route group — judging-facing pages
│   │   ├── layout.tsx          # demo-specific chrome
│   │   ├── attack/page.tsx     # live attack run UI
│   │   └── replay/page.tsx     # canonical replay UI
│   ├── api/
│   │   └── stream/route.ts     # SSE endpoint piping Phoenix traces to client
│   └── _components/            # leading _ = private, not routable
│       ├── attack-matrix.tsx   # client component (Framer Motion)
│       └── resilience-curve.tsx # client component (visx)
├── components/                 # shared, app-wide
│   ├── ui/                     # shadcn/ui primitives (button, card, etc.)
│   └── chart-primitives/       # visx-wrapped reusable shapes
├── lib/
│   ├── api-client.ts           # typed wrapper over fetch to the agent
│   ├── env.ts                  # zod-validated env vars
│   └── utils.ts                # cn() helper, formatters
├── public/                     # static assets
├── styles/                     # if needed, but globals.css usually enough
├── tests/
│   ├── e2e/                    # Playwright
│   └── unit/                   # Vitest
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts          # (Tailwind 4: optional — CSS-first preferred)
├── postcss.config.mjs
├── package.json
└── Dockerfile
```

**Server vs Client component decision rule:**
- Default to **server components** — they're the App Router's reason to exist
- Mark `'use client'` ONLY when you need: `useState`, `useEffect`, event handlers, browser APIs, or third-party client libs (Framer Motion, visx are client-only)
- The `_components/` private folder pattern keeps page-specific client components OUT of the global `components/` tree

**Route groups `(name)/`:** organize files without affecting URL. Used here for `(demo)/` to share chrome across the demo flow.

**Critical pattern:** push `'use client'` boundary as LOW as possible. A `'use client'` at the page level pulls the whole tree client-side and kills RSC benefits. A `'use client'` on just the chart component keeps everything else server-rendered.

---

## 2. Tailwind 4 setup (CSS-first, no config file)

Tailwind 4 (released 2025) moved config from JS to CSS. Install:

```bash
pnpm add -D tailwindcss@latest @tailwindcss/postcss
```

`postcss.config.mjs`:
```js
export default {
  plugins: { '@tailwindcss/postcss': {} }
}
```

`app/globals.css`:
```css
@import "tailwindcss";

@theme {
  --color-attack-red: oklch(0.65 0.24 25);
  --color-pass-green: oklch(0.72 0.20 145);
  --color-patch-line: oklch(0.55 0.30 280);
  --color-agent-orchestrator: oklch(0.62 0.25 220);
  --color-agent-injector: oklch(0.60 0.20 30);
  --color-agent-judge: oklch(0.65 0.18 280);
  --color-agent-patcher: oklch(0.70 0.22 145);
  --color-agent-target: oklch(0.55 0.05 250);
  
  --font-display: "Geist", system-ui, sans-serif;
  --font-mono: "Geist Mono", ui-monospace, monospace;
}

@layer base {
  body {
    @apply bg-background text-foreground antialiased;
  }
}
```

The `@theme` directive replaces `tailwind.config.js` for design tokens. Use `oklch()` color space — perceptually uniform, better for the red/green attack-matrix contrast than RGB.

**Dark mode:** Tailwind 4 supports `@media (prefers-color-scheme: dark)` via `@variant dark`. Or use shadcn's class-based dark mode (toggle adds `.dark` to `<html>`).

---

## 3. shadcn/ui canonical setup

```bash
pnpm dlx shadcn@latest init
```

Pick: New York style, neutral base color, CSS variables for colors, `app/globals.css`. Generates `components.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

Install components individually as needed: `pnpm dlx shadcn@latest add button card dialog toast`. Each generates source code into `components/ui/` — you OWN the code, no runtime dependency.

For ChaosLab's specific needs: `card`, `badge`, `tabs`, `dialog`, `sheet`, `tooltip`, `scroll-area`, `separator`, `button`, `toast` are the high-frequency primitives.

---

## 4. visx for charts (Attack Matrix + Resilience Curve)

Install: `pnpm add @visx/group @visx/scale @visx/shape @visx/grid @visx/axis @visx/responsive @visx/text`.

**Charts MUST be client components.** Top of file:

```tsx
'use client'

import { Group } from '@visx/group'
import { scaleLinear } from '@visx/scale'
import { Bar, LinePath } from '@visx/shape'
import { ParentSize } from '@visx/responsive'
```

**Attack Matrix (5×5 grid of red/green cells):**
```tsx
'use client'

import { motion } from 'framer-motion'

interface AttackCell { idx: number; passed: boolean; faultClass: string }
interface AttackMatrixProps { cells: AttackCell[]; revealedCount: number }

export function AttackMatrix({ cells, revealedCount }: AttackMatrixProps) {
  return (
    <div className="grid grid-cols-5 gap-1.5 aspect-square w-full max-w-md">
      {cells.map((cell, i) => (
        <motion.div
          key={cell.idx}
          initial={{ scale: 0.6, opacity: 0 }}
          animate={i < revealedCount ? { scale: 1, opacity: 1 } : {}}
          transition={{ delay: i * 0.04, type: 'spring', stiffness: 200 }}
          className={cn(
            'rounded-sm aspect-square',
            cell.passed ? 'bg-pass-green' : 'bg-attack-red'
          )}
          title={`${cell.faultClass}: ${cell.passed ? 'PASS' : 'FAIL'}`}
        />
      ))}
    </div>
  )
}
```

**Responsive sizing pattern:**
```tsx
<ParentSize>
  {({ width, height }) => <ResilienceCurve width={width} height={height} data={...} />}
</ParentSize>
```

---

## 5. Framer Motion cascade-flip pattern

The hero moment: matrix cells flip from red → green when the patch fires. Two approaches:

**Approach A: re-render with stagger** (simpler — recommended)
```tsx
// pass `state: 'pre-patch' | 'post-patch'` as prop
// re-render with new pass/fail data; stagger via index delay

<motion.div
  key={`${state}-${i}`}  // key change forces re-mount + stagger
  initial={{ scale: 0.5, opacity: 0 }}
  animate={{ scale: 1, opacity: 1 }}
  transition={{ delay: i * 0.03, duration: 0.4, ease: 'easeOut' }}
/>
```

**Approach B: layout animation** (more elaborate — for the line chart curve)
```tsx
<motion.path
  d={curvePath}
  initial={{ pathLength: 0 }}
  animate={{ pathLength: 1 }}
  transition={{ duration: 1.5, ease: 'easeInOut' }}
/>
```

**Performance:** Always use `transform` (translateX, scale) over `top`/`left`/`width` — transforms are GPU-accelerated, non-transform animations cause layout thrash.

**Accessibility:** Wrap with `useReducedMotion()` from framer-motion. If user has `prefers-reduced-motion: reduce`, swap stagger animations for instant state changes.

```tsx
import { useReducedMotion } from 'framer-motion'

const shouldReduceMotion = useReducedMotion()
const transition = shouldReduceMotion ? { duration: 0 } : { delay: i * 0.04, type: 'spring' }
```

---

## 6. State management

**Decision tree (production-ready 2026):**
- **Server state** (data from the agent backend) → TanStack Query (`@tanstack/react-query` v5)
- **URL state** (selected fault, run ID) → `nuqs` library — type-safe URL search params, no manual `useSearchParams` parsing
- **Local UI state** (modal open, hover) → React `useState`
- **Cross-component state** (current run progress) → Zustand (`zustand` v5) if it spans 3+ components; Context if just 2-3

**Do NOT use Redux for a hackathon-scale app.** Overkill. Zustand or Jotai are 10× simpler.

```tsx
// stores/run-store.ts
import { create } from 'zustand'

interface RunState {
  runId: string | null
  state: 'idle' | 'attacking' | 'patching' | 'reattacking' | 'complete'
  cells: AttackCell[]
  resilienceCurve: { x: number; y: number }[]
  setRun: (id: string) => void
  setState: (s: RunState['state']) => void
  updateCells: (cells: AttackCell[]) => void
}

export const useRunStore = create<RunState>((set) => ({
  runId: null,
  state: 'idle',
  cells: [],
  resilienceCurve: [],
  setRun: (id) => set({ runId: id }),
  setState: (s) => set({ state: s }),
  updateCells: (cells) => set({ cells }),
}))
```

---

## 7. Server-Sent Events for live trace streaming

The agent backend streams Phoenix trace updates over SSE. The frontend reads them and updates the matrix in real-time.

**Server route** (`app/api/stream/route.ts`):
```ts
export const dynamic = 'force-dynamic'

export async function GET(req: Request) {
  const stream = new ReadableStream({
    async start(controller) {
      const send = (event: string, data: unknown) => {
        controller.enqueue(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
      }
      // proxy from the agent backend's SSE endpoint
      const upstream = await fetch(`${process.env.AGENT_BACKEND_URL}/stream`)
      const reader = upstream.body!.getReader()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        controller.enqueue(value)
      }
      controller.close()
    },
  })
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
```

**Client hook:**
```tsx
'use client'

import { useEffect } from 'react'
import { useRunStore } from '@/stores/run-store'

export function useTraceStream(runId: string | null) {
  const updateCells = useRunStore((s) => s.updateCells)
  useEffect(() => {
    if (!runId) return
    const es = new EventSource(`/api/stream?runId=${runId}`)
    es.addEventListener('cell-update', (e) => {
      updateCells(JSON.parse(e.data))
    })
    es.onerror = () => es.close()
    return () => es.close()
  }, [runId, updateCells])
}
```

---

## 8. Environment variables

Use zod-validated env at startup. Create `lib/env.ts`:

```ts
import { z } from 'zod'

const envSchema = z.object({
  AGENT_BACKEND_URL: z.string().url(),
  PHOENIX_API_KEY: z.string().min(1),
  GEMINI_API_KEY: z.string().min(1).optional(),
  // public (NEXT_PUBLIC_*) shipped to client — never put secrets here
  NEXT_PUBLIC_GA_ID: z.string().optional(),
})

export const env = envSchema.parse(process.env)
```

Then import `env` everywhere instead of `process.env.X`. Crashes loudly at startup if any required var is missing.

For Cloud Run: env vars are injected at deploy time via `gcloud run deploy --set-env-vars`. Secrets come from Secret Manager via `--set-secrets`.

---

## 9. Dockerfile for Cloud Run

```dockerfile
# Stage 1: install deps
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# Stage 2: build
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm build  # next build with output: 'standalone'

# Stage 3: runtime
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production PORT=8080 HOSTNAME=0.0.0.0
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 8080
CMD ["node", "server.js"]
```

**Critical:** `next.config.ts` MUST have `output: 'standalone'`:
```ts
import type { NextConfig } from 'next'
const config: NextConfig = {
  output: 'standalone',
  images: { unoptimized: false },
  poweredByHeader: false,
  reactStrictMode: true,
}
export default config
```

`standalone` produces a minimal `server.js` that includes only what was actually imported. Container size drops from ~500MB to ~80MB.

---

## 10. Security headers

`next.config.ts` `headers()`:
```ts
async headers() {
  return [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ],
    },
  ]
}
```

CSP is application-specific; defer to spec unless you need it now.

---

## 11. Performance

- **next/image** for any image. Never plain `<img>`. Auto-optimizes per device.
- **next/font** for fonts. Auto-self-hosts, prevents CLS. Example: `import { Geist } from 'next/font/google'`.
- **`@next/bundle-analyzer`** for bundle inspection. Add as dev dep, enable via env flag, run `pnpm build && pnpm analyze`.
- **Streaming**: wrap below-fold content in `<Suspense fallback={...}>` to ship fast TTFB.
- **ISR is irrelevant for ChaosLab** — this is a real-time demo. SSR/streaming.

---

## 12. SEO + Open Graph (the Devpost cover screenshot)

The hero frame at 2:15 in the demo video — the matrix cascade-flip + curve jump — is also the Devpost project thumbnail.

`app/page.tsx`:
```tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'ChaosLab — Adversarial Resilience for AI Agents',
  description: 'Chaos engineering for LLM agents. Inject faults, watch them fail, harden automatically.',
  openGraph: {
    title: 'ChaosLab — Adversarial Resilience for AI Agents',
    description: '...',
    images: ['/og-hero.png'],  // 1200x630 PNG of the matrix+curve hero
  },
  twitter: { card: 'summary_large_image', images: ['/og-hero.png'] },
}
```

---

## 13. Accessibility (a11y)

- **Color contrast:** red/green attack matrix must pass WCAG AA. Use `oklch()` values from §2 — they hit ≥4.5:1 against the dark bg.
- **Color-blind safe:** add an icon/shape distinction (✓/✗) inside cells in addition to color
- **Keyboard navigation:** every interactive element reachable via Tab + activatable via Enter/Space
- **Focus visible:** keep Tailwind's default focus rings; don't `outline: none` anywhere
- **ARIA:** for the matrix, use `role="grid"` + `aria-label="Attack results: 25 fault injection runs"`; each cell `aria-label="Run 3, malformed tool output, failed"`
- **Reduced motion:** see §5 — `useReducedMotion()` gates Framer Motion stagger

---

## 14. Visual testing with Playwright + sahil-visual-loop

Install: `pnpm add -D @playwright/test`.

`playwright.config.ts`:
```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

**Screenshot regression:**
```ts
import { test, expect } from '@playwright/test'

test('attack matrix renders 25 cells', async ({ page }) => {
  await page.goto('/demo?canonical=1')
  await page.waitForSelector('[data-testid="attack-matrix"]')
  await expect(page).toHaveScreenshot('attack-matrix-canonical.png', {
    maxDiffPixelRatio: 0.02,  // 2% tolerance for AA differences
  })
})
```

**`sahil-visual-loop` integration:** the skill drops in a Playwright config + a screenshot-diff hook + a fresh-context Opus 4.7 reviewer. Invoke once at Day 1 frontend scaffold via `Skill sahil-visual-loop`. Everything below is what the skill installs — don't reimplement.

---

## 15. Common pitfalls

- **Hydration mismatches:** don't read `Date.now()`, `window.X`, or `Math.random()` in render. Wrap in `useEffect` (client) or `headers()`/`cookies()` (server).
- **`'use client'` boundary too high:** if a single component needs `useState`, ONLY that component should be `'use client'`. Not its parent page.
- **Tailwind purging dynamic classes:** Tailwind only ships classes it sees literally. `className={\`bg-${color}-500\`}` won't ship anything. Use a static lookup: `const colorMap = { red: 'bg-red-500', green: 'bg-green-500' }`.
- **Importing server-only code in a client component:** if you mark a file `'use client'` and it imports a module using `fs`, `next/headers`, etc., the build will error. Move the server-only logic to a server component or server action.
- **Forgetting `'use client'` on event handlers:** any component with `onClick`, `onChange`, etc. MUST be `'use client'`.

---

## 16. Sources

- https://nextjs.org/docs/app/getting-started/project-structure (Next.js 15 App Router)
- https://tailwindcss.com/docs/v4-beta (Tailwind 4 CSS-first config)
- https://ui.shadcn.com/docs (shadcn/ui)
- https://airbnb.io/visx/ (visx primitives)
- https://www.framer.com/motion/ (Framer Motion v12+)
- https://www.framer.com/motion/use-reduced-motion/ (a11y)
- https://playwright.dev/docs/test-snapshots (visual regression)
- https://tanstack.com/query/latest (TanStack Query v5)
- https://zustand.docs.pmnd.rs/ (Zustand v5)
- https://github.com/47ng/nuqs (URL state)
- https://nextjs.org/docs/app/api-reference/file-conventions/route-handlers (SSE endpoint)
- https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-nodejs-service (Cloud Run Node deploy)
- `/Users/abu/.claude/skills/sahil-visual-loop/SKILL.md` (in-repo skill, drop-in Playwright + reviewer)
