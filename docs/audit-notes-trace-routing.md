# Trace-routing investigation (IF-19, opened 2026-06-11)

## Symptom

Staging audits since 2026-06-10 ~20:10 UTC produce probes whose joined trace fetch returns ~5 spans (a2a wire spans only). The fault-execution markers (`phoenix_audit.fault.type`) and ADK-internal spans the judge requires are missing. Result: every probe errors with `LookupError: fault '<class>' was registered but its execution marker never appeared in trace <id> — refusing to score`. The audit completes (signed PDF emitted) with 8 rubric errors and 0 scored verdicts.

Yesterday's seeded runs (Jun 10 ≤19:58 UTC) had 79 spans per trace including the markers.

## What changed in the window

The debugger sub-agent (transcript: `/private/tmp/.../tasks/a48badb0ae7bc0b0e.output`) built two reproductions (httpx ASGITransport + real uvicorn) and confirmed:

- **`SessionAttributesMiddleware` (PR #108, story-9.7) is exonerated.** With vs without it: byte-identical span sets, ADK spans present, markers present. Plus PR #108 merged Jun 11 08:46 +0100 — ~12h AFTER the regression started.
- **What actually landed in the window:**
  - `ec1ad73` (Jun 10 20:10): `PHOENIX_COLLECTOR_ENDPOINT` bare → space-scoped `https://app.phoenix.arize.com/s/blockchainoracle-dev/v1/traces`; `GOOGLE_CLOUD_LOCATION` us-central1 → global.
  - `81c3c17` (Jun 10 20:27): `TARGET_PHOENIX_PROJECT=phoenix-audit` added to the auditor.

## Probe results (Jun 11 19:00 UTC)

Production span-fetch path against today's failing trace `4c155725de429f1f5d85878535005400`:

- `phoenix-audit` project: 5 spans, names all `?`, zero fault attrs.
- `target-agent` project: 0 spans for this trace_id, last span newer than 19:24 Jun 10 absent — the target's exporter STOPPED writing here after the endpoint switch.

Yesterday's scored trace `92aa0568a04eb7083d3b8108900ff754`: 79 spans, `phoenix_audit.fault.type=malformed_tool_output` present, `_fault_fired` returns True.

## Open hypotheses

1. **Target export silently failing.** Target boot logs (Jun 11 18:24:31) show `phoenix_observability_setup` succeeded with `endpoint=...space-scoped... project_name=target-agent` and a `Could not infer collector endpoint protocol, defaulting to HTTP` warning. No export errors logged afterwards. The `target-agent` project has no spans since 19:24 Jun 10 — consistent with silent export failure.
2. **Phoenix routing changed.** Earlier the agent-side comment claimed Phoenix routes joined target spans into the auditor's project; today that routing isn't visible. Whether it ever worked or relied on a setting that drifted is unknown.
3. **OTLP protocol mismatch.** The `defaulting to HTTP` warning may mean the OTLP exporter is configured for HTTP/protobuf against a server expecting HTTP/JSON, dropping spans silently. Pre-Jun-10-20:10 the endpoint was bare; the space-scoped path may differ.

## Recommended next steps

- Inspect target-agent logs at OTLP-export trace level (`OTEL_LOG_LEVEL=debug` on the next deploy).
- Confirm with Arize / Phoenix docs whether `register(...)` requires `protocol="http/protobuf"` set explicitly against space-scoped endpoints.
- If exporter silently dropping: the simplest production fix is to put target-agent on `project_name=phoenix-audit` (single project) so the judge reads from where target writes — but that requires PHOENIX_API_KEY discrimination and removes the per-service project separation.

## Not a C4 blocker

PR #120 ships the officer-review layer and Phoenix deep-links. The deep-links are accurate at signing time regardless of this issue. The machine-side annotation write-back is already disclosed in the report ("PHOENIX ANNOTATION WRITE-BACK FAILED" marker block) — when this issue is also fixed the disclosure naturally goes quiet.
