# Story — Env validation (zod) + Cloud Run Dockerfile

**ID:** story-7.3-env-and-dockerfile
**Epic:** Epic 7 — chaoslab-web frontend
**Depends on:** story-7.1-nextjs-scaffold
**Estimate:** ~1h
**Status:** PENDING
**tags:** [frontend, p0, ui]

---

## User story

**As a** coding agent preparing chaoslab-web for Cloud Run deployment
**I want to** add a zod-validated env loader (`lib/env.ts`), a multi-stage Cloud Run Dockerfile producing a <150MB image, and a tight `.dockerignore`
**So that** the app crashes loudly at startup on missing env vars (no silent `undefined` surprises during the demo), the container is small enough for fast Cloud Run cold-starts, and the GitHub Actions staging deploy pipeline has a verified artifact path

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-web/lib/env.ts` — NEW — zod schema validates `AGENT_BACKEND_URL` (URL, required), `NEXT_PUBLIC_GA_ID` (optional), `NODE_ENV` (enum); exports `env` parsed at module load; throws with a clear message listing missing vars per `best-practices/04 §8`. ≤80 LOC.
- `apps/chaoslab-web/Dockerfile` — NEW — multi-stage build per `best-practices/04 §9`: `deps` stage (alpine + pnpm install --frozen-lockfile), `build` stage (next build with `output: 'standalone'`), `runtime` stage (alpine + nextjs user 1001, COPY standalone + .next/static + public, EXPOSE 8080, CMD `node server.js`). Final image <150MB. ≤80 LOC.
- `apps/chaoslab-web/.dockerignore` — NEW — excludes `node_modules`, `.next`, `.git`, `tests`, `screenshots`, `playwright-report`, `*.log`, `.env*`, `README.md`, `docs/`, `.claude/`
- `apps/chaoslab-web/package.json` — UPDATE — add `zod` to `dependencies`

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given lib/env.ts has been created
When `grep -E "import\s*\{\s*z\s*\}\s*from\s*['\"]zod['\"]" apps/chaoslab-web/lib/env.ts` runs
Then exit code is 0

Given lib/env.ts validates AGENT_BACKEND_URL
When `grep -E "AGENT_BACKEND_URL.*z\.string\(\)\.url\(\)" apps/chaoslab-web/lib/env.ts` runs
Then exit code is 0

Given the Dockerfile has been written
When `grep -cE "^FROM node:22-alpine AS (deps|build|runtime)" apps/chaoslab-web/Dockerfile` runs
Then output is 3 (multi-stage)

Given the Dockerfile has been written
When `grep -E "USER nextjs" apps/chaoslab-web/Dockerfile` runs
Then exit code is 0

Given the Dockerfile has been written
When `grep -E "EXPOSE 8080" apps/chaoslab-web/Dockerfile` runs
Then exit code is 0

Given .dockerignore has been written
When `grep -cE "^(node_modules|\.next|\.git|tests|\.env)" apps/chaoslab-web/.dockerignore` runs
Then output is ≥ 5

Given the Dockerfile is valid
When `docker build -t chaoslab-web:test apps/chaoslab-web` runs (with AGENT_BACKEND_URL=http://stub:8000 as build arg if needed)
Then exit code is 0

Given the image was built
When `docker image inspect chaoslab-web:test --format '{{.Size}}'` runs
Then the value is < 157286400 (150 MB in bytes)

Given env.ts is invoked at module load with AGENT_BACKEND_URL unset
When `AGENT_BACKEND_URL= pnpm --filter chaoslab-web exec node -e "require('./apps/chaoslab-web/lib/env').env"` runs
Then exit code is non-zero (the zod parse throws — fail-fast required)

Given AGENT_BACKEND_URL=http://localhost:8001 is set
When `AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build` runs
Then exit code is 0
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-web/lib/env.ts
test -f apps/chaoslab-web/Dockerfile
test -f apps/chaoslab-web/.dockerignore

# zod imported
grep -E "import\s*\{\s*z\s*\}\s*from\s*['\"]zod['\"]" apps/chaoslab-web/lib/env.ts
grep -E "AGENT_BACKEND_URL.*z\.string\(\)\.url\(\)" apps/chaoslab-web/lib/env.ts

# Dockerfile multi-stage
test "$(grep -cE '^FROM node:22-alpine AS (deps|build|runtime)' apps/chaoslab-web/Dockerfile)" -eq 3
grep -E "USER nextjs" apps/chaoslab-web/Dockerfile
grep -E "EXPOSE 8080" apps/chaoslab-web/Dockerfile

# .dockerignore covers the danger zones
test "$(grep -cE '^(node_modules|\.next|\.git|tests|\.env)' apps/chaoslab-web/.dockerignore)" -ge 5

# zod deps present
node -e "const p=require('./apps/chaoslab-web/package.json'); process.exit(p.dependencies.zod ? 0 : 1)"

# Build clean (env satisfied)
AGENT_BACKEND_URL=http://localhost:8001 pnpm --filter chaoslab-web build

# Docker image builds + size check
docker build -t chaoslab-web:test apps/chaoslab-web
SIZE=$(docker image inspect chaoslab-web:test --format '{{.Size}}')
echo "image size: $SIZE bytes"
[ "$SIZE" -lt 157286400 ]

# Fail-fast on missing env (expected failure → exit non-zero, story passes)
( unset AGENT_BACKEND_URL && pnpm --filter chaoslab-web exec node -e "require('./lib/env').env" ) && \
  { echo "FAIL: env should have thrown on missing AGENT_BACKEND_URL"; exit 1; } || \
  echo "PASS: env throws on missing var as expected"

# 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-web/lib/env.ts apps/chaoslab-web/Dockerfile

echo "story-7.3 verification: PASS"
```

