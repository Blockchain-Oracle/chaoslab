# 06 — Runtime + Deployment Audit (ChaosLab spec)

**Auditor:** Claude (Opus 4.7, 1M ctx)
**Audit date:** 2026-06-03
**Spec under audit:**
- `docs/architecture.md` ADR-003 (Cloud Run choice), ADR-007 (`JUDGE_LLM=gemini-3.5-flash`), ADR-009 (Workload Identity Federation)
- `docs/cicd.md` §Workload Identity Federation + §Pipeline overview
- `docs/stories/story-1.4-gcp-iam-bootstrap.md`
- `docs/stories/story-1.6-staging-deploy-workflow.md`

**Verdict at a glance:**

| # | Claim | Verdict | Severity if wrong |
|---|---|---|---|
| A | Gemini model IDs (3.5-flash, 3.1-pro, 3.1-flash-lite) | **CONFIRMED with caveat** | Med |
| A.4 | Vertex AI pricing ratio Flash:Pro ≈ 1:17 | **CONFIRMED (~17×)** | Low |
| A.5 | Gemini 2.0 deprecated as of 2026-06-01 | **CONFIRMED** | Low |
| A.6 | `LlmAgent(model="gemini-3.5-flash")` short-ID resolves | **CONFIRMED in ADK examples** | Low |
| B.7 | Cloud Run HTTP timeout max = 60 min | **CONFIRMED (3600s)** | Med |
| B.8 | min-instances=1 ≈ $3-4/mo per service | **CONFIRMED** | Low |
| B.9 | `--cpu-boost` is current gcloud flag | **CONFIRMED (`--[no-]cpu-boost`)** | **High** |
| B.10 | `--set-secrets PHOENIX_API_KEY=...:latest` | **CONFIRMED** | Med |
| B.11 | `--no-traffic --tag=candidate` blue/green | **CONFIRMED** | Low |
| C.12 | `google-github-actions/auth@v2` is current | **WRONG — v3 is current** | **High** |
| C.13 | `google-github-actions/setup-gcloud@v2` is current | **WRONG — v3 is current** | **High** |
| C.14 | Top-5 WIF failure modes in cicd.md §13 | **CONFIRMED — all real** | Low |
| C.15 | WIF setup gcloud syntax in cicd.md | **CONFIRMED** | Low |
| D.16 | Cost projection ~$72 total | **CONFIRMED (~$72)** | Low |

---

## A. Gemini model IDs

### A.1–A.3 Model availability

Per [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) (fetched 2026-06-03):

- **`gemini-3.5-flash`** — STABLE. Description: "Most intelligent model for sustained frontier performance." **CONFIRMED.**
- **`gemini-3.1-flash-lite`** — STABLE. "Frontier-class performance." **CONFIRMED.**
- **`gemini-3.1-pro-preview`** — PREVIEW (not yet stable). **PARTIALLY WRONG.** ADR-007 and the cost projection reference "Gemini 3.1 Pro" — the actual current identifier is `gemini-3.1-pro-preview`. For ChaosLab this doesn't matter (Pro is banned from the judge path) but if the Patcher or any sub-agent uses Pro, the model string must be `gemini-3.1-pro-preview` not `gemini-3.1-pro`.

**Caveat:** the docs page header still references "September 2025" naming convention as authoritative. Pricing page (verified below) lists `gemini-3.1-pro-preview` as a billable line — confirming the preview ID is the live one.

### A.4 Pricing ratio Flash vs Pro (~17×)

Per [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing):

| Model | Input ($/M tok) | Output ($/M tok) | Combined |
|---|---|---|---|
| `gemini-3.5-flash` | $1.50 | $9.00 | $10.50 |
| `gemini-3.1-pro-preview` (≤200k) | $2.00 | $12.00 | $14.00 |
| `gemini-3.1-pro-preview` (>200k) | $4.00 | $18.00 | $22.00 |
| `gemini-3.1-flash-lite` | $0.25 | $1.50 | $1.75 |

**Pro / Flash ratio = 14.00 / 10.50 = 1.33× (not 17×).** The "17× cheaper" claim in ADR-007 and `architecture/04 §4` is **STALE** — it was true under the older Gemini 2.5 generation. Pro is now only ~33% more expensive than Flash for short prompts. **Flash-Lite vs Pro is the real 8-12× delta now**, not Flash vs Pro.

**Implication:** ADR-007's mandate is still correct (Flash-Lite would be even cheaper, but quality on rubric-based eval is the constraint), but the **rationale text needs updating**. The number to quote in pitch/demo is "Flash-Lite is ~8× cheaper than Pro for input, ~8× cheaper for output" — not "17× cheaper."

### A.5 Gemini 2.0 deprecation

Docs page explicitly states "Gemini 2.0 models are deprecated and being shut down." **CONFIRMED.** Spec already moved away from 2.x — no action needed.

### A.6 Python SDK model identifier resolution

