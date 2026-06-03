# Story — chaoslab-agent Dockerfile + Cloud Run Deploy Wiring

**ID:** story-4.6-chaoslab-agent-deploy
**Epic:** Epic 4 — ChaosLab orchestrator + Phoenix tool wrappers
**Depends on:** story-4.1-agent-entrypoint
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, docker, cloud-run, infra]

---

## User story

**As a** ChaosLab orchestrator
**I want to** have a reproducible multi-stage Docker build that produces a small (≤800MB), non-root Python 3.12 image running `uvicorn chaoslab_agent.main:app` on port 8080
**So that** Epic 1's `staging-deploy.yaml` GitHub Action can build → push → deploy the service to Cloud Run with a single `gcloud run deploy --image=$ARTIFACT_REGISTRY/chaoslab-agent:$GITHUB_SHA` invocation, and the "build once, promote everywhere" ADR-008 pattern works end to end

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/Dockerfile` — NEW — multi-stage build:
  - **Stage 1 (`builder`):** `FROM python:3.12-slim AS builder`. Install `uv` via `pip install --no-cache-dir uv==0.5.x` (pin minor). Set `WORKDIR /app`. `COPY pyproject.toml uv.lock ./` then `RUN uv sync --frozen --no-dev --no-install-project` (caches deps in a layer). `COPY src/ ./src/` then `RUN uv sync --frozen --no-dev` (installs the local package). Strip caches: `RUN find /app/.venv -name "__pycache__" -exec rm -rf {} +`.
  - **Stage 2 (`runtime`):** `FROM python:3.12-slim AS runtime`. Create a non-root user: `RUN groupadd -g 1000 chaoslab && useradd -u 1000 -g 1000 -m -s /bin/bash chaoslab`. `WORKDIR /app`. `COPY --from=builder --chown=chaoslab:chaoslab /app/.venv /app/.venv`. `COPY --from=builder --chown=chaoslab:chaoslab /app/src /app/src`. `ENV PATH="/app/.venv/bin:$PATH"`. `ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1`. `USER chaoslab`. `EXPOSE 8080`. `HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import httpx; httpx.get('http://localhost:8080/health').raise_for_status()"`. `CMD ["uvicorn", "chaoslab_agent.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]`. ~50 lines.
- `apps/chaoslab-agent/.dockerignore` — NEW — excludes `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `tests/`, `htmlcov/`, `.coverage`, `.env*` (never bake env files into the image), `.git/`, `README.md`, `*.md` (not needed in runtime), `Dockerfile`, `.dockerignore`. ~25 lines.
- `apps/chaoslab-agent/README.md` — UPDATE — add a "Container" section documenting the build + local-run flow:
  ```bash
  docker build -t chaoslab-agent:local apps/chaoslab-agent
  docker run --rm -p 8080:8080 --env-file apps/chaoslab-agent/.env chaoslab-agent:local
  curl http://localhost:8080/health
  ```
  ~25 added lines.
- `.github/workflows/staging-deploy.yaml` — UPDATE — append a `chaoslab-agent` deploy job (mirrors the existing `target-agent` job from S2.4 + the workflow defined in S1.6). Steps:
  - `actions/checkout@v4`
  - `google-github-actions/auth@v3` (WIF per ADR-009)
  - `google-github-actions/setup-gcloud@v3`
  - `gcloud auth configure-docker $REGION-docker.pkg.dev`
  - `docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/chaoslab-agent:${{ github.sha }} apps/chaoslab-agent`
  - `docker push $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/chaoslab-agent:${{ github.sha }}`
  - `gcloud run deploy chaoslab-agent --image=... --region=$REGION --platform=managed --service-account=chaoslab-agent-runtime@$PROJECT_ID.iam.gserviceaccount.com --min-instances=1 --max-instances=3 --memory=1Gi --cpu=1 --port=8080 --no-allow-unauthenticated --set-secrets="PHOENIX_API_KEY=phoenix-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,GITLAB_TOKEN=gitlab-token:latest" --set-env-vars="ENVIRONMENT=staging,JUDGE_LLM=gemini-3.5-flash,SERVICE_VERSION=${{ github.sha }},TARGET_DEFAULT_URL=https://target-agent-${PROJECT_HASH}.run.app" --tag=candidate --no-traffic`
  - Smoke test: `curl -fsS https://candidate---chaoslab-agent-$PROJECT_HASH.run.app/health` retries 5x
  - On smoke pass: `gcloud run services update-traffic chaoslab-agent --to-latest=100 --region=$REGION`
  ~50 added lines (workflow file may grow but stays under 400).
- `apps/chaoslab-agent/tests/integration/test_dockerfile.py` — NEW — at least 4 pytest cases marked `@pytest.mark.slow`:
  - `Dockerfile` exists at the expected path and starts with `FROM python:3.12-slim`.
  - `subprocess.run(["docker", "build", ...])` exits 0 (skipped if `DOCKER_AVAILABLE` env var unset — for CI dispatch on a labeled runner).
  - Built image size is < 800MB: `docker images --format "{{.Size}}"` parsed.
  - `docker run -d -p 8080:8080 -e PHOENIX_API_KEY=dummy -e GEMINI_API_KEY=dummy ...` starts the container; `curl http://localhost:8080/health` returns 200; container stops cleanly. (Validates the full Dockerfile contract end-to-end.)
  ~120 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given apps/chaoslab-agent/Dockerfile exists
