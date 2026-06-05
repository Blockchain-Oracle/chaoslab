# X-Phoenix-Audit-\* header convention — Phoenix Audit

**Status:** SPEC (defined here; runtime wiring lands in Epic 4 injector + opt-in target adapters).
**Source:** ADR-015 (`docs/architecture.md`) + memo 27 sub-question 5 + audit-notes D4-10.

Phoenix Audit emits a fixed set of HTTP headers on every probe request so that
well-behaved targets can opt into dry-run behavior (skip side-effecting tool
calls during the audit window) and Phoenix Audit can detect when a target did
NOT opt in — surfacing that gap as a warning in the audit report.

This is the auditor's-side analog to defender-side policy gates (AIR Blackbox,
Microsoft Agent Governance Toolkit). It does NOT replace those — a regulated
Customer should still operate a defender-side gate of their own.

---

## Why this exists (the OSS-landscape gap)

Memo 27 sub-question 5 surveyed how every OSS red-teaming / auditor tool
handles side effects. None of them solve it from the auditor's side:

| Tool                                            | Side-effect handling                                                                               |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Promptfoo**                                   | Out-of-scope. "Use dedicated test environments... mock providers... application-level safeguards." |
| **Garak**                                       | No dry-run mode. Side effects are caller's problem.                                                |
| **DeepTeam**                                    | Caller's callback bears responsibility.                                                            |
| **Inspect AI**                                  | Sandbox is the answer (Docker / K8s isolation).                                                    |
| **AIR Blackbox**                                | Defender-side gate ("air-gate pauses, checks a policy"); not an auditor-side flag.                 |
| **Microsoft Agent Governance Toolkit (MS AGT)** | Defender-side policy engine (`condition: "action.type in ['drop', 'delete']" → action: deny`).     |

**Promptfoo, Garak, DeepTeam all punt.** AIR Blackbox and MS AGT solve it from
the defender's side, not the auditor's side. Phoenix Audit picks Option B
from the memo: define a header convention; warn loudly when targets don't
opt in. This is documented in ADR-015 + landed by Patch #19.

---

## Header schema

Every probe request Phoenix Audit emits MUST carry these three headers:

### `X-Phoenix-Audit`

- **Value:** `true` (literal). No other value is valid.
- **Purpose:** flag header signaling this request is an audit probe, not
  normal production traffic. Targets MAY use this to route to a dry-run code
  path even before reading the other two headers.

### `X-Phoenix-Audit-Run-Id`

- **Value:** UUIDv4 string. MUST match the run-config's `audit_run_id` field
  (see `docs/run-config-schema.md`). Same UUID across every probe in the
  audit run — targets correlate probes to the run by reading this header.
- **Purpose:** correlation key. Used by the target to associate probes with
  an audit context (logging, dry-run state, post-run cleanup if applicable)
  and by Phoenix Audit's reporter to correlate probe spans to the audit run.

### `X-Phoenix-Audit-Dry-Run`

- **Value:** `true` or `false` (string literal, lowercase). Two-value enum.
- **Purpose:** signals to the target whether side-effecting tools SHOULD be
  short-circuited:
  - `true` — audit mode. Target SHOULD return a synthetic success/failure
    response from side-effecting tools (refund, payment, email, ticket
    creation, database mutation) without actually executing them.
  - `false` — side-effects allowed. Target executes normally. The auditor
    is intentionally probing live behavior; the customer has accepted the
    side-effect risk.

For v1 Phoenix Audit emits `X-Phoenix-Audit-Dry-Run: true` on every probe.
The `false` value is reserved for a future "live audit" mode the customer
can opt into explicitly per audit run.

---

## Acknowledgment protocol (how Phoenix Audit knows the target honored)

A target that opts into the convention MUST emit a span attribute on every
response trace:

- **Attribute name:** `phoenix_audit.honored`
- **Attribute value:** `true` (boolean) — the target read the headers AND
  applied the dry-run short-circuit to its side-effecting tools for this
  probe.

The namespace (`phoenix_audit.` prefix) mirrors ADR-013's filter attribute
convention so the auditor can read both attributes from the same response
span. Phoenix Audit's reporter checks every probe-response span: if any
probe's response does NOT carry `phoenix_audit.honored = true`, the audit
report emits the verbatim warning below.

---

## Audit-report warning (locked verbatim per ADR-015)