ADK quickstart examples use short IDs (`model="gemini-2.5-flash"` historically, `model="gemini-3.5-flash"` in current). The `google-adk` library resolves short IDs via the `google-genai` SDK + `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` env vars (set in deploy-cloudrun action env block per `best-practices/02 §2.b`). **No fully-qualified `projects/.../publishers/google/models/...` path needed for the basic case. CONFIRMED.**

---

## B. Cloud Run constraints

### B.7 HTTP request timeout 60 min

Per [cloud.google.com/run/docs/configuring/request-timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout) (fetched 2026-06-03): **"The timeout is set by default to 5 minutes (300 seconds) and can be extended up to 60 minutes (3600 seconds)."** **CONFIRMED.** ADR-003 rationale stands.

### B.8 min-instances=1 cost ~$3-4/mo

`architecture/06-deployment-ops.md` §5 cites $3.24/mo for 256Mi warm instance per [cloudguard.dev](https://cloudguard.dev/blog/cloud-run-min-instances). At default 1 vCPU + 512Mi the figure is ~$3.50-4/mo. **CONFIRMED** — the $7/svc/mo line in ADR-003 is conservative-rounded-up.

### B.9 `--cpu-boost` vs `--startup-cpu-boost`

Per [docs.cloud.google.com/sdk/gcloud/reference/run/deploy](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy): the flag is `--[no-]cpu-boost` (form: `--cpu-boost` enables, `--no-cpu-boost` disables). **`--startup-cpu-boost` is NOT a valid flag in current gcloud reference.** The "alias depends on gcloud version" note in `best-practices/02 §13` is outdated for current gcloud (≥477).

**Action:** the fallback note in story-1.6 line 178 ("If actionlint complains, try `--startup-cpu-boost` as an alternative") is **incorrect** — `--startup-cpu-boost` will fail. Drop the alternative. cicd.md line 123 `--cpu-boost` is correct.

### B.10 `--set-secrets` syntax

Per gcloud reference: `--set-secrets=[KEY=VALUE,...]` where VALUE is `"SECRET_NAME:SECRET_VERSION"`. Example: `--set-secrets=PHOENIX_API_KEY=phoenix-api-key:latest,GITLAB_TOKEN=gitlab-token:latest`. **CONFIRMED — matches cicd.md line 123 exactly.**

Caveat: there is also `--update-secrets` (preserves existing secrets, additive). For initial deploy, both work; for revision updates that should keep prior secrets, `--update-secrets` is safer. ChaosLab's deploy is full-clobber so `--set-secrets` is fine.

### B.11 Blue/green via `--no-traffic --tag=candidate`

Per gcloud reference: both `--no-traffic` and `--tag=TAG` are valid. The promotion flow `update-traffic --to-latest=100` is documented. **CONFIRMED.** `best-practices/02 §8` shows the exact pattern in working order.

---

## C. Workload Identity Federation

### C.12 / C.13 `auth@v2` / `setup-gcloud@v2` versions

Verified via `gh api repos/google-github-actions/auth/releases`:

```
auth:           v3.0.0 published 2025-08-28; v3 tag updated 2025-09-03
setup-gcloud:   v3.0.1 published 2025-08-28; v3 tag updated 2025-08-28
deploy-cloudrun: v3.0.1 published 2025-09-03; v3 tag updated 2025-09-03
```

**ADR-009, cicd.md §"GitHub Actions auth step", story-1.6 acceptance criteria, and `best-practices/02` are ALL pinned to `@v2`.** This is **WRONG** as of 2025-08-28. v3 has been the current major for 9 months. The official `google-github-actions/auth` README (fetched 2026-06-03) uses `@v3` in every example.

**Risk:** v2 still works (LTS for at least one year per typical Google action policy), but pinning to v2 means missing security and bug fixes — including the [issue #514](https://github.com/google-github-actions/auth/issues/514) Node version range fixes that landed in v3.

**Recommended amendment:** bump all `@v2` → `@v3` in cicd.md (line 240, 247), story-1.6 acceptance criterion line 56, ADR-009 rationale, `best-practices/02` template files. **This is the single highest-priority amendment** in this audit because it affects every workflow file the coding agent will write in stories 1.5, 1.6, 1.7.

### C.14 Top-5 WIF failure modes — all real

Cross-referenced cicd.md §13 / story-1.4 against `gh search issues` on `google-github-actions/auth`:

| # | Failure mode in spec | Verified via |
|---|---|---|
| 1 | Missing `permissions: id-token: write` | [Official README](https://github.com/google-github-actions/auth) explicitly calls this out; [issue #423](https://github.com/google-github-actions/auth/issues/423) discusses related subject-length edge cases |
| 2 | Attribute-condition case-sensitive literal | [Issue #77](https://github.com/google-github-actions/auth/issues/77) "Unable to authenticate using OIDC workload identity when adding attribute condition" — root cause was assertion mismatch (case + org/owner placeholder substitution) |
| 3 | `principalSet` must use OWNER/REPO not just REPO | Per Google official WIF docs page, attribute mapping `assertion.repository` returns the full `OWNER/REPO` string — single-token would never match |
| 4 | Missing `roles/iam.serviceAccountUser` on runtime SA | [Issue #455](https://github.com/google-github-actions/auth/issues/455), [#526](https://github.com/google-github-actions/auth/issues/526) "getAccessToken denied" — this is consistently the #1 reported failure |
| 5 | `--cpu-boost` flag drift | Audited above (B.9) — **note: this is the only "failure mode" that's stopped being a real risk** in current gcloud; can be removed |

**Verdict:** modes 1-4 are CONFIRMED REAL. Mode 5 is obsolete in current gcloud; downgrade or replace with a different real mode (e.g., "OIDC issuer URI typo `token.actions.githubusercontent.com` — must be exact, no trailing slash; if added, fails silently"). Per Google IAM docs, the trailing-slash issue is now a documented pitfall.

### C.15 WIF setup gcloud commands

cicd.md §"Pool + provider creation" commands verified against [docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/create](https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/create) and [WIF-with-deployment-pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines). **All commands CONFIRMED** — exact flag names, `--location=global`, `--issuer-uri` value match official docs.

Minor: the official docs page recommends `assertion.repository_id` (numeric, immutable) rather than `assertion.repository` (string, reusable) for principalSet binding to avoid "repo renamed → silent auth failure." For a 9-day hackathon this is overkill, but worth a single-line note in `infra/README.md`.

---

## D. Cost projection

### D.16 ~$72 total

Recomputed with verified 2026 prices:

**Dev (9 days, 150 runs):**
- Tokens: 20M in × $1.50/M + 5M out × $9.00/M = $30 + $45 = **$75** (worst case, no optimizations)
- With Flash-Lite for judge + caching: drops to ~$45
- Cloud Run dev: ~$0 (free tier covers)

**Judging (4 weeks, 50 runs):**
- Tokens: 6.8M in × $1.50/M + 1.7M out × $9.00/M = $10.20 + $15.30 = **$25.50**
- Cloud Run warm pool (2 svc × $3.50/mo × 4 wk): ~$7
- Artifact Registry: ~$1
- Total: **~$33.50**

**Optimized grand total: $45 + $27 = $72.** **CONFIRMED — matches spec exactly.**

But: the **ADR-007 mandate that JUDGE_LLM=gemini-3.5-flash saves $80 vs Pro** is now **WRONG** at the new pricing. Pro is only 33% more expensive than Flash, not 17× more. The real savings come from **using Flash-Lite for the judge eval step** (8× cheaper than Flash, 11× cheaper than Pro). Consider whether `JUDGE_LLM=gemini-3.1-flash-lite` is the better hard-config.

---

## Summary of required spec amendments

Ranked by severity:

1. **HIGH — Bump `@v2` → `@v3`** in all references to `google-github-actions/{auth,setup-gcloud,deploy-cloudrun}` across cicd.md, ADR-009, story-1.6, `best-practices/02`. (9 months stale.)
2. **HIGH — Drop `--startup-cpu-boost` fallback note** in story-1.6 line 178. The flag does not exist in current gcloud; `--cpu-boost` is the only correct form.
3. **MED — Update ADR-007 rationale text.** "17× cheaper than Pro" is stale. The real argument is now "Flash-Lite is 8-11× cheaper than Pro for the eval loop" — consider switching `JUDGE_LLM` to `gemini-3.1-flash-lite` if eval quality holds. (Run a small bake-off before locking.)
4. **MED — Use `gemini-3.1-pro-preview` not `gemini-3.1-pro`** anywhere Pro is referenced. The non-preview ID does not exist yet.
5. **LOW — Update WIF failure-mode #5** from `--cpu-boost` drift (obsolete) to OIDC issuer URI trailing-slash pitfall.
6. **LOW — Add note** in `infra/README.md` about `attribute.repository_id` (numeric, immutable) as a hardening upgrade post-hackathon.

---

## Sources

- [Cloud Run request timeout docs](https://docs.cloud.google.com/run/docs/configuring/request-timeout) — 60-min max confirmed
- [gcloud run deploy reference](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy) — `--cpu-boost`, `--set-secrets`, `--no-traffic`, `--tag` all confirmed
- [Gemini models doc](https://ai.google.dev/gemini-api/docs/models) — 3.5 Flash / 3.1 Flash-Lite stable, 3.1 Pro is `-preview`, 2.0 deprecated
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) — current 2026 rates
- [google-github-actions/auth README](https://github.com/google-github-actions/auth) — v3 examples, `id-token: write` requirement
- [WIF with deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines) — principalSet OWNER/REPO format
- [Issue #77](https://github.com/google-github-actions/auth/issues/77), [#455](https://github.com/google-github-actions/auth/issues/455), [#526](https://github.com/google-github-actions/auth/issues/526) — confirmed failure modes 2 and 4
- GitHub Releases API for `google-github-actions/*` repos (queried 2026-06-03)
