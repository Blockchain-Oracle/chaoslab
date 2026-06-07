# Run-config schema — Phoenix Audit

**Status:** SPEC (defined here; runtime parser lands in Epic 4 — the orchestrator story that consumes a run-config).
**Source:** ADR-013 (`docs/architecture.md`) + memo 27 sub-question 9 + audit-notes D4-9.

This document defines the shape of a Phoenix Audit run-config: the JSON
payload the Customer submits when launching an audit (via the web UI's "Run
audit" button or the audit-agent `/run` API endpoint). Schema is locked here
so Epic 3 (target adapters), Epic 4 (orchestrator), and Epic 6 (Reporter)
can implement against the same contract.

Wire format: JSON. Below, fields are rendered as YAML inline-comment blocks
for readability; the live API payload is JSON.

---

## Top-level shape

```yaml
audit_run_id: string # UUIDv4 generated server-side, returned to the Customer.
target: TargetConfig # The agent being audited.
phoenix_provider: "phoenix-audit" | "customer" # Hosting mode per ADR-017. Default: "phoenix-audit".
customer_phoenix: PhoenixConfig | null # OPTIONAL — required only when phoenix_provider == "customer".
options: AuditOptions # Audit-shape knobs (test count, judge model, etc.).
```

**Note on `phoenix_provider` (ADR-017 hybrid amendment).** This field selects between the two hosting modes:

- `"phoenix-audit"` (DEFAULT) — Phoenix Audit hosts the Phoenix instance. Customer pastes their agent URL + audit options and the run completes without any Phoenix credentials. Trace data follows the 24h retention policy in `docs/data-retention-policy.md`. This is the zero-friction path for the 95% case.
- `"customer"` — Customer provides their own Phoenix endpoint + API key. The `customer_phoenix` block becomes REQUIRED in this mode. Recommended for regulated industries (banking, healthcare, EU AI Act-bound) that prefer full data sovereignty.

The `customer_phoenix` block is **OPTIONAL** when `phoenix_provider == "phoenix-audit"`. Orchestrator rejects the run-config with `ConfigurationError` if `phoenix_provider == "customer"` and `customer_phoenix` is absent or incomplete.

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

## `customer_phoenix` — Customer's Phoenix project (ADR-013 + ADR-017 BYO mode)

This block is the BYO-key contract. **OPTIONAL** when `phoenix_provider == "phoenix-audit"` (default mode). **REQUIRED** when `phoenix_provider == "customer"`. The validation rules below apply only in BYO mode.

```yaml
customer_phoenix:
  endpoint: string # Phoenix Cloud URL, MUST start with "https://".
  api_key: string # One-shot Phoenix API key with access to the project below.
  project_name: string # The Phoenix project name the audit will write to + read from.
```

Field detail:

- **`endpoint`** — Phoenix Cloud URL. MUST start with `https://`.
  Examples:
  - `https://app.phoenix.arize.com` (default workspace)
  - `https://app.phoenix.arize.com/s/<workspace-slug>` (space-scoped — preferred)
- **`api_key`** — One-shot Phoenix API key with access to the project below.
  NEVER persisted server-side after the audit run completes. The Customer
  is responsible for rotating after the audit.
- **`project_name`** — The Phoenix project name the audit will write to + read
  from. Phoenix Audit tags every emitted span with the namespaced attribute
  `phoenix_audit.audit_run_id == <the top-level audit_run_id>` so it can
  filter the trace slice at report time without mixing the audit-run spans
  with the Customer's other workloads. (See "Attribute namespace" below for
  why bare `audit_run_id` is unsafe.)

**Validation rules** (orchestrator MUST enforce at run-config parse time):

