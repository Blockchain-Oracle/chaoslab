# Data retention policy — Phoenix Audit (default mode)

**Status:** SPEC (declared here; runtime enforcement lands in Epic 4 + Epic 6).
**Source:** ADR-017 (`docs/architecture.md`) + audit-notes D4-12 + GDPR research findings (`/tmp/gdpr-retention-research.md`).
**Scope:** Applies to **default mode only** (`phoenix_provider == "phoenix-audit"`). In BYO mode (`phoenix_provider == "customer"`), Customer's own data-retention policy governs; Phoenix Audit holds no copy after the audit run completes (the original ADR-013 contract).

---

## TL;DR

When a Customer uses Phoenix Audit's default zero-friction mode, Phoenix
Audit briefly hosts the Customer's probe-and-response trace data in our
self-hosted Phoenix instance. **We retain that data for 24 hours after
the audit PDF's cryptographic signature is emitted, then cryptographically
erase it via Cloud KMS key-shred.** Phoenix Audit operates as a GDPR
Article 28 data processor for the duration of the retention window.
Right-to-erasure requests are honored at any point during the window.

---

## Why this exists

ADR-017 (Hybrid Phoenix-hosting) introduced a default mode in which
Phoenix Audit hosts Phoenix on behalf of the Customer. That makes
Phoenix Audit a **data processor** under GDPR Article 28 for the
window during which we hold Customer probe-and-response data — even
if that window is short. Article 28 requires a written Data Processing
Agreement (DPA), sub-processor disclosure, and a documented retention
and deletion policy. This file IS that documented policy.

Research basis (`/tmp/gdpr-retention-research.md`):

- Article 28(3) requires a DPA for every controller-processor
  relationship without exception; duration of holding is content of
  the DPA, not a threshold beneath it (cite: legiscope.com/blog/article-28-gdpr.html).
- Industry pattern for transient-hold retention: Langfuse 3-day minimum,
  LangSmith 14-day default, Perplexity Incognito ~24h, Railway 48h
  delayed-delete. Phoenix Audit's 24h is on the short end of industry
  practice — below industry average but above the GDPR breach-notification
  window, with cryptographic erasure as the deletion method.

---

## Retention SLA

- **Retention window:** **24 hours** beginning at the moment the audit
  PDF's cryptographic signature is emitted (Cloud KMS sign operation
  completes). Not a fixed wall-clock from the audit-run-start; the
  signature-emission event is the deletion trigger so that retention
  always covers the post-report window the Customer needs to download +
  verify the signed PDF before evidence is erased.
- **Deletion trigger:** the signature-emission event. Distinct from a
  fixed TTL because audit runs vary in duration; using signature emission
  as the anchor ensures the retention window always begins after the
  Customer has access to the signed report.
- **Deletion method:** **Cloud KMS key-shred** (cryptographic erasure).
  The audit's trace data is encrypted at rest with a per-run Cloud KMS
  data-encryption key (DEK). At T+24h, Phoenix Audit destroys the DEK
  via `gcloud kms keys versions destroy`. The encrypted ciphertext
  becomes unreadable without the destroyed key — cryptographically
  equivalent to deletion, auditable via Cloud KMS audit logs.
- **Backup exclusion:** trace data is explicitly excluded from any
  backup snapshot. Phoenix's Postgres backend (per `infra/phoenix-self-host/compose.yaml`)
  runs with backup disabled for the `spans` and `traces` tables. The
  signed PDF (the durable artifact) IS backed up separately under a
  different KMS key with a 10-year retention to support EU AI Act
  Annex IV's documentation-retention requirement.

---

## GDPR Article 28 obligations Phoenix Audit acknowledges

When operating in default mode, Phoenix Audit acts as a **data processor**
under GDPR Article 28 with the following obligations:

1. **Process Customer trace data only on documented instructions** from
   the Customer (the audit-run request constitutes such instructions).
2. **Confidentiality** — personnel with access to Customer trace data
   are bound by confidentiality obligations.
3. **Security** — appropriate technical and organisational measures
   per Article 32 (encryption at rest via Cloud KMS, encryption in
   transit via TLS, principle of least privilege on the Phoenix host).
4. **Sub-processors disclosed below** — Phoenix Audit will not engage
   new sub-processors without prior written notice to the Customer.
5. **Right-to-erasure pathway** — Customer may invoke right-to-erasure
   at any point during the retention window via the email address listed
   in the audit PDF cover-page footnote. Phoenix Audit honors the request
   within 72 hours (Article 33 timing) and confirms in writing.
6. **Audit and inspection** — Customer may audit Phoenix Audit's
   processing activities upon reasonable notice; Cloud KMS audit logs
   are available for inspection.
7. **Return or deletion at end of services** — at the end of each audit
   run (24h post-signature), all Customer trace data is cryptographically
   erased per the deletion method above.
8. **Breach notification** — Phoenix Audit notifies the Customer of any
   personal-data breach within 24 hours of discovery (faster than
   Article 33's 72-hour controller obligation, giving the Customer
   margin to meet their own).

---

## Sub-processor list (default mode)

Phoenix Audit's default-mode infrastructure uses the following sub-processors:

- **Google Cloud Platform** — Cloud Run (Phoenix Audit orchestrator +
  Phoenix self-hosted Docker), Cloud KMS (signing + DEK management),
  Cloud Storage (signed-PDF archival under different KMS key).
  Region: configurable per Customer; default `us-central1` for the
  hackathon demo, EU regions available for EU Customers.
- **GitHub (Microsoft)** — hardening recipes emitted to GitHub repos
  the Customer designates. Customer's own GitHub credentials are used;
  Phoenix Audit does not act as a sub-processor for the GitHub side.

No other third-party services receive Customer trace data in default mode.

---

## Right-to-erasure pathway

A Customer may invoke their GDPR Article 17 right-to-erasure for any
audit run at any point during the 24h retention window. The mechanism:

1. Email `erasure@phoenix-audit.example` (TODO: actual address lands
   in Epic 6 Reporter story) referencing the `audit_run_id` from the
   signed PDF cover page.
2. Phoenix Audit destroys the audit run's KMS data-encryption key
   within 72 hours and confirms in writing.
3. The signed PDF remains under the Customer's separate KMS retention
   (the Customer downloaded it; Phoenix Audit holds no copy of the
   PDF beyond its own audit-trail backup).

---

## What this PR does NOT do

- It does NOT implement the runtime retention enforcement (Epic 4 +
  Epic 6 own the implementation; this PR is spec-only).
- It does NOT pin the specific Cloud KMS key configuration; Epic 4's
  orchestrator story selects the key hierarchy.
- It does NOT add the `erasure@` mailbox — Epic 6 Reporter story owns
  that infrastructure.
- It does NOT amend BYO mode's contract; BYO mode retention is the
  Customer's policy, not ours.

---

## Cross-references

- ADR-017 in `docs/architecture.md` — the architectural decision this
  policy serves.
- Audit-notes D4-12 — the formal landing record for the hybrid amendment.
- `docs/run-config-schema.md` §"Report template language" — the
  default-mode cover-paragraph variant that cites this policy.
- `/tmp/gdpr-retention-research.md` — the empirical research that
  drove the 24h SLA + key-shred + Article 28 framing.
- `https://gdpr.eu/article-28-processor/` — Article 28 reference.
- `https://artificialintelligenceact.eu/article/11/` — EU AI Act
  Article 11 (technical documentation pack scope; does NOT require
  Customer-side evidence storage, per the ADR-017 honest-rationale
  finding).
