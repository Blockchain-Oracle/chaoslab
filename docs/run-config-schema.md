# Run-config schema — Phoenix Audit

**Status:** SPEC (defined here; runtime parser lands in Epic 4 — the orchestrator story that consumes a run-config).
**Source:** ADR-014 (`docs/architecture.md`) + memo 27 sub-question 9 + audit-notes D4-9.

This document defines the shape of a Phoenix Audit run-config: the JSON
payload the Customer submits when launching an audit (via the web UI's "Run
audit" button or the `chaoslab-agent/run` API endpoint). Schema is locked here
so Epic 3 (target adapters), Epic 4 (orchestrator), and Epic 6 (Reporter)
can implement against the same contract.

---

## Top-level shape

```yaml
audit_run_id: string         # UUIDv4 generated server-side, returned to the Customer.
target: TargetConfig         # The agent being audited.
customer_phoenix: PhoenixConfig  # WHERE the audit traces live (Customer-side per ADR-014).
options: AuditOptions        # Audit-shape knobs (test count, judge model, etc.).
```

---

## `target` — the agent being audited

```yaml
target:
  framework: string          # "adk-a2a" | "langchain-http" | "crewai-http" | "openai-agents" | "http-blackbox"
  url: string                # The agent's reachable endpoint (HTTPS preferred).
  auth: AuthConfig | null    # Bearer token / API key / OAuth — see AuthConfig below.
  environment: string        # "production" | "staging" | "demo" — informational; the Customer asserts this is safe to probe.
```

`framework` selects the adapter from Epic 3's adapter layer. `url` is the
public URL of the target's A2A endpoint (or HTTP endpoint for non-ADK
frameworks). `environment` is **declarative** — Phoenix Audit does not enforce
it; the Customer asserts the URL is safe to probe.

```yaml
auth:
  type: string               # "bearer" | "api_key" | "oauth_client_credentials" | "mtls" | null
  # Plus type-specific fields. See sub-schemas below.
```

Per memo 27 sub-question 4, v1 ships `bearer` + `api_key`; `oauth_client_credentials`
and `mtls` are v2 backlog.

---

## `customer_phoenix` — Customer's Phoenix project (ADR-014)

This is the load-bearing schema for Patch #20. Customer-side trace tenancy
is the locked architectural decision; this is the contract Phoenix Audit
needs to honor it.

```yaml
customer_phoenix:
  endpoint: string           # Phoenix Cloud URL, MUST start with "https://".
                             # Examples:
                             #   "https://app.phoenix.arize.com"                       (default workspace)
                             #   "https://app.phoenix.arize.com/s/<workspace-slug>"   (space-scoped — preferred)
  api_key: string            # One-shot Phoenix API key with access to the project below.
                             # NEVER persisted server-side after the audit run completes.
                             # Customer is responsible for rotating after the audit.
  project_name: string       # The Phoenix project name the audit will write to + read from.
                             # Phoenix Audit tags every emitted span with
                             # `audit_run_id == <the top-level audit_run_id>` so it can
                             # filter the trace slice at report time without mixing
                             # the audit-run spans with the Customer's other workloads.
```

**Validation rules** (orchestrator MUST enforce at run-config parse time):

1. `endpoint` MUST be a parseable URL with a hostname. Schemes other than
   `https` raise `ConfigurationError`. (Same fail-loud pattern as PUBLIC_URL
   in S2.4 per audit-notes D4-9; see `apps/target-agent/src/target_agent/server.py:_build_a2a_app`
   for the canonical implementation to copy.)
2. `api_key` MUST be non-empty.
3. `project_name` MUST match `^[a-z0-9][a-z0-9_-]{0,62}$` (Phoenix project
   naming convention — lowercase alphanumeric + `_`/`-`, max 63 chars).
4. The credentials MUST be discarded from memory after the audit run
   completes (no copy to disk, no copy to Phoenix Audit's own Phoenix
   project, no copy to a log). The Reporter pulls spans, generates the PDF,
   forgets the credentials.

**RAT-2 Test 1 validates this works.** Cross-tenant Phoenix read latency
measured at 1.37s emit-to-visible. See
`research/google-cloud-rapid-agent/RAT-2-results.md` lines 29-49 + the
working smoke script at `rat-2-phoenix-audit/test1_cross_tenant_ingest.py`.

---

## `options` — audit-shape knobs

```yaml
options:
  test_count: integer        # Number of adversarial tests (default 6 per PRD demo).
  judge_model: string        # MUST be "gemini-3.5-flash" per CLAUDE.md hard rule.
  signing_key_ref: string    # Cloud KMS key ref for the signed PDF (Customer-controlled).
                             # Format: "projects/<gcp-project>/locations/<region>/keyRings/<ring>/cryptoKeys/<key>/cryptoKeyVersions/<version>"
  report_destination: string # "pdf" (default) | "json" | "both"
```

---

## Report template language (locked per ADR-014)

When the Reporter (Epic 6) generates the signed PDF, the cover-page MUST
include this exact paragraph (or a translation-equivalent — the legal
substance must be preserved):

> Audit traces remain in the Customer's Phoenix project (project ID:
> `{project_name}` at `{endpoint}`) under the Customer's data-retention
> policy. Phoenix Audit accessed the trace data only during the audit
> run window (start: `{run_started_at}`; end: `{run_completed_at}`) and
> holds no copy after report generation. This signed PDF is the only
> Phoenix Audit-side artifact; all underlying evidence remains in the
> Customer's tenancy.

This text is the compliance hook for the EU AI Act Annex IV chain-of-custody
claim and the "Customer signs with THEIR Cloud KMS key" pitch.

---

## What this PR does NOT do

- It does NOT add a runtime parser (Epic 4's first orchestrator story will).
- It does NOT change any existing Python code paths (S2.1–S2.4 are unchanged).
- It does NOT add the report template (Epic 6 ships the PDF generator).

This PR is the **schema declaration** so downstream stories implement against
a fixed contract, per the "patches before orchestrator stories" recommendation
in `research/.../brainstorm/27-shape-a-architecture-validation.md` synthesis
section.

---

## Cross-references

- ADR-014 in `docs/architecture.md` — the architectural decision this schema serves
- Audit-notes D4-9 (added in this PR) — formal spec landing record
- `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md`
  sub-question 9 — the empirical reasoning that drove Model C
- RAT-2 Test 1 in `research/google-cloud-rapid-agent/RAT-2-results.md` —
  cross-tenant Phoenix read validated at 1.37s
- Phoenix authn limitation: https://github.com/Arize-ai/phoenix/issues/10504