---

## Notes for coding agent

- `lib/env.ts` is the ONLY place `process.env.X` is read directly. Every other file imports `env` from `lib/env.ts`. Enforced by ESLint pattern (consider a `no-restricted-imports` or simply by convention + code review).
- The zod schema for this story: `AGENT_BACKEND_URL` (required URL), `NODE_ENV` (`z.enum(['development', 'production', 'test'])`), `NEXT_PUBLIC_GA_ID` (optional string). Future stories may add: `PHOENIX_API_KEY`, `GEMINI_API_KEY`, `GITLAB_TOKEN`. Add them as they become needed — don't pre-add.
- `NEXT_PUBLIC_*` vars are shipped to the client bundle. NEVER put secrets there. Document this with a comment in env.ts: `// NEXT_PUBLIC_* are CLIENT-side; never put secrets here.`
- The Dockerfile uses `node:22-alpine` base. Alpine is REQUIRED — `standalone` output + alpine is the documented path to <150MB. `bullseye-slim` would push us over.
- `output: 'standalone'` is set in `next.config.ts` from story-7.1. Verify with `grep "standalone" apps/chaoslab-web/next.config.ts` before building. If missing, the runtime stage `COPY --from=build /app/.next/standalone ./` will fail.
- The non-root `nextjs` user with uid 1001 is REQUIRED for Cloud Run security best-practices. Do NOT run as root.
- `corepack enable` in deps + build stages so pnpm is available without a separate install.
- `.dockerignore` is critical for build performance and final image size — without it, the `COPY . .` step in the build stage pulls in `node_modules`, `.next`, `screenshots/`, etc., bloating layers.
- Build context for `docker build`: `apps/chaoslab-web` (not the repo root). The Dockerfile must reference paths relative to that.
- If pnpm-lock.yaml is at the repo root (it is — monorepo), the deps stage needs to handle that. Two options: (a) copy the lockfile from the repo root via build context tricks, or (b) generate a local `pnpm-lock.yaml` for the build via `pnpm install --lockfile-only` before docker build. Use option (a): set build context to repo root (`docker build -t chaoslab-web:test -f apps/chaoslab-web/Dockerfile .`) and `COPY pnpm-lock.yaml pnpm-workspace.yaml package.json apps/chaoslab-web/package.json ./` then `pnpm install --frozen-lockfile --filter chaoslab-web`. Adjust shell verification accordingly.
- The image-size check (<150MB) is the gate. If you cross it, the most likely culprits: forgot `output: 'standalone'`, forgot `.dockerignore`, used non-alpine base, or accidentally COPY'd `node_modules`.
- Health-check endpoint (`/api/health`) is NOT in this story. It's a route — story-7.9 or a future story handles it. Cloud Run gracefully handles missing health endpoint (falls back to startup probe on the container port).
