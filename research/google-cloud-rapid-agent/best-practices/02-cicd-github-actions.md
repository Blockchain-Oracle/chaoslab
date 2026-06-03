# 02 — CI/CD with GitHub Actions for ADK + Cloud Run

Scope: factual best-practices for a Python ADK agent + Next.js frontend + multi-service Cloud Run + Phoenix Cloud + Vertex AI stack. No project-specific opinions. URLs cited inline; full list at bottom.

Marker convention: `[UNVERIFIED]` = inferred from adjacent docs, not directly stated; `[VERIFIED]` = pulled from a primary source page checked in the research pass. When in doubt, assume `[UNVERIFIED]`.

---

## 1. Canonical CI/CD pipeline (hackathon-scale)

The de-facto stages, ordered:

```
PR opened/updated
  └─ ci.yml
        Lint  →  Type-check  →  Unit tests  →  Build (smoke)  →  (Integration tests, gated)

Merge to main
  └─ deploy-cloud-run.yml
        Auth (WIF)  →  Build & push images  →  Deploy to STAGING Cloud Run
        →  Smoke test staging  →  Load/integration tests
        →  (Optional manual approval gate)
        →  Deploy to PROD Cloud Run  →  Smoke test prod

Tag pushed (vX.Y.Z)
  └─ release.yml
        Generate release notes  →  Optional rollback pointer
```

The agent-starter-pack reference implements this exact two-stage split: `staging.yaml` runs on push-to-main, then `call_production_workflow` invokes `deploy-to-prod.yaml` via `workflow_call`, with production gated by a GitHub Environment that has `Required reviewers` protection rules. ([agent-starter-pack staging.yaml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/staging.yaml), [deploy-to-prod.yaml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/deploy-to-prod.yaml))

### What runs on which event

| Event | Workflows | Cost concern |
| --- | --- | --- |
| `pull_request` (opened/sync to `main`) | `ci.yml` (lint, type, unit, fast integration) | Free on public repos, otherwise 2k min/mo cap |
| `push` to `main` | `deploy-cloud-run.yml` (build + deploy staging + smoke + prod gate) | Each push = real GCP $ via image build, Cloud Run revision, optional load test |
| `push` of tag `v*.*.*` | `release.yml` (release notes, registry retag latest→version) | Trivial |
| `workflow_dispatch` | Manual prod deploy, manual rollback | Manual gate; useful for hackathon emergency |
| `schedule` (cron) | Nightly E2E vs staging, dependency audit | Optional |

### Branch protection rules (the must-haves)

[VERIFIED via GitHub docs] Configure under `Settings → Branches → Branch protection rules → main`:

1. `Require a pull request before merging`
2. `Require status checks to pass before merging`
   - Required checks: `ci / lint`, `ci / type-check`, `ci / test`, `ci / build`
3. `Require branches to be up to date before merging` (recommended only if you have <5 merges/day; otherwise it forces serial merges)
4. `Require linear history` if you use squash-merge
5. `Do not allow bypassing` for repo admins (unless you need emergency hotfix override during hackathon)

For a solo / 2-person hackathon team, the realistic policy is: required CI checks but no required reviewer (or self-review allowed). ([GitHub branch protection docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches))

---

## 2. Workflow files — paste-ready templates

The four templates below are generic and reusable. Replace placeholder values: `PROJECT_ID`, `PROJECT_NUMBER`, region (`us-central1`), service names, repo name.

### a) `.github/workflows/ci.yml` — runs on PR, fails fast

```yaml
# Runs on every PR. Lint + type + unit tests + build smoke + file-size guard.
# No GCP credentials needed → no WIF roundtrip → faster.
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]   # also run on main to catch direct pushes / fast-forwards

# Limit concurrency so superseded PRs cancel old runs.
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ----------------------------------------------------------------------
  # Job 1 — change detection (controls which downstream jobs run)
  # ----------------------------------------------------------------------
  changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    outputs:
      agent: ${{ steps.filter.outputs.agent }}
      web:   ${{ steps.filter.outputs.web }}
      shared: ${{ steps.filter.outputs.shared }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            agent:
              - 'services/agent/**'
              - 'uv.lock'
              - 'pyproject.toml'
            web:
              - 'services/web/**'
              - 'pnpm-lock.yaml'
            shared:
              - '.github/workflows/**'
              - 'pyproject.toml'
              - 'package.json'

  # ----------------------------------------------------------------------
  # Job 2 — Python: lint + type + unit tests
  # ----------------------------------------------------------------------
  python-checks:
    needs: changes
    if: ${{ needs.changes.outputs.agent == 'true' || needs.changes.outputs.shared == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6     # canonical uv installer
        with:
          enable-cache: true            # built-in cache; keyed on uv.lock automatically
          cache-dependency-glob: '**/uv.lock'

      - name: Sync deps (locked, no install of project itself)
        run: uv sync --locked --all-extras

      - name: Ruff lint
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy strict
        run: uv run mypy --strict services/agent

      - name: Pytest (unit only — fast)
        run: uv run pytest tests/unit -q --maxfail=1

  # ----------------------------------------------------------------------
  # Job 3 — Next.js: lint + type + unit tests
  # ----------------------------------------------------------------------
  web-checks:
    needs: changes
    if: ${{ needs.changes.outputs.web == 'true' || needs.changes.outputs.shared == 'true' }}
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: services/web
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'                  # built-in pnpm cache via setup-node
          cache-dependency-path: services/web/pnpm-lock.yaml

      - run: pnpm install --frozen-lockfile

      - run: pnpm lint
      - run: pnpm typecheck
      - run: pnpm test --run             # vitest non-watch
      - run: pnpm build                  # build smoke — catches type+lint regressions

  # ----------------------------------------------------------------------
  # Job 4 — Repo hygiene: 400-line guard, conventional commits, markdownlint
  # ----------------------------------------------------------------------
  repo-hygiene:
    needs: changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 400-line file size guard
        run: |
          # Fails the build if any tracked source file exceeds 400 lines.
          # Excludes lockfiles, generated files, and docs.
          BAD=$(git ls-files \
            | grep -Ev '\.(lock|sum|svg|png|jpg|md|json)$|/(node_modules|dist|\.next|generated)/' \
            | xargs -I{} sh -c 'lines=$(wc -l <"{}"); [ "$lines" -gt 400 ] && echo "{}:$lines"' \
            || true)
          if [ -n "$BAD" ]; then
            echo "::error::Files exceed 400 lines (sahil rule):"; echo "$BAD"; exit 1
          fi

      - name: Conventional commits lint (PR title)
        if: github.event_name == 'pull_request'
        uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: markdownlint
        uses: DavidAnson/markdownlint-cli2-action@v16
        with:
          globs: '**/*.md'
```