1.  `endpoint` MUST be a parseable URL with a hostname. **Scheme MUST be
    `https` ONLY** — `http` is rejected here (narrower than PUBLIC_URL's
    `http+https` whitelist in `server.py:_build_a2a_app`, because the
    Customer's audit traces are sensitive evidence and must transit TLS).
    Use the same urlparse + frozenset + fail-loud `SystemExit` PATTERN as
    `_build_a2a_app` — but with `frozenset({"https"})` not
    `frozenset({"http", "https"})`. The pattern is portable, the
    whitelist content differs.
2.  `api_key` MUST be non-empty (whitespace-only also rejected).
3.  `project_name` MUST match `^[a-z0-9][a-z0-9_-]{0,62}$`. **Note:
    Phoenix Cloud does not publicly document its project-name validation
    rules.** This is Phoenix Audit's locally-imposed constraint, modeled
    on common identifier-validation conventions (lowercase alphanumeric +
    hyphens + underscores; starts/ends with letter or number; DNS-style
    63-char max). If a Customer's existing project name violates this,
    they create a new project for the audit run. Empirical existence
    proof (NOT a derivation of Phoenix's actual rule set): one name
    shaped like `rat2-test1-cross-tenant-{8-hex}` was accepted by
    Phoenix Cloud in `rat-2-phoenix-audit/test1_cross_tenant_ingest.py:50`.
    This is consistent with (not proof of) the regex above; Phoenix may
    accept names the regex rejects. Post-hackathon TODO: empirically
    probe Phoenix Cloud's actual rule set.
4.  **Credentials MUST be discarded from memory after the audit run completes.**
    This is enforced by three concrete obligations Epic 4 must implement (rendered
    as paragraphs below rather than nested bullets to keep the markdown
    reformatter-stable).

**Rule 4a — `pydantic.SecretStr` on `api_key`.** Default `repr()` redacts as
`SecretStr('**********')` so `logger.info(config)` cannot leak the key.

**Rule 4b — Locked unit test pattern.** `assert "api_key=" not in repr(config)`
AND, using `structlog.testing.capture_logs()` over an orchestrator round-trip,
`assert config.customer_phoenix.api_key.get_secret_value() not in <any captured
log line>`. Both assertions MUST land in Epic 4's orchestrator story.

**Rule 4c — Context-manager scoping via an `audit_run_context()` helper** (NOT
the run-config object itself — `pydantic.BaseModel` does not implement
`__enter__`/`__exit__`). Epic 4 ships a separate helper:
`with audit_run_context(run_config) as ctx:` whose `__exit__` overwrites
`ctx.run_config.customer_phoenix.api_key` with `SecretStr("")` via
`object.__setattr__(...)`. With Pydantic v2's default config (`frozen=False` +
`validate_assignment=False`), regular `model.field = x` works without going
through validators — `object.__setattr__` isn't strictly required today. We
use it anyway as a forward-compatible scrub that survives future config
tightening (any future change to `frozen=True` or `validate_assignment=True`
would otherwise silently break the scrub path).

**Sentinel check (full spec, not a placeholder):** before entering the context,
capture the raw secret string:
`original_key = run_config.customer_phoenix.api_key.get_secret_value()`.
After `__exit__` returns + an explicit `gc.collect()`, scan module-scope
containers for survivors: assert that no `dict`/`list`/`tuple` reachable from
the current module's globals (via `vars(sys.modules[__name__]).values()`)
holds an item equal to `original_key`. **Honest caveat:** this module-globals
walk only catches leaks via top-level containers (misses values held in
instance attributes, closures, nested containers, frame locals). It is
defense-in-depth on top of `SecretStr.__repr__` redaction + log capture +
`__exit__` overwrite, not the actual security boundary. Python strings are
immutable; "scrub" means "drop all references and `gc.collect()`."
Bytes-level zeroization of the underlying string is not Python-guaranteed
without `ctypes` memmove — out of scope for v1.

**RAT-2 Test 1 validates the cross-tenant read works.** Cross-tenant
Phoenix read latency measured at 1.37s emit-to-visible. See
`research/google-cloud-rapid-agent/RAT-2-results.md` lines 29-49 + the
working smoke script at `rat-2-phoenix-audit/test1_cross_tenant_ingest.py`.

**Attribute namespace (fixes silent-data-leak risk):** Phoenix Audit
emits spans with `phoenix_audit.audit_run_id = <uuid>` (namespaced) as
the filter key when pulling the trace slice — NOT bare `audit_run_id`,
which a Customer's other observability workload might also set, causing
accidental cross-workload bleed into the audit slice. For the realistic
threat model (Customer is the protected party, not an adversary),
namespace alone closes the accidental-collision risk. **HMAC binding
deferred to TBD-18** (`docs/audit-notes.md` open-items table):
`phoenix_audit.run_signature` = HMAC(audit_run_id, per-run ephemeral
key) makes the filter cryptographically tight against malicious
cross-tenant injection. Tracked separately because (a) the realistic
threat model doesn't require it for v1 Customer-protected use, and
(b) HMAC key generation/storage/recovery is a non-trivial design
(per-run ephemeral; minted server-side at orchestrator start; stored
in `audit_run_context`; scrubbed alongside `api_key` on `__exit__`).

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

## Report template language (locked per ADR-013 + ADR-017)

The audit PDF's cover-page paragraph is **mode-conditional**. The Reporter
(Epic 6) selects between two variants based on `phoenix_provider`:

### Default-mode variant (`phoenix_provider == "phoenix-audit"`)

When Phoenix Audit hosts Phoenix on the Customer's behalf, the cover-page
MUST include this EXACT paragraph (verbatim — no rewording for length,
style, or tone; same lock-discipline as the BYO variant below):

> Audit traces are retained in Phoenix Audit's hosted Phoenix project
> for 24 hours after this report's cryptographic signature is emitted,
> then cryptographically erased via Cloud KMS key-shred. Phoenix Audit
> acts as a GDPR Article 28 data processor for the duration of the
> retention window. This signed PDF is the durable artifact; all
> underlying probe-and-response data is destroyed after the retention
> window closes.

**Canonical fixture (default mode)** — Epic 6 SHOULD copy verbatim into
the snapshot-test constant; this fenced block is the machine-readable lock:

<!-- prettier-ignore -->
```text
Audit traces are retained in Phoenix Audit's hosted Phoenix project for 24 hours after this report's cryptographic signature is emitted, then cryptographically erased via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data processor for the duration of the retention window. This signed PDF is the durable artifact; all underlying probe-and-response data is destroyed after the retention window closes.
```

The retention SLA + key-shred + GDPR Article 28 framing are load-bearing
compliance hooks; see `docs/data-retention-policy.md` for the full policy.

### BYO-mode variant (`phoenix_provider == "customer"`)

When the Customer hosts their own Phoenix (regulated-industry default),
the cover-page MUST include this EXACT paragraph (verbatim — no rewording):

> Audit traces remain in the Customer's Phoenix project (project ID:
> `{project_name}` at `{endpoint}`) under the Customer's data-retention
> policy. Phoenix Audit accessed the trace data only during the audit
> run window (start: `{run_started_at}`; end: `{run_completed_at}`) and
> holds no copy after report generation. This signed PDF is the only
> Phoenix Audit-side artifact; all underlying evidence remains in the
> Customer's tenancy.

