# 06 — ChaosLab Deployment & Ops Architecture

> **Scope:** what gets deployed where, how it costs, what fails, what scales.
> **Project:** ChaosLab (Arize track, Google Cloud Rapid Agent Hackathon).
> **Builder:** Abu, solo, 9 days (today = 2026-06-02, submit by 2026-06-11 14:00 PT).
> **Budget:** $100 GCP promo credit + Phoenix Cloud free tier.
> **Survival window:** demo URL must stay clickable from submit → judging end (~2026-07-06) → winner announce (~2026-07-07). ~4 weeks live.
> **Scale target:** ONE judge running ONE demo at a time. Not production.

Companion files:
- `02a-google-cloud-stack.md` §5 (Agent Runtime vs Cloud Run), §10 (deployment paths)
- `02b-gemini-enterprise-agent-platform.md` (the 4-phase platform map + model pricing note)
- `brainstorm/05-ecosystem-refactor.md` §Appendix C (9-day cadence)
- `CONTEXT.md` §3 (verified facts incl. pricing rows)

---

## 1. The hosted Project URL — what does a judge see?

### What the judge clicks

Devpost submission form has one slot for **Project URL**. That's the URL judges visit during the 2026-06-22 → 2026-07-06 judging window. There is no login; the FAQ confirms judges expect a no-auth sandbox with pre-loaded sample data so they can hit Run and see the agent act.

### What the URL points at

Recommend: **Cloud Run service** serving a static-ish frontend (Next.js / Streamlit) that calls a same-process or sibling Cloud Run service hosting the ADK `api_server`, which in turn:
- calls Gemini 3.5 Flash via the Vertex AI SDK (token-cost line)
- calls Phoenix MCP (`@arizeai/phoenix-mcp` via `npx`) as an `MCPToolset` inside ADK
- emits traces to Phoenix Cloud (`app.phoenix.arize.com`) via OpenInference auto-instrumentation
- invokes the **target agent** (a separate Cloud Run service, the deliberately-naive support bot) via HTTP — this is the "victim" ChaosLab attacks

### Auth posture for the demo

Per `02a` §10 and `02a` §11: deploy with `--allow-unauthenticated` and set IAM binding `allUsers` → `roles/run.invoker`. Judges hit a public URL and run the demo. No login, no shared password, no token in the URL. The sandbox is read-only-from-judge's-perspective — every Run button click triggers a fresh attack sweep against the pre-loaded target agent and writes new spans to a judge-visible Phoenix project.

[UNVERIFIED] Devpost rules don't explicitly require unauthenticated access, but past Google AI hackathon winners (per `05-prior-winners.md`) universally shipped no-login demos. A login gate is the single best way to lose Tech Implementation points.

### Recommended deployment shape (ASCII)

```
                       ┌──────────────────────────────────────────────┐
                       │            Judge's browser                    │
                       │   https://chaoslab-xxxxx-uc.a.run.app         │
                       └────────────────────┬─────────────────────────┘
                                            │ HTTPS
                                            ▼
            ┌────────────────────────────────────────────────────────┐
            │  Cloud Run service: chaoslab-web                       │
            │  - Next.js OR Streamlit static + API routes            │
            │  - --allow-unauthenticated                             │
            │  - min-instances=1 during judging window (warm)        │
            └────────────────────┬───────────────────────────────────┘
                                 │ HTTP (internal, same project)
                                 ▼
            ┌────────────────────────────────────────────────────────┐
            │  Cloud Run service: chaoslab-agent                     │
            │  - ADK `api_server` (Python 3.11)                       │
            │  - root_agent = ChaosLab orchestrator                  │
            │  - MCPToolset(npx @arizeai/phoenix-mcp)                │
            │  - OpenInference auto-instrumentation                  │
            │  - Secrets injected via Secret Manager IAM             │
            └─────┬──────────────────┬───────────────────────────┬───┘
                  │ Vertex AI SDK    │ HTTP                      │ OTLP
                  ▼                  ▼                           ▼
        ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────┐
        │ Gemini 3.5 Flash │  │ Cloud Run service:│  │ Phoenix Cloud      │
        │ (Vertex AI)      │  │ target-agent      │  │ app.phoenix.arize  │
        │                  │  │ (naive support)   │  │ .com (free tier)   │
        └──────────────────┘  └───────────────────┘  └────────────────────┘
                                       │
                                       │ (target's own Phoenix project,
                                       ▼  separate from ChaosLab's)
                              ┌────────────────────┐
                              │ Phoenix Cloud      │
                              │ project: target-   │
                              │ agent-traces       │
                              └────────────────────┘
```

Three Cloud Run services in the demo: `chaoslab-web`, `chaoslab-agent`, `target-agent`. One MCP server (`@arizeai/phoenix-mcp` spawned via `npx` inside `chaoslab-agent`). One external service (Phoenix Cloud) holding traces.

Why three services and not one Docker monolith: separation of "the agent doing the attacking" from "the agent getting attacked" is the demo's entire conceptual payload. Fold them and the judge can't tell what's what. Three URLs, three logs, three Phoenix projects = three clean planes the demo video can show.

[UNVERIFIED] Whether to put a custom domain (`chaoslab.dev` or similar) in front. Per `brainstorm/05-ecosystem-refactor.md` Day 7, this is a polish item, not a requirement. The default `*.run.app` URL is judge-acceptable. Cut if behind.

---

## 2. Cloud Run vs Agent Runtime — pick the right host

This is the single biggest architectural call. Both are allowed per hackathon rules. Re-read `02a` §5 and `02b` §5 first.

### Side-by-side for ChaosLab specifically

