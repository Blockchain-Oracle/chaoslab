# Example artifacts

Real outputs from a staging audit run (`run_fddd5de82845`, 2026-06-11) against the `target-agent` demo bot. These are what a regulator receives — same files, same Ed25519 signature shape, verifiable offline.

## Files

| File                                  | What it is                                                                                                         |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `sample-signed-report.pdf`            | The signed PDF the operator downloads (also emailed via Resend if enabled).                                        |
| `sample-signed-report.json`           | The structured JSON pack with every verdict, span citation, and root-cause cluster. The PDF is rendered from this. |
| `sample-signed-report.signature.json` | The Cloud-KMS Ed25519 signature sidecar — `{key_version, algorithm, signature, signed_at}`.                        |

## Verify the signature offline

```bash
uv run python scripts/verify_report_signature.py \
  docs/examples/sample-signed-report.pdf \
  docs/examples/sample-signed-report.signature.json
```

The script fetches the public key from Cloud KMS (key version pinned in the signature sidecar), recomputes the SHA-256 over the PDF bytes, and verifies the Ed25519 signature. Exit code `0` = valid attestation; non-zero = tampering.

## What this particular run shows

This audit was the IF-19 verification run (see commit history) — the target's Phoenix span instrumentation was misconfigured at the time, so the judge couldn't read the target's internal evidence and every probe surfaced as **rubric error** rather than pass/fail. The report cover reads honestly: "8 errored, 0 passed clean." Useful as a sample of the failure-disclosure shape — Phoenix Audit never hides an unverifiable verdict behind a clean stamp.

For a clean-pass example, see [phxaudit.xyz/replay](https://phxaudit.xyz/replay).