Notes:

- `concurrency.cancel-in-progress` is the single biggest CI cost saver during a hackathon: every force-push cancels the prior run.
- The `changes` job is what makes a monorepo cheap. Without it every PR runs every job.
- `python-checks` and `web-checks` run in parallel.
- No GCP auth in `ci.yml` → no Workload Identity Federation latency / failure mode in the hot path.

### b) `.github/workflows/deploy-cloud-run.yml` — on merge to main

Multi-service version. Builds and deploys whichever services changed.

```yaml
name: Deploy (Cloud Run)

on:
  push:
    branches: [main]
    paths:
      - 'services/**'
      - 'uv.lock'
      - 'pnpm-lock.yaml'
      - '.github/workflows/deploy-cloud-run.yml'

concurrency:
  group: deploy-main      # serialise: never run two prod deploys in parallel
  cancel-in-progress: false

env:
  GCP_REGION: us-central1
  ARTIFACT_REPO: chaoslab-images          # Artifact Registry repo name
  STAGING_PROJECT_ID: ${{ vars.STAGING_PROJECT_ID }}
  PROD_PROJECT_ID:    ${{ vars.PROD_PROJECT_ID }}
  CICD_PROJECT_ID:    ${{ vars.CICD_PROJECT_ID }}   # holds Artifact Registry + WIF

jobs:
  # ---------------------------------------------------------------------
  # Detect which services changed
  # ---------------------------------------------------------------------
  changes:
    runs-on: ubuntu-latest
    outputs:
      agent:        ${{ steps.f.outputs.agent }}
      web:          ${{ steps.f.outputs.web }}
      target_agent: ${{ steps.f.outputs.target_agent }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - uses: dorny/paths-filter@v3
        id: f
        with:
          filters: |
            agent:
              - 'services/agent/**'
              - 'uv.lock'
            target_agent:
              - 'services/target-agent/**'
              - 'uv.lock'
            web:
              - 'services/web/**'
              - 'pnpm-lock.yaml'

  # ---------------------------------------------------------------------
  # Build + push + deploy to STAGING (parallel across services)
  # ---------------------------------------------------------------------
  deploy-staging:
    needs: changes
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write           # required for WIF OIDC token
    strategy:
      fail-fast: false
      matrix:
        include:
          - { service: agent,        path: services/agent,        changed: 'agent' }
          - { service: target-agent, path: services/target-agent, changed: 'target_agent' }
          - { service: web,          path: services/web,          changed: 'web' }
    steps:
      - name: Skip if unchanged
        if: ${{ needs.changes.outputs[matrix.changed] != 'true' }}
        run: |
          echo "Service ${{ matrix.service }} unchanged — skipping."
          echo "SKIP=true" >> $GITHUB_ENV

      - if: env.SKIP != 'true'
        uses: actions/checkout@v4

      # ---- Auth via Workload Identity Federation (no JSON key) ----
      - if: env.SKIP != 'true'
        id: auth
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/${{ vars.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/${{ vars.WIF_POOL_ID }}/providers/${{ vars.WIF_PROVIDER_ID }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}
          project_id: ${{ env.CICD_PROJECT_ID }}

      - if: env.SKIP != 'true'
        uses: google-github-actions/setup-gcloud@v3

      - if: env.SKIP != 'true'
        name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ env.GCP_REGION }}-docker.pkg.dev --quiet

      - if: env.SKIP != 'true'
        uses: docker/setup-buildx-action@v3

      # ---- Build & push with layer cache ----
      - if: env.SKIP != 'true'
        name: Build & push image
        uses: docker/build-push-action@v6
        with:
          context: ${{ matrix.path }}
          push: true
          tags: |
            ${{ env.GCP_REGION }}-docker.pkg.dev/${{ env.CICD_PROJECT_ID }}/${{ env.ARTIFACT_REPO }}/${{ matrix.service }}:${{ github.sha }}
            ${{ env.GCP_REGION }}-docker.pkg.dev/${{ env.CICD_PROJECT_ID }}/${{ env.ARTIFACT_REPO }}/${{ matrix.service }}:latest
          cache-from: type=gha,scope=${{ matrix.service }}
          cache-to: type=gha,mode=max,scope=${{ matrix.service }}
          build-args: |
            COMMIT_SHA=${{ github.sha }}

      # ---- Deploy to staging Cloud Run ----
      - if: env.SKIP != 'true'
        id: deploy
        uses: google-github-actions/deploy-cloudrun@v3
        with:
          service: ${{ matrix.service }}-staging
          image: ${{ env.GCP_REGION }}-docker.pkg.dev/${{ env.CICD_PROJECT_ID }}/${{ env.ARTIFACT_REPO }}/${{ matrix.service }}:${{ github.sha }}
          region: ${{ env.GCP_REGION }}
          project_id: ${{ env.STAGING_PROJECT_ID }}
          flags: >-
            --service-account=${{ vars.RUNTIME_SA_STAGING }}
            --min-instances=0
            --max-instances=10
            --memory=1Gi
            --cpu=1
            --concurrency=80
            --timeout=300
            --allow-unauthenticated
          env_vars: |-
            GOOGLE_CLOUD_PROJECT=${{ env.STAGING_PROJECT_ID }}
            GOOGLE_CLOUD_LOCATION=${{ env.GCP_REGION }}
            GOOGLE_GENAI_USE_VERTEXAI=True
            COMMIT_SHA=${{ github.sha }}
          secrets: |-
            PHOENIX_API_KEY=phoenix-api-key:latest

      # ---- Smoke test ----
      - if: env.SKIP != 'true'
        name: Smoke test staging
        run: |
          URL="${{ steps.deploy.outputs.url }}"
          for i in 1 2 3 4 5; do
            if curl -fsS "$URL/healthz"; then exit 0; fi
            sleep 5
          done
          echo "::error::Smoke test failed for ${{ matrix.service }}"
          exit 1

  # ---------------------------------------------------------------------
  # Promote staging → prod (manual approval gate via Environment).
  # Same structure as deploy-staging but: environment: production gates on
  # human approval; uses RUNTIME_SA_PROD + PROD_PROJECT_ID; --min-instances=1;
  # never rebuilds — promotes the same :${{ github.sha }} image.
  # ---------------------------------------------------------------------
  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production       # requires reviewer approval, configured in repo settings
    concurrency: deploy-prod
    permissions: { contents: read, id-token: write }
    strategy:
      fail-fast: false
      matrix:
        service: [agent, target-agent, web]
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/${{ vars.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/${{ vars.WIF_POOL_ID }}/providers/${{ vars.WIF_PROVIDER_ID }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v3
      - uses: google-github-actions/deploy-cloudrun@v3
        with:
          service: ${{ matrix.service }}-prod
          image: ${{ env.GCP_REGION }}-docker.pkg.dev/${{ env.CICD_PROJECT_ID }}/${{ env.ARTIFACT_REPO }}/${{ matrix.service }}:${{ github.sha }}
          region: ${{ env.GCP_REGION }}
          project_id: ${{ env.PROD_PROJECT_ID }}
          flags: >-
            --service-account=${{ vars.RUNTIME_SA_PROD }}
            --min-instances=1 --max-instances=20 --memory=2Gi --cpu=2 --concurrency=80 --timeout=300
          env_vars: |-
            GOOGLE_CLOUD_PROJECT=${{ env.PROD_PROJECT_ID }}
            GOOGLE_CLOUD_LOCATION=${{ env.GCP_REGION }}
            GOOGLE_GENAI_USE_VERTEXAI=True
            COMMIT_SHA=${{ github.sha }}
          secrets: PHOENIX_API_KEY=phoenix-api-key:latest
```

