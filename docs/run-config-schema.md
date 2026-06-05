# Run-config schema — Phoenix Audit

**Status:** SPEC (defined here; runtime parser lands in Epic 4 — the orchestrator story that consumes a run-config).
**Source:** ADR-013 (`docs/architecture.md`) + memo 27 sub-question 9 + audit-notes D4-9.

This document defines the shape of a Phoenix Audit run-config: the JSON
payload the Customer submits when launching an audit (via the web UI's "Run
audit" button or the `chaoslab-agent/run` API endpoint). Schema is locked here
so Epic 3 (target adapters), Epic 4 (orchestrator), and Epic 6 (Reporter)
can implement against the same contract.

---

## Top-level shape

```yaml
audit_run_id: string # UUIDv4 generated server-side, returned to the Customer.
target: TargetConfig # The agent being audited.
customer_phoenix: PhoenixConfig # WHERE the audit traces live (Customer-side per ADR-013).
options: AuditOptions # Audit-shape knobs (test count, judge model, etc.).
```

---

## `target` — the agent being audited

```yaml
target:
  framework: string # "adk-a2a" | "langchain-http" | "crewai-http" | "openai-agents" | "http-blackbox"
  url: string # The agent's reachable endpoint (HTTPS preferred).
  auth: AuthConfig | null # Bearer token / API key / OAuth — see AuthConfig below.
  environment: string # "production" | "staging" | "demo" — informational; the Customer asserts this is safe to probe.
```

`framework` selects the adapter from Epic 3's adapter layer. `url` is the
public URL of the target's A2A endpoint (or HTTP endpoint for non-ADK
frameworks). `environment` is **declarative** — Phoenix Audit does not enforce
it; the Customer asserts the URL is safe to probe.

```yaml
auth:
  type: string # "bearer" | "api_key" | "oauth_client_credentials" | "mtls" | null
  # Plus type-specific fields. See sub-schemas below.
```

Per memo 27 sub-question 4, v1 ships `bearer` + `api_key`; `oauth_client_credentials`
and `mtls` are v2 backlog.

---

## `customer_phoenix` — Customer's Phoenix project (ADR-013)

This is the load-bearing schema for Patch #20. Customer-side trace tenancy
is the locked architectural decision; this is the contract Phoenix Audit
needs to honor it.

```yaml
customer_phoenix:
  endpoint:
    string # Phoenix Cloud URL, MUST start with "https://".
    # Examples:
    #   "https://app.phoenix.arize.com"                       (default workspace)
    #   "https://app.phoenix.arize.com/s/<workspace-slug>"   (space-scoped — preferred)
  api_key:
    string # One-shot Phoenix API key with access to the project below.
    # NEVER persisted server-side after the audit run completes.
    # Customer is responsible for rotating after the audit.
  project_name:
    string # The Phoenix project name the audit will write to + read from.
    # Phoenix Audit tags every emitted span with
    # `audit_run_id == <the top-level audit_run_id>` so it can
    # filter the trace slice at report time without mixing
    # the audit-run spans with the Customer's other workloads.
```

**Validation rules** (orchestrator MUST enforce at run-config parse time):

1. `endpoint` MUST be a parseable URL with a hostname. **Scheme MUST be
   `https` ONLY** — `http` is rejected here (narrower than PUBLIC_URL's
   `http+https` whitelist in `server.py:_build_a2a_app`, because the
   Customer's audit traces are sensitive evidence and must transit TLS).
   Use the same urlparse + frozenset + fail-loud `SystemExit` PATTERN as
   `_build_a2a_app` — but with `frozenset({"https"})` not
   `frozenset({"http", "https"})`. The pattern is portable, the
   whitelist content differs.
2. `api_key` MUST be non-empty (whitespace-only also rejected).
3. `project_name` MUST match `^[a-z0-9][a-z0-9_-]{0,62}$`. **Note:
   Phoenix Cloud does not publicly document its project-name validation
   rules.** This is Phoenix Audit's locally-imposed constraint, modeled
   on Phoenix's documented prompt-tag rule ("lowercase letters, numbers,
   hyphens, underscores; starts/ends with letter or number") + DNS
   conventions (max 63 chars). If a Customer's existing project name
   violates this, they create a new project for the audit run. Empirical
   evidence: `rat-2-phoenix-audit/test1_cross_tenant_ingest.py:50` uses
   `rat2-test1-cross-tenant-{8-hex}` which matches the pattern + worked.
   Post-hackathon TODO: empirically probe Phoenix Cloud's actual rule set.
4. **Credentials MUST be discarded from memory after the audit run completes.**
   This is enforced by THREE concrete obligations Epic 4 must implement:
   - **`pydantic.SecretStr` on `api_key`.** Default `repr()` redacts as
     `SecretStr('**********')` so logger.info(config) cannot leak the key.
   - **Locked unit test pattern:** `assert "api_key=" not in repr(config)`
     AND `assert config.customer_phoenix.api_key.get_secret_value() not in
<any captured log line>`. Both assertions MUST land in Epic 4's
     orchestrator story.
   - **Context-manager scoping:** the run-config object exists inside a
     `with` block that scrubs the api_key on `__exit__` (sets to empty
     SecretStr). After the audit returns, `gc.collect()` + sentinel check
     verifies no surviving reference holds the original secret value.

**RAT-2 Test 1 validates the cross-tenant read works.** Cross-tenant
Phoenix read latency measured at 1.37s emit-to-visible. See
`research/google-cloud-rapid-agent/RAT-2-results.md` lines 29-49 + the
working smoke script at `rat-2-phoenix-audit/test1_cross_tenant_ingest.py`.

**Attribute namespace (fixes silent-data-leak risk):** Phoenix Audit
emits spans with `phoenix_audit.audit_run_id = <uuid>` (namespaced) as
the filter key when pulling the trace slice — NOT bare `audit_run_id`
which a Customer's other workload might also set, causing accidental
spillover. Epic 4 SHOULD ALSO emit `phoenix_audit.run_signature` as an
HMAC of `(audit_run_id, server-side nonce)` so the filter is
cryptographically tight, not just attribute-equal.

---

## `options` — audit-shape knobs

```yaml
options:
  test_count: integer # Number of adversarial tests (default 6 per PRD demo).
  judge_model: string # MUST be "gemini-3.5-flash" per CLAUDE.md hard rule.
  signing_key_ref:
    string # Cloud KMS key ref for the signed PDF (Customer-controlled).
    # Format: "projects/<gcp-project>/locations/<region>/keyRings/<ring>/cryptoKeys/<key>/cryptoKeyVersions/<version>"
  report_destination: string # "pdf" (default) | "json" | "both"
```

---

## Report template language (locked per ADR-013)

When the Reporter (Epic 6) generates the signed PDF, the cover-page MUST
include this EXACT paragraph (verbatim — no "translation-equivalent"
carve-out, because legal substance is too easy to silently water down
under that framing):

> Audit traces remain in the Customer's Phoenix project (project ID:
> `{project_name}` at `{endpoint}`) under the Customer's data-retention
> policy. Phoenix Audit accessed the trace data only during the audit
> run window (start: `{run_started_at}`; end: `{run_completed_at}`) and
> holds no copy after report generation. This signed PDF is the only
> Phoenix Audit-side artifact; all underlying evidence remains in the
> Customer's tenancy.