| Dimension | Cloud Run | Agent Runtime (Agent Engine) |
|---|---|---|
| Container model | Any Docker | ADK-tied PaaS, no Docker |
| Public HTTP URL | Yes, native | No — must front with a Cloud Run/Cloud Functions/SDK caller |
| Cold start (typical) | 1-3s Python, up to 5s with deps ([Cloud Run docs](https://docs.cloud.google.com/run/docs/tips/general)) | **<1s** documented per `02b` §5 |
| Continuous reasoning ceiling | HTTP request timeout: 60min max (configurable up to 60min) | **Up to 7 days** per `02b` §5 |
| Session/memory | Roll your own | Built-in (Agent Sessions + Memory Bank) |
| Observability | Cloud Logging only | Native Agent Observability dashboards |
| Cost shape | Per vCPU-sec + GiB-sec + requests (see §5) | Per vCPU-hr + GiB-hr — billed for active agent time, idle is free per [Vertex AI Agent Engine pricing](https://cloud.google.com/vertex-ai/pricing) |
| Free tier | 180k vCPU-sec, 360k GiB-sec, 2M req/month | 50 vCPU-hrs + 100 GB-hrs/month |
| Lock-in | Low (it's Docker) | High (ADK + Vertex AI SDK only) |
| Phoenix OpenInference attach | Trivial, works in container | [UNVERIFIED] — `partner-arize.md` shows it works on ADK runtimes generally, but specific Agent Runtime startup-hook semantics for OpenInference instrumentation registration may differ |

### ChaosLab workload analysis

ChaosLab's hot path per demo run:
1. Judge clicks "Run Chaos Sweep" in the web UI
2. ChaosLab agent enumerates ~12 attack scenarios (fault-class × test-input matrix)
3. For each scenario: invoke target-agent with adversarial input
4. Target-agent does its thing (3 tool calls, 1-3 LLM calls)
5. ChaosLab fetches resulting Phoenix traces via Phoenix MCP
6. ChaosLab runs LLM-as-judge eval rubric (1 Gemini call per scenario)
7. ChaosLab aggregates resilience curve, returns to web UI

Total wall-clock per Run button: **~60-180 seconds**. That's well inside Cloud Run's 60-minute HTTP timeout. ChaosLab does NOT need 7-day continuous reasoning. The "long-running" framing was a red herring — the long-running candidate would be a true autonomous agent that runs unprompted for days. ChaosLab is request/response: judge clicks, agent runs a finite sweep, agent returns.

The cold-start delta matters more. <1s vs 3-5s could be the difference between "judge sees instant response" and "judge wonders if it's broken". But Cloud Run's `min-instances=1` during the judging window eliminates Cloud Run's cold start (see §6) — for ~$3-4/month per service. That kills Agent Runtime's main edge for this use case.

### Recommendation: Cloud Run for everything

**All three services on Cloud Run.** Specifically:

- `chaoslab-web` — Cloud Run, request-based billing, min-instances=1 during judging
- `chaoslab-agent` — Cloud Run, request-based billing, min-instances=1 during judging, `adk api_server` baked into the Dockerfile
- `target-agent` — Cloud Run, request-based billing, min-instances=0 (cold-start tax is fine for the victim — it just adds 2s to each attack's wall-clock)

Reasoning:
1. **Single deployment story.** One `gcloud run deploy` per service, one set of mental models.
2. **Public URL native.** No SDK-proxy layer in front of Agent Runtime.
3. **Cost is bounded and observable.** Per-second billing with min-instances warm-up is predictable; Agent Runtime's per-vCPU-hour shape is similar but with less per-request granularity.
4. **Phoenix OpenInference attach is the verified path.** `partner-arize.md` and the ChaosLab Day-1 cadence in `brainstorm/05-ecosystem-refactor.md` Appendix C explicitly call out "Cloud Run + OpenInference auto-instrumentation" as the wired path. Agent Runtime + OpenInference is [UNVERIFIED] and not worth the discovery time on Day 1.
5. **Cut Agent Runtime as a stretch.** If Abu finishes Day 7 with margin, he can swap `chaoslab-agent` to Agent Runtime to demo the platform-native runtime in the video — but it's a swap, not the build target.

### When you'd flip the call

If ChaosLab's wedge included "agent runs for 6 hours autonomously crawling target-agent failure modes" (it doesn't — bounded sweep), Agent Runtime's 7-day continuous reasoning would be load-bearing.

---

## 3. Phoenix Cloud vs self-hosted Phoenix

This is the second biggest call. Phoenix has two deploys: managed at `app.phoenix.arize.com`, and OSS Docker image you can run yourself.

### Side-by-side

| Dimension | Phoenix Cloud (AX Free) | Self-hosted OSS Phoenix |
|---|---|---|
| Setup time | ~5 min (sign up, copy API key) | ~30-90 min (Docker, persistent volume, ingress, TLS) |
| Cost | $0 forever ([Arize pricing](https://phoenix.arize.com/pricing/)) | Compute cost on Cloud Run or VM (~$5-15/mo for a small instance) |
| Span limit | 25k spans/month | Unlimited (subject to your storage) |
| Ingestion volume | 1 GB/month | Unlimited |
| Retention | 15 days | You configure (default lifetime of storage volume) |
| Project count | [UNVERIFIED — listed N/A in their pricing page] | Unlimited |
| Annotation write access | Yes, via Phoenix MCP write tools | Yes, plus direct DB access |
| Debug endpoints | Limited | Full (you own the server) |
| Auth | Email/password + API keys | Whatever you configure |
| Trial expiry | None — free tier is permanent | N/A |
| Operational burden in judging window | Zero — Arize keeps it up | Yours — if your Phoenix VM crashes, demo URL is partially broken |

### What the OSS version gives you that the cloud doesn't

[UNVERIFIED] Based on Arize docs scan during research:
- Direct write access to span annotations via DB (not just API)
- Custom retention policies beyond 15 days
- Custom eval LLM plug-ins beyond what AX Free exposes
- Air-gapped option (irrelevant for a public demo)

None of these matter for a 9-day hackathon build where the demo runs ~50 attack sweeps total.

### Math on the span budget

Each ChaosLab demo run emits, roughly:
- Target agent: 12 attacks × ~5 spans per attack invocation = 60 spans
- ChaosLab agent: 12 evals × ~3 spans each + orchestration overhead ≈ 50 spans
- Total per demo: ~110 spans

25k spans/month ÷ 110 spans/demo = **~227 demo runs/month**.

Across 9 days of dev (call it ~150 dev runs, generous) + 4 weeks of judging (call it ~50 judge runs, very generous — most judges click Run once or twice), Abu uses **~200 demos × 110 spans = 22k spans over the entire build + judging window**. Comfortably under the monthly cap, assuming the months don't roll over badly.

The 15-day retention is the real constraint: spans from Day 1 of the build are gone by Day 16. The demo URL itself must regenerate fresh spans on each Run click — no relying on "see these old traces from yesterday". Good — that's how the demo works anyway.

### Recommendation: Phoenix Cloud (AX Free)

For ChaosLab's 9-day build + 4-week judging window:

- **Use Phoenix Cloud.** Zero ops burden, zero cost, instant setup. Day 0 of the cadence (`brainstorm/05-ecosystem-refactor.md` Appendix C) is "Phoenix Cloud account live" — this is the verified path.
- Provision **two Phoenix projects**: `chaoslab-traces` (the orchestrator's spans) and `target-agent-traces` (the victim's spans). The demo video splits the screen showing both.
- API key goes into Secret Manager (see §4).
- **Do NOT self-host.** The 30-90 min you'd spend Dockerizing Phoenix is the 30-90 min you need for the Day-6 resilience curve dashboard. Operational discipline says: don't take on infra you don't need.

[UNVERIFIED] Whether Phoenix Cloud free tier truly imposes zero credit-card requirement. The Arize Rapid Agent Hackathon partner page should confirm — search results say "free SAAS option" but don't explicitly say "no card on file required". Re-verify at sign-up. If a card IS required and Abu doesn't want to give one, fall back to self-hosted on a small Cloud Run instance ($5-10/mo).

---

## 4. Secret management

### What secrets does ChaosLab handle?

| Secret | What it is | Used by | Sensitivity |
|---|---|---|---|
| `PHOENIX_API_KEY` | Phoenix Cloud API key for OpenInference traces + Phoenix MCP | `chaoslab-agent`, `target-agent` | High — exposes all spans |
| `GEMINI_API_KEY` / Vertex AI default credentials | Gemini access. On GCP, default to **Application Default Credentials (ADC) via the service account** — no API key file needed in-container. | `chaoslab-agent` (model calls + judge LLM), `target-agent` | High — burnable credit |
| `GITLAB_PAT` | GitLab personal access token for MR emission stretch goal | `chaoslab-agent` (only if Day 7 GitLab stretch ships) | High — write access to a repo |
| `VOYAGE_AI_KEY` | Voyage embeddings for MongoDB MCP | Not used in ChaosLab — MongoDB MCP isn't in the wedge | N/A |
| `TARGET_AGENT_URL` | URL of the victim agent (Cloud Run autogenerated) | `chaoslab-agent` | Low — public URL anyway, but config-y so worth managing |

Voyage AI is not needed; ChaosLab's MCP server is Phoenix, not MongoDB. Skip.

### Why direct env vars on Cloud Run are NOT enough

Cloud Run lets you set env vars in two ways:
1. **`--set-env-vars KEY=value`** — plain text, stored in service config, visible to anyone with `roles/run.viewer`. **Wrong for secrets.**
2. **`--set-secrets KEY=secret-name:version`** — Cloud Run reads the secret from Secret Manager at startup and injects as env var into the container. **Right for secrets.**

Path 1 is tempting on Day 1 (faster), but:
- The secret value lives in the service revision config forever, retrievable by anyone with viewer rights including a future you who forgets and tweets a screenshot
- Rotating the secret means redeploying the service with a new env var (vs updating one Secret Manager version)
- `gcloud run services describe` dumps it in plaintext
- Hackathon judges include people who can inspect Cloud Run configs if they're curious — leaked Phoenix key, leaked GitLab PAT = blast radius

Path 2 keeps the secret value in Secret Manager only, with audit logs of every access. Cost: $0.06/active-version/month + free tier covers 6 versions and 10k accesses ([Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)). ChaosLab has 3 real secrets — fits free tier with margin.

### Setup commands (Day 1)

```bash
# Create Phoenix API key secret
echo -n "<paste phoenix key>" | gcloud secrets create phoenix-api-key \
    --data-file=- --replication-policy=automatic

# Create GitLab PAT secret (only if Day 7 stretch is on)
echo -n "<paste gitlab PAT>" | gcloud secrets create gitlab-pat \
    --data-file=- --replication-policy=automatic

# Grant Cloud Run service account access
PROJECT_ID=$(gcloud config get-value project)
RUNTIME_SA="${PROJECT_ID}-compute@developer.gserviceaccount.com"
# (or a dedicated SA you create — see below)

gcloud secrets add-iam-policy-binding phoenix-api-key \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gitlab-pat \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"

# Deploy Cloud Run service with secret injection
gcloud run deploy chaoslab-agent \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/agent:latest \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=$RUNTIME_SA \
    --set-secrets=PHOENIX_API_KEY=phoenix-api-key:latest,GITLAB_PAT=gitlab-pat:latest \
    --memory=1Gi --cpu=1
```

### Dedicated service account vs default compute SA

The default `${PROJECT_ID}-compute@developer.gserviceaccount.com` has too many roles by default. For a hackathon-grade demo this is fine, but the "production polish" lift is:

```bash
gcloud iam service-accounts create chaoslab-runtime \
    --display-name="ChaosLab runtime SA"

# Grant ONLY what the agent needs:
RUNTIME_SA="chaoslab-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/aiplatform.user"           # Gemini access via Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/run.invoker"               # to call sibling services
```

Mention this in the demo video as "least-privilege service account per agent" — earns Tech Implementation points and matches `02b` §9 "Agent Identity" platform primitive.

### Gemini auth specifically

On Cloud Run, prefer **Application Default Credentials via the service account** over an explicit `GEMINI_API_KEY`. The `google-genai` Python SDK auto-picks up ADC. No secret needed. This is also the only path that bills against the $100 Cloud credit — AI Studio API keys bill separately (see `02a` §6).

---

## 5. Cost projection — fitting under $100 credit

### Cost lines

| Line | Driver | Rate (verified 2026) |
|---|---|---|
| Gemini 3.5 Flash input tokens | Model calls | $1.50/M tokens ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)) |
| Gemini 3.5 Flash output tokens | Model calls | $9.00/M tokens |
| Gemini 3.5 Flash cached input | Model calls | $0.15/M tokens |
| Gemini 3.1 Flash-Lite input | Cheaper sub-agent / judge calls | $0.25/M tokens |
| Gemini 3.1 Flash-Lite output | Cheaper sub-agent / judge calls | $1.50/M tokens |
| Cloud Run vCPU-sec (request-based) | Per-request compute | $0.000024/vCPU-sec |
| Cloud Run GiB-sec | Memory per request | $0.0000025/GiB-sec |
| Cloud Run requests | Per request | $0.40/M (after 2M/month free) |
| Cloud Run min-instances idle | Warm pool 24/7 | ~$3-4/month per warm instance (256Mi-1Gi) |
| Artifact Registry | Docker image storage | $0.10/GB/month (first 0.5GB free) |
| Cloud Storage | Any artifacts | $0.02/GB/month standard |
| Secret Manager | 3 secrets active | $0 (under 6-version free tier) |
| Cloud Logging | Logs | First 50 GiB/project/month free |

### Phase 1 — Dev (9 days, 2026-06-02 → 2026-06-11)

**Token usage estimate:**
- ~150 dev runs across 9 days (testing ADK locally + Cloud Run smoke tests)
- Per run: ~12 attacks × (target agent ~3 LLM calls @ ~2k input + 500 output each) + ChaosLab orchestrator ~12 judge evals @ ~3k input + 200 output
  - Per attack: target agent 6k in / 1.5k out ≈ 9k tokens
  - Per eval: judge 3k in / 200 out ≈ 3.2k tokens
  - Plus ChaosLab orchestrator overhead ~20k in / 5k out per run
- Per run total: ~12 × 12.2k = 146k tokens + 25k orchestrator = **~170k tokens/run**, split ~80% input / 20% output
- 9-day total: 150 runs × 170k = **25.5M tokens** (~20M in, ~5M out)

**Token cost (Gemini 3.5 Flash everywhere):**
- Input: 20M × $1.50/M = **$30.00**
- Output: 5M × $9.00/M = **$45.00**
- **Phase 1 token subtotal: $75**

That's the worst case with no caching, no Flash-Lite, no batch mode. Apply cost optimizations (next subsection) and this drops fast.

**Cloud Run dev:**
- 150 runs × ~120s/run × 1 vCPU × 1 GiB = 18,000 vCPU-sec + 18,000 GiB-sec
- vCPU: 18,000 × $0.000024 = $0.43
- Memory: 18,000 × $0.0000025 = $0.045
- **Free tier covers this fully** (free 180k vCPU-sec/mo)
- **Phase 1 Cloud Run subtotal: ~$0**

**Phase 1 total: ~$75** if absolutely no optimization. ~$25-40 with sensible optimization.

### Phase 2 — Judging window (4 weeks, 2026-06-22 → 2026-07-06 + buffer)

**Token usage estimate:**
- ~50 total judge runs across the window (18 judges × 2-3 clicks each + buffer)
- Same per-run cost: 170k tokens
- 4-week total: 50 × 170k = **8.5M tokens** (~6.8M in, ~1.7M out)
- Input: 6.8M × $1.50/M = $10.20
- Output: 1.7M × $9.00/M = $15.30
- **Phase 2 token subtotal: ~$25.50**

**Cloud Run idle (warm pool):**
- 2 services with min-instances=1 (chaoslab-web, chaoslab-agent) × ~$3.50/mo × 4 weeks ≈ $7
- target-agent at min-instances=0 (cold-start fine for the victim) → $0
- **Phase 2 Cloud Run subtotal: ~$7**

**Cloud Run request:**
- 50 runs × 120s × 1 vCPU × 1 GiB across 2 services = 12,000 vCPU-sec
- $0.29 — fits free tier
- **~$0**

**Artifact Registry:**
- ~500MB Docker image × 3 services + revisions × 4 weeks ≈ $0.50
- **~$1**

**Phase 2 total: ~$33.50** (the warm pool is the biggest line, not the tokens).

### Combined total (no optimization)

**$75 (dev) + $33.50 (judging) = ~$108.50.**

That's $8.50 OVER the $100 credit. Sanity check failed. Apply optimizations:

### Cost optimizations (apply at least 2 of 3)

1. **Use Flash-Lite for the LLM-as-judge eval step.** Eval is "did the target agent respond safely?" — a classification task, not deep reasoning. Flash-Lite is $0.25/M in vs $1.50/M in (6× cheaper) and $1.50/M out vs $9.00/M out (6× cheaper). Drops the judge-eval token cost to ~1/6th. Savings on Phase 1: judge-eval is ~30% of tokens → savings of ~$15. **Net Phase 1: $60.**

2. **Cache the target-agent system prompt.** Phoenix MCP and ADK both support prompt caching (Gemini 3.5 Flash cached input = $0.15/M, 10× cheaper than fresh input). The target-agent's instruction prompt is the same on every attack — cache it. Drops input cost ~50%. Phase 1 savings: ~$15. **Net Phase 1: $45.**

3. **Skip min-instances=1 during dev.** Only enable warm pool from 2026-06-15 onwards (one week before judging starts). Saves ~$3-4 × 2 weeks = $7. **Net Phase 2: $26.50.**

4. **(Stretch) Batch mode for the Day-2 fault-catalog generation.** Batch mode halves cost. Probably overkill for hackathon scale.

**Optimized total: ~$45 (dev) + ~$27 (judging) = ~$72.** Fits $100 with $28 margin for surprises.

### Biggest cost surprise

The **warm pool (min-instances=1)** is a bigger line during judging than tokens are. Naive intuition says "tokens dominate". For a hackathon-scale demo (50 judge runs over 4 weeks), idle compute outweighs request compute. Don't enable min-instances=1 for the entire 9-day dev cycle, or you double the Phase-1 idle bill.

### Burn-rate alarm

Set Cloud Billing budget alert at **$70** (70% of credit). Configure at `console.cloud.google.com/billing/budgets`. Email yourself when it trips. The credit auto-fences spend after $100, but the alert gives you a chance to switch off min-instances and downshift to Flash-Lite before the demo runs dry.

[UNVERIFIED] Gemini 3.5 Flash output price of $9.00/M was current as of 2026-05-19 per [apidog pricing analysis](https://apidog.com/blog/gemini-3-5-flash-pricing/) — verify at the official [pricing page](https://ai.google.dev/gemini-api/docs/pricing) when Abu redeems the credit. If the rate is now $4.50/M or $12/M, redo the math.

---

## 6. The 4-week judging-window survival plan

Submit on Jun 11. Judging Jun 22 → Jul 6. Winner notify ~Jul 7. The demo URL must be CLICKABLE and RESPONSIVE the entire time, including ~Jun 11 → Jun 22 quiet stretch when nobody's looking.

### What can break

| Risk | Detection | Mitigation |
|---|---|---|
| Cloud Run cold start eats first impression | Manual test | min-instances=1 from Jun 18 onward |
| Cloud Run service crashes (OOM, panic) | Cloud Logging error rate alert | Auto-restart is Cloud Run default; add liveness check |
| Phoenix Cloud free-tier span cap hit mid-judging | Phoenix dashboard | 25k/mo limit; rolls over monthly; monitor at week 3 |
| Phoenix Cloud retention rollover (15 days) | N/A — by design | Demo regenerates fresh spans on each click; safe |
| Gemini API rate-limit during simultaneous judges | 429 in logs | Set max-concurrency on Cloud Run; queue if >2 simultaneous demos |
| Gemini 3.5 Flash model deprecated | Search Vertex AI release notes | Unlikely in 4 weeks; pin to model ID `gemini-3.5-flash` not `gemini-flash-latest` |
| Secret rotation (e.g., Phoenix API key expired) | Cloud Run logs auth errors | Phoenix Cloud API keys don't auto-expire [UNVERIFIED but typical]; mint a fresh one before Jun 22 just in case |
| Cloud Run image purged from Artifact Registry | Image-pull error on cold start | Keep image; AR doesn't garbage-collect without explicit retention policy |
| ADK package version drift | Local dev still works, prod doesn't | Pin `google-adk==X.Y.Z` in `requirements.txt`, never `>=` |
| `npx @arizeai/phoenix-mcp` connectivity flaky | Tool-call errors in agent logs | Container-local subprocess; verify `npx` works in Dockerfile during build |
| $100 credit exhausted | Billing alert | Set alert at $70; pre-emptive cost optimizations |
| Anti-bot / WAF blocks judges' IPs | Manual test from incognito | Don't add a WAF; Cloud Run default ingress is fine |

### Concrete keep-alive mechanism

`min-instances=1` from Jun 18 onward keeps `chaoslab-web` and `chaoslab-agent` warm. Cost: ~$7 for the 4 weeks.

If Abu wants belt-and-suspenders, add a **Cloud Scheduler job** that hits the demo URL every 5 minutes:

```bash
gcloud scheduler jobs create http chaoslab-warmup \
    --schedule="*/5 * * * *" \
    --uri="https://chaoslab-xxxxx-uc.a.run.app/healthz" \
    --http-method=GET \
    --location=$REGION
```

Cost: 3 jobs × $0.10/job/month = $0.30. ($0.10/job/mo per [Cloud Scheduler pricing](https://cloud.google.com/scheduler/pricing) — first 3 jobs free.) Free.

### Monitoring

For a hackathon, simple > sophisticated:

1. **Cloud Logging** built-in for all 3 services. Filter to severity >= ERROR and create an alert policy that emails Abu when error count > 5 in 10 min.

2. **Uptime check** via Cloud Monitoring on the public URL. Hits every 1 minute, alerts if 3 consecutive failures. Free under the first 1M check-executions.

3. **Phoenix Cloud's own dashboard** — log in once a day during judging to see new spans land.

4. **Devpost notification** — judges sometimes ask questions through the platform. Check daily.

### Disaster recovery: if the demo URL dies during judging

| Failure | Recovery action | RTO |
|---|---|---|
| Cloud Run service returning 5xx | `gcloud run services update --update-env-vars=BUMP=$(date +%s)` to force new revision | <5 min |
| Cloud Run service deleted | Re-run the deploy script from repo `infra/deploy.sh` | <10 min |
| Phoenix Cloud down | Wait — it's their problem. Worst case, swap demo to "trace-less mode" via a feature flag in the agent | depends |
| GCP project quota exceeded | Request quota increase via console; usually approved in 1-2 hours for low-volume hackathon | ~2 hr |
| $100 credit exhausted (billing freezes) | Top up with personal $20 — same billing account | <30 min |
| ADK breaks due to dep update | Image is pinned; this can't happen at runtime unless someone redeploys | N/A |

Keep `infra/deploy.sh` in the repo. Keep a tested local Docker image you can re-push as a last-resort. Keep `.env.example` updated so Abu can re-bootstrap from a different GCP account if the original gets banned (unlikely but cheap insurance).

---

## 7. Repo structure

GitHub repo IS a judging surface. The README is read first; clean structure earns Tech Implementation points (`01-prizes-tracks.md`).

### Recommended top-level layout

```
chaoslab/                       # repo root
├── README.md                   # judge entry point — see §README sections below
├── LICENSE                     # MIT (see §License below)
├── .gitignore
├── .env.example                # documented env var names, no secrets
│
├── chaoslab/                   # the orchestrator agent (the ChaosLab itself)
│   ├── agent.py                # root_agent = LlmAgent(...) — Gemini 3.5 Flash
│   ├── attacks/                # one file per fault class
│   │   ├── __init__.py
│   │   ├── malformed_tool_output.py
│   │   ├── prompt_injection.py
│   │   ├── context_poisoning.py
│   │   └── mcp_flakiness.py
│   ├── judge.py                # LLM-as-judge eval rubrics
│   ├── recipe.py               # hardening recipe generator (Day 5)
│   ├── phoenix_mcp.py          # MCPToolset wiring for @arizeai/phoenix-mcp
│   ├── server.py               # adk api_server entrypoint
│   ├── Dockerfile
│   └── requirements.txt        # pinned versions
│
├── target_agent/               # the deliberately-naive support agent (the victim)
│   ├── agent.py                # naive_root_agent — Gemini 3.5 Flash, 3 tools, no validation
│   ├── tools/
│   │   ├── lookup_order.py
│   │   ├── issue_refund.py
│   │   └── escalate_ticket.py
│   ├── server.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # demo UI
│   ├── (Next.js OR Streamlit — pick one)
│   ├── pages/index.tsx OR app.py
│   ├── Dockerfile
│   └── package.json OR requirements.txt
│
├── infra/                      # everything deploy-related
│   ├── deploy.sh               # bash; gcloud commands to deploy all 3 services
│   ├── secrets-setup.sh        # one-shot to create + bind Secret Manager
│   ├── cloud-build.yaml        # (stretch) — auto-deploy on push
│   └── monitoring.yaml         # uptime check + alert policy as code
│
├── eval/                       # eval datasets + rubrics (Day 3+)
│   ├── attack-corpus.json      # the 12 baseline attack inputs
│   ├── judge-rubrics.md        # what "passed" / "failed" means
│   └── golden-traces/          # canonical Phoenix trace exports for the dataset
│
├── docs/                       # per Sahil spec writer conventions
│   ├── ARCHITECTURE.md         # this file's twin — system diagram + flow
│   ├── DEMO-SCRIPT.md          # the 3-min video script
│   └── KNOWN-LIMITATIONS.md    # candid scope-cuts (judges respect this)
│
└── .github/
    └── workflows/
        └── deploy.yml          # GitHub Actions deploy on push to main (stretch)
```

### License

**MIT.** Apache-2.0 is also fine, but MIT is shorter, more permissive, and judges who skim see "MIT" and move on — Apache-2.0's contributor-license-grant clauses make some reviewers pause unnecessarily.

The hackathon rules don't mandate a specific license, just "open source". `LICENSE` file at repo root is the standard answer.

[UNVERIFIED] Specific judging rubric weight for license choice — but `01-prizes-tracks.md` confirms an OSS license is required for submission. Without it = DQ.

### README sections that win

Per `05-prior-winners.md` pattern (and `01-prizes-tracks.md` judging criteria):

1. **Title + one-line tagline.** "ChaosLab — chaos engineering for AI agents."
2. **Demo video embed** (YouTube link → 3-min video).
3. **Live demo URL** (Cloud Run public URL).
4. **The pain in one paragraph.** Solo devs ship AI agents with no resilience tests. ChaosLab runs a 12-attack sweep and grades.
5. **Architecture diagram** (the ASCII in §1 above, or a real image — Excalidraw export).
6. **Quick start** (deploy your own — see §8).
7. **Tech stack** with versions — `google-adk==X.Y.Z`, Gemini 3.5 Flash, Phoenix MCP, etc.
8. **MCP integration callout** — name Phoenix MCP explicitly, show one tool call snippet (judges look for this on the Arize track).
9. **Resilience curve screenshot** — the before/after wow image.
10. **Limitations** — small bullet list of what's NOT shipped. Honesty signals.
11. **License: MIT** — at the bottom, simple.

Don't include: roadmap, "future work", marketing fluff. Judges scan; tighter = better.

### CI/CD: GitHub Actions vs manual

For 9 days, **manual `gcloud run deploy`** is the right call. CI/CD setup eats half a day. The shape:

```bash
# infra/deploy.sh
set -euo pipefail
PROJECT_ID=${PROJECT_ID:-chaoslab-demo}
REGION=${REGION:-us-central1}

for svc in chaoslab-agent target-agent chaoslab-web; do
  gcloud builds submit $svc \
    --tag $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/$svc:latest
  gcloud run deploy $svc \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/$svc:latest \
    --region $REGION \
    --allow-unauthenticated \
    --service-account chaoslab-runtime@$PROJECT_ID.iam.gserviceaccount.com \
    --set-secrets PHOENIX_API_KEY=phoenix-api-key:latest
done
```

GitHub Actions is a stretch goal for Day 7 polish. Workflow:

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: deployer@${{ secrets.GCP_PROJECT }}.iam.gserviceaccount.com
      - uses: google-github-actions/setup-gcloud@v2
      - run: bash infra/deploy.sh
```

Workload Identity Federation is the right auth posture (vs storing GCP service-account JSON in GitHub secrets). But the WIF setup is ~1 hour of yak-shaving — skip for the 9-day build, add post-submit if Abu wants ongoing demo updates during the judging window.

---

## 8. Demo data + sandbox state

### Pre-loaded sample data

The demo URL needs to "just work" — judge clicks Run, sees attacks executed and graded against a pre-staged target agent. Where the state lives:

| Asset | Where it lives | Why |
|---|---|---|
| **Naive target agent** | `target_agent/` deployed as its own Cloud Run service | The "victim" is part of the demo; judge sees it being attacked |
| **Attack catalog (12 scenarios)** | `eval/attack-corpus.json` in the repo, baked into the chaoslab-agent Docker image | Static — no need for a DB |
| **Judge eval rubrics** | `eval/judge-rubrics.md` (prompt-only) → embedded into the eval LLM's system prompt | Static |
| **Resilience curve baseline** | Re-computed live on each demo run by re-attacking the unhardened target | Fresh on every click — no staleness risk |
| **Resilience curve "after"** | Re-computed live by attacking the hardened-version target | Same |
| **Phoenix traces** | Phoenix Cloud projects `chaoslab-traces` and `target-agent-traces` | Live, regenerated per run; 15-day retention is fine |
| **Golden trace snapshots** | `eval/golden-traces/` JSON files for offline tests | Repo-checked-in, immutable |
| **Hardening recipes** | Generated live by ChaosLab → written to in-memory state, displayed in UI, optionally to GCS bucket for download | If GCS: bucket `chaoslab-demo-artifacts`, public-read with bucket-level ACL |

No real DB. ChaosLab doesn't have a "user account" concept; every demo session is ephemeral. Session state lives in the ADK in-memory session service (`InMemorySessionService` from `02a` §3) — fine because Cloud Run with min-instances=1 keeps that memory alive across requests in normal operation, and even if Cloud Run rotates the instance, the worst case is the user clicks Run again.

### "Deploy your own ChaosLab" — making it frictionless for curious judges

The README's Quick Start should be 5 commands:

```bash
# 1. Clone
git clone https://github.com/abu/chaoslab && cd chaoslab

# 2. Set GCP project + region
export PROJECT_ID=your-project   REGION=us-central1
gcloud config set project $PROJECT_ID

# 3. Enable APIs
gcloud services enable run.googleapis.com \
    secretmanager.googleapis.com aiplatform.googleapis.com \
    artifactregistry.googleapis.com cloudbuild.googleapis.com

# 4. Set secrets (only Phoenix key required)
echo -n "<your-phoenix-key>" | gcloud secrets create phoenix-api-key --data-file=-

# 5. Deploy
bash infra/deploy.sh
```

After step 5, deploy.sh prints the 3 Cloud Run URLs. Open the `chaoslab-web` URL = working demo on the judge's own GCP account.

[UNVERIFIED] Whether judges actually re-deploy. Most don't — they click the hosted URL and watch. But the README's frictionless deploy story signals "this is a real engineer's work, not a demo-driven prototype" — earns Tech Implementation points even if no judge actually runs it.

### Sample target agents that ship with ChaosLab

For the 9-day build, ship one:

- **`target_agent/` — naive customer support agent.** 3 tools (`lookup_order`, `issue_refund`, `escalate_ticket`), no input validation, no PII guard, no tool-output sanitization. Will refund any order, will escalate based on prompt-injected instructions, will leak its system prompt when asked nicely.

Stretch for Day 7 if margin exists:

- **`target_agent_v2/` — naive HR onboarding agent.** Different domain (so judges see ChaosLab isn't domain-tied), same naivete shape.

The hackathon ships ONE target. Anything more is gilding.

---

## 9. Risk register — what kills the deploy

Top deployment-shaped failure modes for the 9-day build + 4-week judging window. Format: probability / blast radius / mitigation / recovery time.

| # | Risk | P | Blast | Mitigation | Recovery |
|---|---|---|---|---|---|
| 1 | **Cloud Run cold start eats first impression** | Med | High (judge bounces in <5s) | min-instances=1 from Jun 18; warm-ping Cloud Scheduler every 5 min | 0 (preventive) |
| 2 | **Phoenix MCP via `npx` keep-alive flakes on Cloud Run** (per `brainstorm/05-ecosystem-refactor.md` Day-3 risk + `CONTEXT.md` OQ-3) | Med | High (Phoenix integration is the entire wedge) | Test locally Day 2; fall back to stdio launch via `subprocess.Popen` if Streamable HTTP misbehaves; pin `@arizeai/phoenix-mcp` version | <2hr (swap import) |
| 3 | **$100 credit exhausted before judging ends** | Low (with optimization) | High (demo URL 5xxs when Vertex AI billing freezes) | Apply optimizations §5; alarm at $70; top up $20 personal if needed | <30 min (top-up) |
| 4 | **Gemini 3.5 Flash rate-limit during simultaneous judges** | Low (1 judge at a time mostly) | Med (demo run fails) | Set Cloud Run max-concurrency=1; add retry+jitter on 429 | <0 (auto-retry) |
| 5 | **GitLab MCP rate-limits during stretch MR demo** | Med (if Day 7 ships) | Low (stretch feature; cuttable) | Demo MR-emit once, cache result; don't loop | N/A — cut feature |
| 6 | **ADK package version drift (1.x → 2.x mid-build)** | Low | Med (breaking API change) | Pin `google-adk==X.Y.Z` exactly in `requirements.txt`; lock Docker image | <1hr (revert to pinned version) |
| 7 | **Naive target agent stops being naive when Gemini 3.5 Flash quietly updates** | Med | Med (resilience curve flattens — demo's wow moment disappears) | Pin model ID `gemini-3.5-flash` not `gemini-flash-latest`; if 3.5 truly improves, sharpen attacks accordingly; record baseline trace screenshots Day 2 | 2-4 hr (sharpen attacks) |
| 8 | **Demo URL breaks because Cloud Run pod restart wipes in-memory session** | High (will happen mid-judging) | Low (judge clicks Run again — sessions are ephemeral by design) | Document this in README; ensure UI shows "Run" button always; no multi-step state | 0 (by design) |
| 9 | **Phoenix Cloud free-tier span cap (25k/month) hit during judging** | Low (~22k projected) | Med (no new traces visible — demo shows empty Phoenix) | Monitor at week 3; second Phoenix account ready as failover; rotation calendar-month aware | <30 min (point env var at backup) |
| 10 | **GCP project quota for Cloud Run vCPU exceeded** | Low | High (no new deploys) | Default quota is 1000 vCPU / region, ChaosLab uses 3; safe. Verify via `gcloud compute project-info describe` Day 1 | ~2 hr (request increase) |
| 11 | **Secret Manager IAM binding drifts (Cloud Run SA loses access)** | Low | High (agent 500s on startup, can't read Phoenix key) | Bake binding into `infra/deploy.sh`; re-apply on every deploy | <5 min |
| 12 | **Custom domain DNS misconfig blocks judges (only if Day 7 custom-domain ships)** | Med (DNS is finicky) | Med (judges use `*.run.app` fallback) | Document both URLs in submission; cut custom domain if behind | <30 min (kill DNS, use *.run.app) |

Risk #1 (cold start) and #2 (Phoenix MCP flakiness) are the load-bearing ones. Everything else is bounded or low-probability.

### Combined-risk mitigation: the 24h-before-judging checklist

On 2026-06-21 (T-1 day before judging opens):

1. Hit demo URL from 3 different networks (home, mobile data, incognito). Confirm <5s response.
2. Run 5 demos end-to-end. Confirm Phoenix shows traces. Screenshot the resilience curve.
3. Re-mint Phoenix API key; update secret version.
4. Confirm Cloud Logging alert policy is active.
5. Re-read the README from a stranger's perspective. Fix anything confusing.
6. Push a redeploy with `--update-env-vars=DEPLOY_DATE=2026-06-21` to force fresh revision (catches any base-image rot).
7. Set min-instances=1 on `chaoslab-web` and `chaoslab-agent` if not already.
8. Bookmark Cloud Console > Cloud Run > each service > Logs for one-click incident response.

---

## 10. The first concrete deployment step

Day 1 (2026-06-03) of `brainstorm/05-ecosystem-refactor.md` Appendix C: **naive target agent + Phoenix wiring on Cloud Run, with first traces visible in Phoenix Cloud.**

The smallest unit of "I have shipped to GCP" is even smaller than that: **hello-world ADK agent on Cloud Run, one trace in Phoenix Cloud.** That's Day 1, hour 1.

### Exact commands (assumes $100 credit redeemed, GCP project created, gcloud CLI auth'd)

```bash
# ---------- one-time project setup ----------
export PROJECT_ID=chaoslab-demo
export REGION=us-central1
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Enable required APIs
gcloud services enable run.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com

# Artifact Registry repo for Docker images
gcloud artifacts repositories create chaoslab \
    --repository-format=docker --location=$REGION

# ---------- create Phoenix Cloud project ----------
# (manual: sign up at app.phoenix.arize.com, create project "hello-adk", copy API key)

# Store Phoenix key in Secret Manager
echo -n "<paste phoenix key>" | gcloud secrets create phoenix-api-key \
    --data-file=- --replication-policy=automatic

# Dedicated service account
gcloud iam service-accounts create chaoslab-runtime \
    --display-name="ChaosLab runtime SA"
RUNTIME_SA="chaoslab-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding phoenix-api-key \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/aiplatform.user"

# ---------- write the hello-world agent ----------
mkdir -p chaoslab && cd chaoslab
cat > requirements.txt <<'EOF'
google-adk==1.16.0
openinference-instrumentation-google-adk
opentelemetry-exporter-otlp
phoenix-otel
EOF

cat > agent.py <<'EOF'
import os
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from google.adk.agents import Agent

# Phoenix Cloud OTLP setup
tracer_provider = register(
    project_name="hello-adk",
    endpoint="https://app.phoenix.arize.com/v1/traces",
    headers={"api_key": os.environ["PHOENIX_API_KEY"]},
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

root_agent = Agent(
    name="hello_agent",
    model="gemini-3.5-flash",
    instruction="You are a friendly hello-world agent. Greet the user warmly.",
)
EOF

cat > Dockerfile <<'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
ENV PORT=8080
CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8080"]
EOF

# ---------- build + deploy ----------
gcloud builds submit \
    --tag $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/hello-agent:v1

gcloud run deploy hello-agent \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/chaoslab/hello-agent:v1 \
    --region $REGION \
    --allow-unauthenticated \
    --service-account $RUNTIME_SA \
    --set-secrets PHOENIX_API_KEY=phoenix-api-key:latest \
    --memory 1Gi --cpu 1 --max-instances 3

# ---------- smoke test ----------
URL=$(gcloud run services describe hello-agent --region $REGION --format='value(status.url)')
curl -X POST "$URL/run" \
    -H "Content-Type: application/json" \
    -d '{"input": "say hello"}'

# Visit app.phoenix.arize.com → project "hello-adk" → confirm trace visible
```

That's it. Sub-30-minute Day-1 goal. Confirm:
1. `curl` returns a 200 with the agent's greeting
2. Phoenix Cloud > project "hello-adk" > Traces tab shows one entry with the model call span

Once both green-light: the riskiest Day-1 step (`brainstorm/05-ecosystem-refactor.md` Day-1 risk = "ADK + Phoenix wiring") is closed. Everything else in the 9-day cadence is incremental.

[UNVERIFIED] Exact import path of `phoenix.otel.register` and `openinference.instrumentation.google_adk.GoogleADKInstrumentor` against current package versions. Per `partner-arize.md` and the Arize hackathon resources page, these are the documented imports as of 2026-06-02 — verify with `pip show openinference-instrumentation-google-adk` after install. If imports moved, the OpenInference docs at `arize.com/docs/phoenix/integrations` have the current path.

[UNVERIFIED] The `adk api_server` CLI command's exact flag names — `02a` §5 references it but the precise `--host`/`--port` args may differ in current ADK versions. `adk api_server --help` is the source of truth after `pip install`.

---

## Summary

ChaosLab deploys as **3 Cloud Run services + Phoenix Cloud (free tier) + Gemini 3.5 Flash via Vertex AI** on a single GCP project. Secrets via Secret Manager bound to a dedicated runtime service account. Cost projects to **~$72 of the $100 credit** with two basic optimizations (Flash-Lite for judge LLM, prompt caching for target system prompt). The biggest cost line during judging is the **Cloud Run min-instances=1 warm pool** — not tokens — and the biggest infra risk is **Phoenix MCP keep-alive behavior under Cloud Run cold-start dynamics** (Day-3 verification step). Day-1 ship target = hello-world ADK agent on Cloud Run with one Phoenix trace, ~30 minutes of commands.

---

## Sources

- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) — official, re-verify before locking model
- [Gemini 3.5 Flash pricing analysis (apidog)](https://apidog.com/blog/gemini-3-5-flash-pricing/) — $1.50/M input / $9.00/M output (2026-05-19)
- [Gemini 3.1 Flash-Lite pricing](https://devtk.ai/en/models/gemini-3-1-flash-lite/) — $0.25/M input / $1.50/M output
- [Cloud Run pricing](https://cloud.google.com/run/pricing) — $0.000024/vCPU-sec, $0.0000025/GiB-sec, $0.40/M requests
- [Cloud Run min-instances cost analysis](https://cloudguard.dev/blog/cloud-run-min-instances) — ~$3.24/mo for 256Mi warm instance
- [Vertex AI Agent Engine pricing](https://cloud.google.com/vertex-ai/pricing) — $0.0864/vCPU-hr, $0.0090/GB-hr
- [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing) — $0.06/active-version/mo, 6 free
- [Arize Phoenix pricing](https://phoenix.arize.com/pricing/) — AX Free: 25k spans/mo, 1GB, 15-day retention
- [Arize Phoenix Cloud getting started](https://arize.com/docs/phoenix/phoenix-cloud) — Phoenix Cloud is the recommended path
- [Cloud Run cold start docs](https://docs.cloud.google.com/run/docs/tips/general) — 1-3s typical Python
- [Cloud Run min-instances feature](https://cloud.google.com/blog/products/serverless/cloud-run-adds-min-instances-feature-for-latency-sensitive-apps)
- Companion: `02a-google-cloud-stack.md` §5, §10
- Companion: `02b-gemini-enterprise-agent-platform.md` §5 (Agent Runtime), model version note
- Companion: `brainstorm/05-ecosystem-refactor.md` Appendix C (9-day cadence)
- Companion: `CONTEXT.md` §3 (verified facts table)
- Companion: `partner-arize.md` (Phoenix MCP integration details — referenced for OpenInference wiring)