Key patterns:

- **Same image promoted, never rebuilt.** Staging and prod consume the same `:${{ github.sha }}` tag. Rebuilding for prod is the most common foot-gun that introduces "works in staging, breaks in prod."
- **Matrix with per-service skip.** All three services are in one matrix; the `if: env.SKIP != 'true'` gate inside each step means unchanged services exit cheaply rather than skipping the whole job (which would otherwise hide the matrix leg).
- **`min-instances=1` on prod only.** Staging stays at 0 to save cost; prod keeps a warm instance so demo-day cold-starts are not 8 seconds. (Cloud Run cold-start mitigation; see Section 13.)
- **Secrets injected by reference**, not value: `secrets: PHOENIX_API_KEY=phoenix-api-key:latest` reads from Secret Manager at deploy time. See [google-github-actions/deploy-cloudrun docs](https://github.com/google-github-actions/deploy-cloudrun).

### c) `.github/workflows/visual-test.yml` — Playwright vs deployed staging

```yaml
# Visual regression + smoke E2E against the live staging Cloud Run URL.
# Integrates with the sahil-visual-loop skill: anchor screenshots live in
# tests/visual/anchors/, the Playwright spec compares against them.
name: Visual Tests

on:
  workflow_run:
    workflows: ["Deploy (Cloud Run)"]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      staging_url:
        description: 'Override staging URL (otherwise discovered via gcloud)'
        required: false

jobs:
  visual:
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with: { version: 9 }

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          cache-dependency-path: tests/visual/pnpm-lock.yaml

      - name: Install Playwright + deps
        working-directory: tests/visual
        run: |
          pnpm install --frozen-lockfile
          pnpm exec playwright install --with-deps chromium

      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/${{ vars.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/${{ vars.WIF_POOL_ID }}/providers/${{ vars.WIF_PROVIDER_ID }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v3

      - name: Discover staging URL
        id: url
        run: |
          if [ -n "${{ inputs.staging_url }}" ]; then
            echo "url=${{ inputs.staging_url }}" >> $GITHUB_OUTPUT
          else
            URL=$(gcloud run services describe web-staging \
              --region=us-central1 \
              --project=${{ vars.STAGING_PROJECT_ID }} \
              --format='value(status.url)')
            echo "url=$URL" >> $GITHUB_OUTPUT
          fi

      - name: Run Playwright
        working-directory: tests/visual
        env:
          BASE_URL: ${{ steps.url.outputs.url }}
        run: pnpm exec playwright test --reporter=line,html

      - name: Upload diff report
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: tests/visual/playwright-report/
          retention-days: 7

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: visual-diffs
          path: tests/visual/test-results/
          retention-days: 7
```

Notes:

- Triggered by `workflow_run` so it only runs after a successful deploy. This avoids the antipattern of running Playwright on every PR against ephemeral URLs.
- `workflow_dispatch` allows the human (or `sahil-visual-loop` skill) to re-run against an arbitrary URL.
- Anchor screenshots live in `tests/visual/anchors/` per the `sahil-visual-loop` skill convention — Playwright's `toHaveScreenshot()` does the pixel diff. On failure, the `playwright-report/` artifact contains the diff that the fresh-context Opus reviewer reads.

### d) `.github/workflows/preview-deploy.yml` — ephemeral PR preview

```yaml
# Per-PR ephemeral Cloud Run preview. One revision per PR, tagged pr-NNN.
# Cleaned up by close-preview job when PR is closed.
name: Preview Deploy

on:
  pull_request:
    types: [opened, synchronize, reopened, closed]
    paths:
      - 'services/web/**'        # only spin previews for web changes (cost)
      - 'pnpm-lock.yaml'

concurrency:
  group: preview-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  preview:
    if: ${{ github.event.action != 'closed' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      pull-requests: write       # to comment with preview URL
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/${{ vars.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/${{ vars.WIF_POOL_ID }}/providers/${{ vars.WIF_PROVIDER_ID }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v3

      - name: Build & push preview image
        run: |
          gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
          IMAGE="us-central1-docker.pkg.dev/${{ vars.CICD_PROJECT_ID }}/chaoslab-images/web:pr-${{ github.event.pull_request.number }}-${{ github.sha }}"
          docker build -t "$IMAGE" services/web
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> $GITHUB_ENV

      - id: deploy
        uses: google-github-actions/deploy-cloudrun@v3
        with:
          service: web-preview-pr${{ github.event.pull_request.number }}
          image: ${{ env.IMAGE }}
          region: us-central1
          project_id: ${{ vars.STAGING_PROJECT_ID }}
          flags: >-
            --min-instances=0
            --max-instances=2
            --memory=1Gi
            --cpu=1
            --allow-unauthenticated

      - name: Comment preview URL on PR
        uses: actions/github-script@v7
        with:
          script: |
            const url = '${{ steps.deploy.outputs.url }}';
            const body = `Preview: ${url}\n(Updated on every push to this PR.)`;
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner, repo: context.repo.repo,
              issue_number: context.issue.number,
            });
            const existing = comments.find(c => c.user.type === 'Bot' && c.body.startsWith('Preview:'));
            if (existing) {
              await github.rest.issues.updateComment({ ...context.repo, comment_id: existing.id, body });
            } else {
              await github.rest.issues.createComment({ ...context.repo, issue_number: context.issue.number, body });
            }

  close-preview:
    if: ${{ github.event.action == 'closed' }}
    runs-on: ubuntu-latest
    permissions: { contents: read, id-token: write }
    steps:
      - uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/${{ vars.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/${{ vars.WIF_POOL_ID }}/providers/${{ vars.WIF_PROVIDER_ID }}
          service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v3
      - run: |
          gcloud run services delete web-preview-pr${{ github.event.pull_request.number }} \
            --region=us-central1 --project=${{ vars.STAGING_PROJECT_ID }} --quiet || true
```

[UNVERIFIED] Preview deploys to Cloud Run cost roughly the same as an unused staging revision: ~$0 when idle (min-instances=0), but image storage and deploy time accrue. For a 9-day hackathon with 5-10 active PRs this is acceptable.

---

## 3. Workload Identity Federation (OIDC) for GCP auth

The modern non-secret way to authenticate GitHub Actions to Google Cloud. No JSON keys, ever. ([VERIFIED — Google Cloud Blog](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions))

### Why WIF, not JSON keys

- JSON service-account keys are long-lived, leak via logs/secrets/forks, and require rotation.
- WIF issues short-lived (~1 hour) OAuth tokens from a federated identity. ([VERIFIED](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions))
- WIF attribute conditions can restrict auth to a single repo, branch, or commit SHA pattern. ([VERIFIED — Google IAM best practices](https://docs.cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation))

### Setup (gcloud, one-time)

```bash
export PROJECT_ID="chaoslab-cicd"        # dedicated CI/CD project (best practice)
export PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
export POOL_ID="github"
export PROVIDER_ID="github-provider"
export REPO="myorg/chaoslab"             # GitHub org/repo
export SA_NAME="github-actions-deployer"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 1. Create the workload identity pool
gcloud iam workload-identity-pools create "$POOL_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Create the OIDC provider with REPO restriction in the attribute condition
#    The attribute-condition is the critical security boundary — without it,
#    ANY GitHub repo in the world can impersonate this provider.
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="$POOL_ID" \
  --display-name="GitHub Actions Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_owner == 'myorg' && assertion.repository == '${REPO}'"

# 3. Create the service account that will be impersonated
gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT_ID" \
  --display-name="GitHub Actions Deployer"

# 4. Bind the WIF principal to the service account.
#    The principalSet path restricts WHICH workflow runs can impersonate.
#    Below: only workflows in the specified repo.
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

# 5. Print the provider resource name — paste this into GitHub secrets/vars
echo "workload_identity_provider:"
echo "  projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
echo "service_account: ${SA_EMAIL}"
```

### Locking down further: branch-scoped binding

[VERIFIED via Google IAM best practices] For prod, scope the principalSet to a specific ref:

```bash
gcloud iam service-accounts add-iam-policy-binding "$PROD_SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.ref/refs/heads/main"
```

Now only workflow runs from `main` can impersonate the prod deploy SA. PRs from forks cannot.

### The `auth@v2` step

```yaml
- id: auth
  uses: google-github-actions/auth@v3
  with:
    workload_identity_provider: projects/123456789/locations/global/workloadIdentityPools/github/providers/github-provider
    service_account: github-actions-deployer@chaoslab-cicd.iam.gserviceaccount.com
    project_id: chaoslab-cicd              # optional but recommended
    create_credentials_file: true          # required if downstream tools read GOOGLE_APPLICATION_CREDENTIALS
    token_format: access_token             # default — use 'id_token' only for Cloud Run-to-Cloud Run calls
```

Critical: the calling job MUST declare `permissions: id-token: write` at the job or workflow level. Without it, the OIDC token request fails with a misleading "permission denied" error. ([VERIFIED — google-github-actions/auth README](https://github.com/google-github-actions/auth))

### Least-privilege service account roles

For a deploy SA that needs to push images, deploy Cloud Run, and read secrets:

```bash
# Image push to Artifact Registry
gcloud projects add-iam-policy-binding "$CICD_PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Deploy Cloud Run revisions in staging + prod projects
for ENV_PROJECT in "$STAGING_PROJECT" "$PROD_PROJECT"; do
  gcloud projects add-iam-policy-binding "$ENV_PROJECT" \
    --member="serviceAccount:${SA_EMAIL}" --role="roles/run.developer"
  gcloud projects add-iam-policy-binding "$ENV_PROJECT" \
    --member="serviceAccount:${SA_EMAIL}" --role="roles/iam.serviceAccountUser"
  gcloud projects add-iam-policy-binding "$ENV_PROJECT" \
    --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor"
done
```

Roles, mapped to capability:

| Role | What it lets the SA do |
| --- | --- |
| `roles/artifactregistry.writer` | Push images to AR |
| `roles/run.developer` | Create/update Cloud Run services and revisions |
| `roles/iam.serviceAccountUser` | Set the runtime SA on the deployed service (REQUIRED — most forgotten role) |
| `roles/secretmanager.secretAccessor` | Read secrets the service uses at runtime |
| `roles/logging.logWriter` | (Only needed for runtime SA, not deploy SA) |

The `iam.serviceAccountUser` role on the **runtime** SA is the most-missed piece. Without it, `gcloud run deploy --service-account=runtime-sa@...` fails with `Permission denied on service account`.

---

## 4. Multi-service repo deploy strategy

### Path-based filters

Already shown in section 2b. The `dorny/paths-filter@v3` action returns boolean outputs per filter, used via `if: needs.changes.outputs.X == 'true'`. ([dorny/paths-filter README](https://github.com/dorny/paths-filter))

### Tag conventions

| Image tag | Lifetime | When pushed |
| --- | --- | --- |
| `:${{ github.sha }}` | Immutable, kept ~30 days | Every successful main build |
| `:latest` | Mutable, points to latest main | Every successful main build |
| `:pr-NNN-{sha}` | Cleaned on PR close | Preview deploys |
| `:v1.2.3` | Permanent | Manual release tag |

Rule: deploys (staging and prod) reference `:${sha}`, never `:latest`. `:latest` is for human convenience only.

### Image registry layout

```
us-central1-docker.pkg.dev/
  chaoslab-cicd/                              # CI/CD project — shared registry
    chaoslab-images/                          # Artifact Registry repo
      agent:abc1234                           # ADK agent service
      target-agent:abc1234                    # the agent being tested
      web:abc1234                             # Next.js frontend
```

One Artifact Registry repo, one image per service, tag = commit SHA. The CICD project (separate from STAGING/PROD app projects) hosts the registry — this is what the agent-starter-pack template does. ([VERIFIED](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/staging.yaml))

### Per-service Cloud Run config defaults

These are reasonable starting points; profile and adjust.

| Service | Memory | CPU | min-inst | max-inst | Concurrency | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agent` (ADK) | 2Gi | 2 | prod: 1 / staging: 0 | 10 | 80 | Loads Vertex client + Phoenix exporter; min-instances=1 in prod to avoid 5-10s cold start |
| `target-agent` | 1Gi | 1 | 0 | 10 | 80 | Throwaway target; cold-start tolerable |
| `web` (Next.js) | 1Gi | 1 | prod: 1 / staging: 0 | 20 | 80 | SSR; min-instances=1 in prod for demo |

[UNVERIFIED] These are starting points based on typical ADK + Vertex agent footprints. Profile under realistic load before final demo.

CPU-always-allocated (`--cpu-always-allocated`) is worth setting for the agent service if it does background work, but it doubles cost.

---

## 5. Secret management in CI

### Where secrets live, and why

| Type | Lives in | Used by |
| --- | --- | --- |
| GCP auth (WIF provider, SA email) | GitHub repository **variables** (NOT secrets — they're not sensitive) | Every workflow's auth step |
| `GITHUB_TOKEN` | Auto-injected | PR comments, gh CLI |
| `PHOENIX_API_KEY` (runtime) | Google Secret Manager → mounted by Cloud Run | The deployed service at runtime |
| `PHOENIX_API_KEY` (CI integration tests) | GitHub repository **secret** | Integration test job, narrow scope |
| `VERTEX_AI_LOCATION` etc. | GitHub variables | Workflows |
| Per-environment overrides | GitHub Environments (staging, production) | Their respective deploy jobs |

The split: **runtime secrets in Secret Manager** (so they're rotatable without redeploying CI); **CI-time secrets in GitHub** (so they're tied to the workflow, not the service).

### Fetching from Secret Manager during deploy

The `deploy-cloudrun@v2` action does this declaratively — no fetch step needed. The `secrets:` input is a list of `ENV_NAME=secret-name:version`:

```yaml
- uses: google-github-actions/deploy-cloudrun@v3
  with:
    service: chaoslab-agent
    image: ...
    secrets: |-
      PHOENIX_API_KEY=phoenix-api-key:latest
      OPENAI_API_KEY=openai-key:2
```

Cloud Run injects these as env vars at container startup. The deploy SA needs `roles/secretmanager.secretAccessor` on each secret. ([VERIFIED — deploy-cloudrun README](https://github.com/google-github-actions/deploy-cloudrun))

For volume-mounted secrets (e.g., a JSON config), prefix the key with a path:

```yaml
secrets: |-
  /etc/config/openai.json=openai-config:latest
```

### Per-environment secret separation

Use GitHub Environments (`staging`, `production`) — they store secrets/variables that only the matching job can read:

```yaml
jobs:
  deploy-prod:
    environment: production    # accesses production env's secrets only
    ...
```

In Secret Manager, name secrets with environment suffix: `phoenix-api-key-staging`, `phoenix-api-key-prod`. The deploy step references the right one based on `${{ env.STAGING_PROJECT_ID }}` vs `${{ env.PROD_PROJECT_ID }}`.

### CI-time secrets (integration tests)

Phoenix Cloud integration tests need a real API key. Create a **separate, low-quota** Phoenix project for CI:

```yaml
- name: Integration tests against Phoenix Cloud (CI account)
  env:
    PHOENIX_API_KEY: ${{ secrets.PHOENIX_CI_API_KEY }}
    PHOENIX_PROJECT_NAME: chaoslab-ci    # isolated project
  run: uv run pytest tests/integration -m phoenix
```

Rotate this key independently of the runtime key. If a fork PR leaks it, the blast radius is the CI Phoenix project.

---

## 6. Speed optimizations

### uv caching

`astral-sh/setup-uv@v6` ships with built-in caching keyed on `uv.lock`. ([VERIFIED — astral-sh docs](https://docs.astral.sh/uv/guides/integration/github/))

```yaml
- uses: astral-sh/setup-uv@v6
  with:
    enable-cache: true
    cache-dependency-glob: '**/uv.lock'   # explicit; default is uv.lock at root
- run: uv sync --locked
```

Manual variant if you need fine control:

```yaml
- uses: actions/cache@v4
  with:
    path: /tmp/.uv-cache
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: |
      uv-${{ runner.os }}-
- run: uv sync --locked
- run: uv cache prune --ci    # before exiting, to keep cache slim
```

The `uv cache prune --ci` step strips wheel artifacts that don't need to be re-cached. ([VERIFIED — astral-sh docs](https://docs.astral.sh/uv/guides/integration/github/))

### Docker layer caching

Two viable backends:

| Backend | `cache-from` / `cache-to` | Speed | Storage |
| --- | --- | --- | --- |
| GitHub Actions cache (`type=gha`) | `type=gha` + `type=gha,mode=max` | Fast (same DC as runner) | Counts toward GitHub cache quota (~10GB per repo, evicted LRU) |
| Registry cache (Artifact Registry) | `type=registry,ref=...:cache` | Slower (network roundtrip) | Counts toward AR storage $ |
| Inline (in published image) | `type=inline` | Free | Larger published images |

For hackathon scale, `type=gha,mode=max` is the right default. Use distinct `scope=` values when building multiple images in one workflow — otherwise they clobber each other. ([VERIFIED — Docker GHA cache docs](https://docs.docker.com/build/cache/backends/gha/))

```yaml
- uses: docker/build-push-action@v6
  with:
    context: services/agent
    push: true
    tags: ...
    cache-from: type=gha,scope=agent
    cache-to: type=gha,mode=max,scope=agent
```

`mode=max` exports ALL layers (including intermediate build stages) — strongly recommended for multi-stage Dockerfiles.

### pnpm / npm caching for Next.js

`actions/setup-node@v4` has native pnpm cache support:

```yaml
- uses: pnpm/action-setup@v4
  with: { version: 9 }
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'pnpm'
    cache-dependency-path: services/web/pnpm-lock.yaml
- run: pnpm install --frozen-lockfile
```

For Next.js build artifacts (`.next/cache`):

```yaml
- uses: actions/cache@v4
  with:
    path: services/web/.next/cache
    key: nextjs-${{ runner.os }}-${{ hashFiles('services/web/pnpm-lock.yaml') }}-${{ hashFiles('services/web/**/*.ts', 'services/web/**/*.tsx') }}
    restore-keys: |
      nextjs-${{ runner.os }}-${{ hashFiles('services/web/pnpm-lock.yaml') }}-
```

### Parallel jobs

`ci.yml` already splits Python, web, and hygiene into three parallel jobs. The matrix in `deploy-cloud-run.yml` parallelizes three service builds.

The constraint: `ubuntu-latest` runners are dual-core, so parallelism only helps when the bottleneck is I/O (download deps, push image), not CPU.

### Matrix builds where useful

- **Python version matrix:** Only if you publish a library. For a service deploying to Cloud Run, pin one Python version and skip the matrix.
- **Node version matrix:** Same — pick one.
- **Service matrix:** Yes (as shown), parallelizes per-service Docker builds.

---

## 7. Test pipeline composition

| Layer | When | Cost | Where |
| --- | --- | --- | --- |
| Unit (pytest, vitest) | Every PR | Free (CPU only) | `ci.yml` |
| Type check (mypy, tsc) | Every PR | Free | `ci.yml` |
| Lint (ruff, eslint) | Every PR | Free | `ci.yml` |
| Build smoke (`pnpm build`, `docker build`) | Every PR | Free (uses cache) | `ci.yml` |
| Integration (Phoenix, Vertex AI mock) | Every PR, marked `@pytest.mark.integration` | Small Vertex API $ | `ci.yml` job, gated on label or always |
| E2E (Playwright vs deployed staging) | After deploy succeeds on main | Cloud Run invocations | `visual-test.yml` |
| Load test (locust) | After deploy to staging | Cloud Run invocations | `deploy-cloud-run.yml` post-deploy step |

### Real Phoenix + real Vertex AI in CI

Two valid postures:

**Posture A: full integration on every PR.** Cheap for a hackathon — Vertex AI calls are usually fractions of a cent. Use a low-quota CI project to cap blast radius if a test loops.

**Posture B: integration only on main.** Saves cost but lets bugs slip to staging. Acceptable if your unit tests are good and your demo deadline is far.

For ChaosLab-scale (9-day cadence, 4-week judging), Posture A on every PR but with strict pytest markers and timeouts:

```python
# tests/conftest.py
@pytest.fixture(scope='session')
def phoenix_client():
    if not os.environ.get('PHOENIX_API_KEY'):
        pytest.skip('PHOENIX_API_KEY not set')
    return phoenix.Client()

# tests/integration/test_agent.py
@pytest.mark.integration
@pytest.mark.timeout(60)
def test_agent_returns_response(phoenix_client):
    ...
```

```yaml
- name: Integration tests
  env:
    PHOENIX_API_KEY: ${{ secrets.PHOENIX_CI_API_KEY }}
    GOOGLE_CLOUD_PROJECT: ${{ vars.CICD_PROJECT_ID }}
  run: uv run pytest tests/integration -m integration --timeout=60
```

### Cost-aware gating

Use labels to opt-in expensive checks:

```yaml
- name: Heavy integration suite
  if: contains(github.event.pull_request.labels.*.name, 'run-full-tests')
  run: uv run pytest tests/integration/full
```

---

## 8. Deploy-on-merge-to-main pattern

### Conventional commits → semver

Use `release-please` to auto-bump version, generate CHANGELOG, and create a release PR:

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    branches: [main]
jobs:
  release-please:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: python    # or: node, simple
```

Commit messages follow conventional-commits: `feat:`, `fix:`, `chore:`, `docs:`. Each `feat:` bumps minor; each `fix:` bumps patch; `BREAKING CHANGE:` in the body bumps major.

### Skip deploy when only docs change

Already handled by the `paths:` filter on `deploy-cloud-run.yml` (it doesn't include `docs/**` or `*.md`). Also add at the job level:

```yaml
jobs:
  deploy:
    if: ${{ !contains(github.event.head_commit.message, '[skip ci]') }}
```

### Rollback strategy

Cloud Run's revision model makes rollback one command:

```bash
# Find previous good revision
gcloud run revisions list --service=chaoslab-agent --region=us-central1 \
  --project=chaoslab-prod --limit=5

# Route 100% traffic back to previous revision
gcloud run services update-traffic chaoslab-agent \
  --region=us-central1 --project=chaoslab-prod \
  --to-revisions=chaoslab-agent-00041-xyz=100
```

Wrap this in a `workflow_dispatch` workflow `.github/workflows/rollback.yml` taking `service` and `revision` as inputs. If smoke test fails post-deploy, the deploy job exits non-zero and Cloud Run keeps serving the previous revision (since the new revision didn't get 100% traffic) — unless you used `--no-traffic` + manual promotion, the new revision IS already serving and you need explicit rollback.

The safer pattern: deploy with `--no-traffic`, then `update-traffic --to-latest=100` only after smoke test passes:

```yaml
- name: Deploy with no traffic
  run: |
    gcloud run deploy chaoslab-agent \
      --image=... \
      --no-traffic --tag=candidate \
      --region=us-central1
- name: Smoke test against tagged revision
  run: |
    URL=$(gcloud run services describe chaoslab-agent --format='value(status.traffic.url)' --filter='tag=candidate')
    curl -fsS "$URL/healthz"
- name: Shift traffic
  run: |
    gcloud run services update-traffic chaoslab-agent --to-latest=100
```

This gives you blue/green semantics without ever serving a broken revision.

---

## 9. Branch protection + PR rules

### Required checks

In `Settings → Branches → Branch protection rules → main`:

- `Require status checks to pass before merging`
- Required checks (exact names from `ci.yml`):
  - `CI / python-checks`
  - `CI / web-checks`
  - `CI / repo-hygiene`
- Plus, if you use the visual test: `Visual Tests / visual` (only meaningful for post-merge though)

### Required reviewers

- Solo / 2-person team: not enforced, but enable "Require review from Code Owners" so the `CODEOWNERS` file forces reviewer assignment.
- Automated review via [@claude PR review or sahil-pr-audit]: post-merge or as a non-blocking comment-only check. Treat AI review as advisory, not a gate.

### CODEOWNERS

```
# .github/CODEOWNERS
* @abu
services/agent/    @abu
services/web/      @abu
.github/           @abu
```

Even with one owner, this triggers reviewer assignment automatically on every PR.

### Squash vs merge commit policy

For a hackathon: **squash-merge only**. One PR = one commit on main. Makes `git bisect` and rollback trivial. Configure in `Settings → General → Pull Requests`: enable "Allow squash merging", disable the others.

---

## 10. Pre-commit hook integration

### `pre-commit` framework

`.pre-commit-config.yaml`:

```yaml
repos:
  # Ruff: lint + format Python
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # Mypy strict on changed files
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]
        additional_dependencies: [types-requests, pydantic]

  # markdownlint
  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.41.0
    hooks:
      - id: markdownlint
        args: [--fix]

  # Conventional commits
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.4.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]

  # Local hook: 400-line file size guard
  - repo: local
    hooks:
      - id: file-size-400
        name: Block files > 400 lines (sahil rule)
        entry: bash -c 'for f in "$@"; do n=$(wc -l <"$f"); [ "$n" -gt 400 ] && { echo "$f: $n lines exceeds 400"; exit 1; }; done' --
        language: system
        types_or: [python, typescript, javascript, tsx]
        exclude: '^(.*\.lock|.*generated.*)$'

  # Optional: pytest --quick subset
  - repo: local
    hooks:
      - id: pytest-quick
        name: pytest fast unit tests
        entry: uv run pytest tests/unit -q -x --timeout=10
        language: system
        pass_filenames: false
        stages: [pre-push]    # only on push, not every commit
```

Install once: `pre-commit install --install-hooks --hook-type commit-msg --hook-type pre-push`.

CI runs the same hooks to catch anyone who skipped local install:

```yaml
- uses: pre-commit/action@v3.0.1
  with:
    extra_args: --all-files
```

---

## 11. Observability of CI/CD itself

### Run history & insights

- `Actions → All workflows` shows run history with duration trend.
- `Actions → Caches` shows cache hit/miss and storage usage. Evict by hand if a cache key goes stale.
- For organizations: `Insights → Actions` shows minutes consumed per workflow, useful for cost attribution.

### Notifications

On failure, ping Slack:

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1.27.0
  with:
    payload: |
      {
        "text": "Deploy failed: ${{ github.workflow }} on ${{ github.ref }} — ${{ github.event.head_commit.message }}",
        "blocks": [
          {"type": "section", "text": {"type": "mrkdwn",
            "text": "*Failure:* <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|view run>"}}
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

For a hackathon, a simpler route is `gh run watch` in your terminal while pushing, or `gh run list --limit 5` for spot-check.

### Run logs

GitHub retains workflow run logs for 90 days on free plans, 400 days on paid. For longer retention or audit, stream to Cloud Logging:

```yaml
- name: Stream logs to Cloud Logging
  if: always()
  run: |
    gcloud logging write github-actions-runs \
      "{\"workflow\":\"${{ github.workflow }}\",\"run_id\":\"${{ github.run_id }}\",\"conclusion\":\"${{ job.status }}\",\"sha\":\"${{ github.sha }}\"}" \
      --severity=INFO \
      --project=${{ vars.CICD_PROJECT_ID }}
```

---

## 12. Cost projection

### GitHub Actions free tier

[VERIFIED — GitHub Actions billing docs] As of mid-2026:

- **Public repos:** unlimited minutes, all OS.
- **Private repos (free plan):** 2,000 minutes/month of Linux runner time. macOS counts 10×, Windows 2×.

For ChaosLab over a 9-day build + 4-week judging window:

[UNVERIFIED] Rough back-of-envelope (assuming public repo, so it doesn't matter):

| Workflow | Avg run | Runs/day | Days | Total minutes |
| --- | --- | --- | --- | --- |
| `ci.yml` (PR + push) | 4 min | 8 | 35 | 1,120 |
| `deploy-cloud-run.yml` | 12 min | 2 | 35 | 840 |
| `visual-test.yml` | 5 min | 2 | 35 | 350 |
| `preview-deploy.yml` | 8 min | 5 | 21 (PR phase) | 840 |
| **Total** | | | | **~3,150 minutes** |

Public repo: free. Private repo: would exceed the 2k limit — at $0.008/min Linux that's ~$25 of overage. Below noise.

### Self-hosted runners

Not relevant for a hackathon. Self-hosted runners make sense when:

- You have >50k minutes/month sustained on private repos
- You need GPU
- You need to access on-prem networks

Skip.

### GCP-side cost

The bigger cost is Cloud Run + Artifact Registry + Vertex AI:

- Cloud Run staging (always idle): <$5/mo
- Cloud Run prod with min-instances=1: ~$30-50/mo (depends on CPU/memory; CPU-allocated-during-request is cheap)
- Artifact Registry storage: ~$0.10/GB/mo; with `:latest` + ~30 SHA tags retained, expect <$2/mo
- Vertex AI Gemini calls: dominant cost; budget separately
- Phoenix Cloud: per their tier; CI account should be free-tier

---

## 13. Common failure modes + mitigations

### WIF misconfiguration — the #1 deploy failure

Symptoms: workflow runs, `auth@v2` step fails with `Permission 'iam.serviceAccounts.getAccessToken' denied`.

Root causes, ranked by frequency:

1. **Missing `permissions: id-token: write`** in the job/workflow. Fix: add it.
2. **Attribute condition excludes your repo.** Verify with `gcloud iam workload-identity-pools providers describe ...` and check `attributeCondition` matches your `repository_owner`/`repository` literal values exactly (case-sensitive).
3. **Service-account binding uses wrong principalSet path.** The `attribute.repository/${REPO}` requires the literal `OWNER/REPO` form, not just `REPO`.
4. **Forgot to grant `roles/iam.serviceAccountUser`** on the runtime SA to the deploy SA → deploy fails after auth succeeds.
5. **Provider not enabled / OIDC issuer URI typo.** Compare to `https://token.actions.githubusercontent.com` exactly.

Debug step: in the workflow, add `gcloud auth list && gcloud config list` after `auth@v2`. Confirms the identity is what you think it is.

### Docker build cache miss → slow build

Symptoms: builds take 5+ minutes when they used to take 1.

Causes:

- Changing `apt-get install` order invalidates a layer. Pin the order or use `apt-get install -y --no-install-recommends`.
- Adding files via `COPY . .` before `COPY pyproject.toml` busts the dep-install layer. Order: `COPY pyproject.toml uv.lock . && uv sync` BEFORE `COPY . .`.
- GitHub Actions cache for `type=gha` is per-branch and evicts at 10GB. Use `scope=` to keep distinct images in distinct caches.
- For multi-stage builds, set `cache-to: type=gha,mode=max` (not the default `mode=min`) to retain intermediate-stage layers.

### Cloud Run cold start after deploy

Symptoms: first request after deploy takes 5-15 seconds; demo is awkward.

Mitigations:

- `--min-instances=1` on prod. This is the primary fix.
- For ADK agents: lazy-load Vertex client at first request (already default), but consider warming in a `startup_probe`.
- Use `--cpu-boost` (free) — gives extra CPU during cold start.

```yaml
flags: >-
  --min-instances=1
  --cpu-boost
  # (--startup-cpu-boost does NOT exist; verified 2026-06-03)
```

[UNVERIFIED] `--cpu-boost` flag name has changed across gcloud versions. Check `gcloud run deploy --help` on your runner image.

### Secret rotation breaking CI

Symptoms: PR fails with `Permission denied accessing secret`; rotated the WIF SA key by accident.

Causes:

- WIF doesn't use keys — but the GH variable `GCP_SERVICE_ACCOUNT` might still point to a deleted SA.
- Secret Manager: a deleted/disabled secret version breaks `secrets: KEY=name:latest`. Pin to a version (`:7`) for prod.
- Rotated Phoenix CI key but forgot to update GitHub repo secret. Fix: maintain a `secrets-runbook.md` listing every secret and its rotation cadence.

### Vertex AI quota errors in CI

Symptoms: integration test fails with `RESOURCE_EXHAUSTED` or `429`.

Causes:

- Free-tier quota on `gemini-2.5-flash` is per-project per-minute. Multiple CI runs in parallel hit it.
- Fix: route CI to a dedicated CI project with quota explicitly raised, or serialize integration tests with `concurrency: integration-tests`.
- For burst control: `pytest -n auto` parallelism multiplies quota burn — use `-n 2` and `pytest --tb=short -x` to fail fast.

---

## 14. Sources

Primary docs and references used for this file.

- **agent-starter-pack workflow templates (canonical example):**
  - [pr_checks.yaml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/pr_checks.yaml)
  - [staging.yaml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/staging.yaml)
  - [deploy-to-prod.yaml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/agent_starter_pack/base_templates/python/.github/workflows/deploy-to-prod.yaml)
  - [GitHub repo root](https://github.com/GoogleCloudPlatform/agent-starter-pack)
  - [Deployment guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment.html)

- **GitHub Actions: GCP auth (Workload Identity Federation):**
  - [google-github-actions/auth README](https://github.com/google-github-actions/auth)
  - [Google IAM best practices for WIF](https://docs.cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation)
  - [Google IAM: configure WIF with deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
  - [Google Cloud blog: enabling keyless auth from GitHub Actions](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)

- **GitHub Actions: Cloud Run deploy:**
  - [google-github-actions/deploy-cloudrun README](https://github.com/google-github-actions/deploy-cloudrun)
  - [google-github-actions/setup-gcloud README](https://github.com/google-github-actions/setup-gcloud)

- **ADK + Cloud Run:**
  - [ADK Cloud Run deployment docs](https://adk.dev/deploy/cloud-run/)

- **Path filtering / monorepo CI:**
  - [dorny/paths-filter README](https://github.com/dorny/paths-filter)

- **Docker build + caching:**
  - [Docker buildx GHA cache backend](https://docs.docker.com/build/cache/backends/gha/)
  - [docker/build-push-action GitHub Actions cache management](https://docs.docker.com/build/ci/github-actions/cache/)

- **uv + GitHub Actions:**
  - [Astral uv: GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/)
  - [astral-sh/setup-uv action](https://github.com/astral-sh/setup-uv)

- **Conventional commits + release:**
  - [release-please](https://github.com/googleapis/release-please-action)
  - [conventional-pre-commit](https://github.com/compilerla/conventional-pre-commit)

- **Branch protection:**
  - [GitHub: about protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

- **Pre-commit:**
  - [pre-commit framework](https://pre-commit.com/)
  - [Ruff pre-commit](https://github.com/astral-sh/ruff-pre-commit)
