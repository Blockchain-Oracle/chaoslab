#!/usr/bin/env python3
"""Offline verification of a Phoenix Audit signed-report sidecar.

Usage:
    python3 scripts/verify_report_signature.py signature.json [artifact-dir]

Verifies every artifact listed in the sidecar against the embedded Ed25519
public key using the documented convention ed25519_sign(sha256(file_bytes)).
Fully offline — no Google dependency; the regulator's trust anchor is the
published PEM, independently retrievable via:
    gcloud kms keys versions get-public-key <v> --key <k> --keyring <r> ...

Requires: pip install cryptography
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

_MIN_ARGC = 2  # script name + sidecar path


def main() -> int:
    if len(sys.argv) < _MIN_ARGC:
        print(__doc__)
        return 2
    sidecar_path = Path(sys.argv[1])
    artifact_dir = Path(sys.argv[2]) if len(sys.argv) > _MIN_ARGC else sidecar_path.parent

    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if sidecar.get("message_convention") != "ed25519_sign(sha256(file_bytes))":
        print(f"FAIL unknown message convention: {sidecar.get('message_convention')!r}")
        return 1
    public_key = load_pem_public_key(sidecar["public_key_pem"].encode("utf-8"))

    failures = 0
    for artifact in sidecar["artifacts"]:
        path = artifact_dir / artifact["file"]
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).digest()
        if digest.hex() != artifact["sha256"]:
            print(f"FAIL {artifact['file']}: sha256 mismatch (file altered)")
            failures += 1
            continue
        try:
            public_key.verify(base64.b64decode(artifact["signature_b64"]), digest)  # type: ignore[union-attr]
        except Exception:
            print(f"FAIL {artifact['file']}: signature INVALID")
            failures += 1
            continue
        print(f"OK   {artifact['file']}  sha256={artifact['sha256'][:16]}…")

    if failures:
        print(f"\n{failures} artifact(s) FAILED verification")
        return 1
    print("\nAll artifacts verified — signature chain intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