This text is the compliance hook for the EU AI Act Annex IV chain-of-custody
claim and the "Customer signs with THEIR Cloud KMS key" pitch.

**Canonical fixture (BYO mode)** — Epic 6 SHOULD copy verbatim into
the snapshot-test constant:

<!-- prettier-ignore -->
```text
Audit traces remain in the Customer's Phoenix project (project ID: {project_name} at {endpoint}) under the Customer's data-retention policy. Phoenix Audit accessed the trace data only during the audit run window (start: {run_started_at}; end: {run_completed_at}) and holds no copy after report generation. This signed PDF is the only Phoenix Audit-side artifact; all underlying evidence remains in the Customer's tenancy.
```

**Verbatim-lock rationale:** earlier draft of this schema allowed
"translation-equivalent" wording with the qualifier "legal substance must
be preserved." Reviewer flagged the loophole: shortening the cover-page
sentence about post-report retention is semantically close to the original
but legally weaker (permits derived data, summaries, vector embeddings).
Verbatim is the only durable lock against quiet drift. The acceptance
test (`tests/acceptance/test_patch_20_trace_tenancy.sh`) anti-anchors the
specific weakening phrases the reviewer flagged; see the test for the
authoritative list (kept there to avoid this prose silently drifting
out of sync with the gate).

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
- It does NOT implement the `phoenix_audit.run_signature` HMAC mitigation
  declared as deferred above — TBD-18 in audit-notes tracks that delivery.

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
  `ftp://`, `//host`, `not-a-url`, `https:malformed`,
  `HTTPS://example.com` (uppercase scheme — verify normalization choice
  matches `_build_a2a_app`'s behavior; either accept after lowercase
  or reject), `  https://example.com` (leading whitespace),
  `https://example.com  ` (trailing whitespace), and one IDNA
  homoglyph case (`https://exаmple.com` — Cyrillic 'а' U+0430).
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

- Snapshot test of the cover-page paragraph — **byte-identical** match
  against the canonical fixture above (no `.strip()`, no whitespace
  normalization, no rewrap), with placeholders correctly interpolated.
  The four placeholders (`{project_name}`, `{endpoint}`, `{run_started_at}`,
  `{run_completed_at}`) are the ONLY substitutions permitted.
- ANTI-anchor assertions: cover page MUST NOT contain any Model-A
  regression markers (affirmative "centralizes/will centralize/may
  centralize/should centralize" wording, or "vendor Phoenix project").
  Authoritative list lives in
  `tests/acceptance/test_patch_20_trace_tenancy.sh` — keep both in sync.
- ANTI-anchor assertions for legal-weakening phrases the verbatim-lock
  rationale guards against. Authoritative list lives in the same
  acceptance test (kept there rather than inline so this spec doc and
  the gate can't silently drift apart).
- Asserts `EU AI Act Annex IV` and `chain-of-custody` appear (the
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