When  `docker build -t chaoslab-agent:test apps/chaoslab-agent` runs
Then  exit code is 0
And   the build completes in under 5 minutes on a clean Docker cache

Given the image was built
When  `docker images --format "{{.Size}}" chaoslab-agent:test` is parsed
Then  the size is < 800MB

Given the built image
When  `docker inspect chaoslab-agent:test --format '{{.Config.User}}'` runs
Then  the output is "chaoslab" (non-root user, security gate)

Given the built image
When  `docker inspect chaoslab-agent:test --format '{{.Config.ExposedPorts}}'` runs
Then  the output contains "8080/tcp"

Given the built image
When  `docker run -d --name chaoslab-test -p 18080:8080 -e PHOENIX_API_KEY=dummy -e GEMINI_API_KEY=dummy -e JUDGE_LLM=gemini-3.5-flash chaoslab-agent:test` is run
Then  the container starts within 10 seconds
And   `curl -fsS http://localhost:18080/health` returns 200 within 15 seconds (allowing for startup)
And   the response JSON has status=="ok"

Given the running container
When  `docker exec chaoslab-test id -u` runs
Then  the output is 1000 (the non-root chaoslab uid)

Given .dockerignore exists
When  the file is parsed
Then  it contains entries for `.git/`, `.venv/`, `tests/`, `.env*`, `__pycache__/`

Given .github/workflows/staging-deploy.yaml exists
When  yq or grep extracts the `chaoslab-agent` job
Then  the job references `--set-secrets="PHOENIX_API_KEY=phoenix-api-key:latest,...,GITLAB_TOKEN=gitlab-token:latest"`
And   the job uses `${{ github.sha }}` for both the image tag AND the SERVICE_VERSION env var (ADR-008 build-once + version tagging)
And   the job runs `gcloud run deploy ... --tag=candidate --no-traffic` followed by a smoke-test and `update-traffic --to-latest=100` (ADR-008 blue/green)

Given `cd apps/chaoslab-agent && uv run pytest tests/integration/test_dockerfile.py -v -m slow` runs (when Docker is available)
When  the test suite completes
Then  at least 4 behavioral test cases pass

Given the 400-line guard runs
When  `python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/` runs
Then  exit code is 0
And   .github/workflows/staging-deploy.yaml is still ≤ 400 lines
```

---

## Shell verification

```bash
# 1) Build the image (this is THE primary BDD)
docker build -t chaoslab-agent:test apps/chaoslab-agent
# Must exit 0

# 2) Size check
SIZE_RAW=$(docker images --format "{{.Size}}" chaoslab-agent:test)
echo "Image size: $SIZE_RAW"
# Parse the size; verify < 800MB
docker images chaoslab-agent:test --format "{{.Size}}" | python3 -c "
import sys, re
s = sys.stdin.read().strip()
m = re.match(r'([\d.]+)(GB|MB)', s)
val, unit = float(m.group(1)), m.group(2)
mb = val * 1024 if unit == 'GB' else val
print(f'MB: {mb}')
assert mb < 800, f'Image too large: {mb} MB > 800 MB'
print('OK')
"
# Must print OK

# 3) Non-root user check
USER=$(docker inspect chaoslab-agent:test --format '{{.Config.User}}')
[ "$USER" = "chaoslab" ] || { echo "FAIL: not running as chaoslab user (got $USER)"; exit 1; }
echo "USER=chaoslab OK"

# 4) Port exposure
docker inspect chaoslab-agent:test --format '{{.Config.ExposedPorts}}' | grep -q "8080/tcp" || { echo "FAIL: port 8080 not exposed"; exit 1; }
echo "PORT=8080 OK"

# 5) End-to-end container smoke test
docker rm -f chaoslab-smoke 2>/dev/null || true
docker run -d --name chaoslab-smoke -p 18080:8080 \
  -e PHOENIX_API_KEY=dummy -e GEMINI_API_KEY=dummy -e JUDGE_LLM=gemini-3.5-flash \
  chaoslab-agent:test
sleep 8
curl -fsS http://localhost:18080/health | tee /tmp/health.json
grep -q '"status":"ok"' /tmp/health.json || { docker logs chaoslab-smoke; docker rm -f chaoslab-smoke; exit 1; }
docker rm -f chaoslab-smoke
echo "SMOKE OK"

# 6) Pytest Docker integration suite (when Docker is available)
if command -v docker >/dev/null 2>&1; then
  cd apps/chaoslab-agent && uv run pytest tests/integration/test_dockerfile.py -v -m slow 2>&1 | tee /tmp/docker-test.log
  grep -E "PASSED" /tmp/docker-test.log | wc -l
  # Must output ≥ 4
fi