This text is the compliance hook for the EU AI Act Annex IV chain-of-custody
claim and the "Customer signs with THEIR Cloud KMS key" pitch.

**Verbatim-lock rationale:** earlier draft of this schema allowed
"translation-equivalent" wording with the qualifier "legal substance must
be preserved." Reviewer flagged the loophole: shortening "holds no copy
after report generation" to "does not retain copies of trace data" is
semantically close but legally weaker (permits derived data, summaries,
embeddings). Verbatim is the only durable lock against quiet drift.

Required placeholder substitutions:

- `{project_name}` — from `customer_phoenix.project_name`
- `{endpoint}` — from `customer_phoenix.endpoint`
- `{run_started_at}` — ISO-8601 timestamp, UTC, when orchestrator entered the audit phase
- `{run_completed_at}` — ISO-8601 timestamp, UTC, when Reporter emitted the signed PDF

---

## What this PR does NOT do

- It does NOT add a runtime parser (Epic 4's first orchestrator story will).
- It does NOT change any existing Python code paths (S2.1–S2.4 are unchanged).
- It does NOT add the report template (Epic 6 ships the PDF generator).

This PR is the **schema declaration** so downstream stories implement against
a fixed contract, per the "BEFORE writing more S2.x stories" recommendation
in `research/.../brainstorm/27-shape-a-architecture-validation.md` synthesis
section (which sequences this patch ahead of the S2.x → Epic 4 orchestrator
story chain).

---

## Downstream test obligations (for Epic 4 + Epic 6 implementers)

The acceptance test for THIS patch pins the SPEC (file shapes + content).
The runtime tests below land with their respective stories. Listed here so
the Epic 4 / Epic 6 implementer can't miss them.

**Epic 4 orchestrator story (run-config parser) MUST add:**

- Parametrized rejection tests for validation rule 1 (non-https schemes
  → `ConfigurationError` with bad input echoed). Cover `http://`,
  `ftp://`, `//host`, `not-a-url`, `https:malformed`.
- Rejection test for rule 2 (empty + whitespace-only `api_key`).
- Rejection tests for rule 3 (project names that fail the regex —
  uppercase, dot, leading hyphen, >63 chars).
- Credential-discard tests for rule 4:
  - `assert "api_key=" not in repr(config)` and
    `assert config.customer_phoenix.api_key.get_secret_value() not in repr(config)`.
  - `structlog.testing.capture_logs()` round-trip on a full orchestrator
    run; assert the api_key value never appears in any captured log line.
  - Post-run `gc.collect()` + sentinel check that no surviving Python
    object equals the original api_key string.

**Epic 6 Reporter story (PDF generation) MUST add:**

- Snapshot test of the cover-page paragraph — verbatim match against the
  locked text above, with placeholders correctly interpolated.
- ANTI-anchor assertions: cover page MUST NOT contain `"Phoenix Audit
centralizes"` or `"vendor Phoenix project"` (guards against
  accidentally regressing to Model A wording).
- Asserts `"EU AI Act Annex IV"` and `"chain-of-custody"` appear (the
  regulatory hooks).

---

## Cross-references

- ADR-013 in `docs/architecture.md` — the architectural decision this schema serves
- Audit-notes D4-9 (added in this PR) — formal spec landing record
- `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md`
  sub-question 9 — the empirical reasoning that drove Model C
- RAT-2 Test 1 in `research/google-cloud-rapid-agent/RAT-2-results.md` —
  cross-tenant Phoenix read validated at 1.37s
- Phoenix authn limitation: https://github.com/Arize-ai/phoenix/issues/10504