When the Reporter (Epic 6) generates the signed PDF, if any probe-response
span lacks `phoenix_audit.honored = true`, the report MUST include this
EXACT paragraph (verbatim — no translation-equivalent rewording, same
lock-discipline as the Patch #20 cover paragraph):

> Target did not signal it honored the X-Phoenix-Audit-\* headers
> (`phoenix_audit.honored = true` was absent from N probe-response spans).
> Side-effecting tool calls during this audit run MAY have been executed
> for real against the target. To opt into dry-run behavior, the target
> must read `X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting
> tools when its value is `true`, AND emit `phoenix_audit.honored = true`
> as a span attribute on every response.

**Canonical fixture** (Epic 6 SHOULD copy this verbatim into a test
constant; this fenced block is the byte-stable lock — the blockquote above
is for human reading, this block is the machine-readable lock):

```text
Target did not signal it honored the X-Phoenix-Audit-* headers (`phoenix_audit.honored = true` was absent from {N} probe-response spans). Side-effecting tool calls during this audit run MAY have been executed for real against the target. To opt into dry-run behavior, the target must read `X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting tools when its value is `true`, AND emit `phoenix_audit.honored = true` as a span attribute on every response.
```

Required placeholder substitution:

- `{N}` — integer count of probe-response spans missing the
  `phoenix_audit.honored = true` attribute.

---

## Threat model + honest disclosure

The header convention is **advisory, not enforced.** Specifically:

1. **A target that ignores the headers still executes side-effecting tools.**
   The headers don't prevent execution; they only request the target opt into
   dry-run. The audit-report warning above is the visible signal when a
   target didn't opt in.
2. **The acknowledgment attribute (`phoenix_audit.honored = true`) is
   self-reported by the target.** A malicious target could emit the attribute
   without actually short-circuiting its side-effecting tools.
3. **Run-Id is not cryptographically bound.** A malicious target could log
   or replay the Run-Id outside the audit window.

For the realistic threat model (the Customer is auditing their own agent;
the agent is cooperative or at worst neutral, not actively adversarial),
self-reporting is sufficient. The Customer's risk is the agent _silently_
executing side-effects during the audit, not the agent _actively lying_
about whether it did so.

**Post-hackathon hardening (TBD-19 in audit-notes):** HMAC-bind the
`X-Phoenix-Audit-Run-Id` header value with a per-run ephemeral key so a
target's claimed honor can be cryptographically verified. This is the
auditor's-side analog to ADR-013's TBD-18 (HMAC on the trace filter
attribute).

---

## Downstream test obligations (for Epic 3 + Epic 4 implementers)

The acceptance test for THIS patch pins the SPEC (file shapes + content).
The runtime tests below land with their respective stories.

**Epic 4 injector story (probe emission) MUST add:**

- Integration test: emit a probe via the injector against the S2.1 demo
  target; assert the three headers are present on the outbound HTTP
  request (`X-Phoenix-Audit: true`, `X-Phoenix-Audit-Run-Id: <uuid>`,
  `X-Phoenix-Audit-Dry-Run: true`).
- Unit test: the injector's header value for `X-Phoenix-Audit-Run-Id`
  MUST equal the orchestrator's `audit_run_id` for the current run.
- Anti-anchor: refuse probe emission if any of the three headers is
  missing or has an unexpected value (rule-of-construction enforcement).

**Epic 3 / target adapter implementers (the well-behaved-target side):**

- Read the three headers from the request scope.
- If `X-Phoenix-Audit-Dry-Run` is `true`, every side-effecting tool
  (refund, payment, ticket creation, database mutation) MUST short-circuit:
  return a synthetic success/failure envelope WITHOUT executing the real
  effect. The synthetic envelope shape SHOULD match the tool's normal
  response shape so the calling agent's downstream logic isn't disturbed.
- Emit `phoenix_audit.honored = true` on the response span for every
  probe the target handled (regardless of which tool was invoked).
- The S2.1 demo target is the reference implementation. It's expected to
  opt into the convention so the demo audit reports "0 unhonored probes"
  cleanly. Wiring it up is its own story (post-Patch-#19).

**Epic 6 Reporter story (PDF generation) MUST add:**

- Snapshot test: render the canonical warning fixture from this doc with
  the `{N}` placeholder substituted; byte-identical match required (same
  lock-discipline as Patch #20's cover-paragraph fixture).
- Integration: count probe-response spans missing
  `phoenix_audit.honored = true`; if N > 0, include the warning paragraph
  in the signed PDF; if N = 0, omit the warning entirely (clean report).
- Anti-anchor: refuse to substitute any placeholder other than `{N}` —
  the warning text is verbatim-locked otherwise.

---

## What this PR does NOT do

- It does NOT wire the headers into any existing target (the S2.1 demo
  target stays unaware of headers until Epic 3 / a dedicated wiring story).
- It does NOT implement the injector that emits the headers (Epic 4).
- It does NOT implement the Reporter that emits the warning (Epic 6).
- It does NOT implement HMAC-bound headers (TBD-19, post-hackathon).

This PR is the **convention declaration** so downstream stories
implement against a fixed contract.

---

## Cross-references

- ADR-015 in `docs/architecture.md` — the architectural decision this convention serves
- Audit-notes D4-10 (added in this PR) — formal spec landing record
- `docs/run-config-schema.md` — `audit_run_id` field that `X-Phoenix-Audit-Run-Id` must match
- ADR-013 (`docs/architecture.md`) — trace-tenancy decision; the
  `phoenix_audit.*` attribute namespace is shared with this convention
- `research/google-cloud-rapid-agent/brainstorm/27-shape-a-architecture-validation.md`
  sub-question 5 — the empirical OSS-landscape survey that drove Option B