# 7) Workflow file sanity
grep -q "chaoslab-agent" .github/workflows/staging-deploy.yaml || { echo "FAIL: workflow missing chaoslab-agent job"; exit 1; }
grep -q 'PHOENIX_API_KEY=phoenix-api-key:latest' .github/workflows/staging-deploy.yaml || { echo "FAIL: secrets binding missing"; exit 1; }
grep -q 'JUDGE_LLM=gemini-3.5-flash' .github/workflows/staging-deploy.yaml || { echo "FAIL: ADR-007 env var missing"; exit 1; }
grep -q '\-\-tag=candidate' .github/workflows/staging-deploy.yaml || { echo "FAIL: blue/green --tag=candidate missing (ADR-008)"; exit 1; }
echo "WORKFLOW OK"

# 8) 400-line guard
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/
# Must exit 0

# 9) green-light
.claude/scripts/green-light.sh
# Must exit 0
```

---

## Notes for coding agent

- **Multi-stage is non-negotiable** for the <800MB target. A single-stage `python:3.12-slim` + full `uv sync` lands around 1.2GB; splitting deps install in builder + copy `.venv` to runtime drops to ~600MB typical. If the size check fails, suspect (a) `tests/` accidentally COPYed in, (b) dev deps not excluded via `--no-dev`, (c) `__pycache__` directories not stripped.
- **Pin `uv` version.** `pip install uv==0.5.x` (or whatever is current at S1.1 time) — DO NOT pin to `latest` or omit the version. Reproducible builds are an ADR-008 requirement.
- **`uv sync --frozen --no-dev --no-install-project` then `--no-dev`.** The two-step pattern caches dep installs separately from local-package install — speeds up rebuild when only source changes. `--frozen` enforces the lockfile (rejects builds if `pyproject.toml` drifts from `uv.lock`).
- **Non-root user `chaoslab:1000:1000`.** Cloud Run requires the container to listen on `$PORT` (default 8080) and run as a non-root user is a hardening best-practice (and a security-reviewer gate per `sahil-pr-audit`). The BDD asserts both `Config.User == "chaoslab"` and `docker exec ... id -u == 1000`.
- **`--no-access-log` on uvicorn.** Cloud Run logs every HTTP request at the proxy layer already — uvicorn's access log is duplicate noise. Errors still surface via stderr. Reduces log-line volume by ~50%.
- **`HEALTHCHECK` is informational, not load-bearing.** Cloud Run does its own health probing via the `/health` endpoint configured separately (`gcloud run services update --liveness-probe-path=/health`). The Dockerfile `HEALTHCHECK` is for local `docker run` debugging.
- **`.dockerignore` MUST exclude `.env*`.** Baking `.env` files into images is a §14-adjacent slop pattern AND a security incident (leaked Phoenix keys in registry). The BDD asserts the entry.
- **`--no-allow-unauthenticated` on the agent service.** Per `architecture/06 §3` deployment ops + ADR-003: `chaoslab-agent` is called BY `chaoslab-web` (via service account) — not by humans directly. `chaoslab-web` Cloud Run service identity has `roles/run.invoker` on `chaoslab-agent`. Public traffic only hits the frontend.
- **`--min-instances=1` on the agent during judging window** per ADR-003. Cold start mitigation. Costs ~$7/svc/month — pre-budgeted in `architecture/06 §5`.
- **`--tag=candidate --no-traffic` then smoke test then `update-traffic --to-latest=100`** is the ADR-008 blue/green pattern. The BDD asserts both flags appear in the workflow. Free on Cloud Run — no excuse not to use it.
- **`SERVICE_VERSION=${{ github.sha }}`** lands in the env so `/health` returns the actual deployed commit SHA. Test asserts the health response includes the version.
- **`--set-secrets` mounts Secret Manager refs as env vars** (per ADR-009 + `infra/secret-manager-setup.sh` from S1.4). The actual secret values never appear in `staging-deploy.yaml`. Only references to `secret-name:latest`.
- **Local Docker test in `test_dockerfile.py`** uses dummy env values — the `/health` endpoint does NOT require a real Phoenix API key (it only checks settings load correctness). If the endpoint started calling Phoenix on health check, that would be a config bug — `/health` is a pure liveness probe.
- **Build time budget.** The build SHOULD complete in <5 min on GitHub Actions hosted runners (`ubuntu-latest` 4-core). If it exceeds 8 min, layer-caching is misconfigured — verify the COPY order separates deps (rarely-changing) from src (frequently-changing).
- **Cross-reference docs:**
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/architecture/06-deployment-ops.md` (Cloud Run service shape + cost model + min-instances rationale)
  - `/Users/abu/dev/hackathon/rapid-agents/research/google-cloud-rapid-agent/best-practices/02-cicd-github-actions.md` §1 (build-once-promote-everywhere) + §3 (WIF auth) + §13 (top-5 WIF failure modes)
  - `/Users/abu/dev/hackathon/rapid-agents/docs/architecture.md` ADR-003 (Cloud Run × 3), ADR-008 (build-once), ADR-009 (WIF)
  - Story `docs/stories/story-1.6-staging-deploy-workflow.md` for the existing workflow skeleton
  - Story `docs/stories/story-2.4-target-cloud-run-deploy.md` for the mirroring `target-agent` job pattern
