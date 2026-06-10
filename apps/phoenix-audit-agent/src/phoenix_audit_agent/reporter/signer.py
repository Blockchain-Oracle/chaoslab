"""Cloud KMS Ed25519 detached signing (ADR-014).

KMS Ed25519 is PureEdDSA: it signs RAW bytes via the `data` field (the
`digest` field is for ECDSA algorithms and is mutually exclusive). Because
KMS payload limits are KiB-scale and a font-embedded PDF is not, we sign
sha256(file_bytes) as the 32-byte Ed25519 message — the documented
convention in the sidecar: ed25519_sign(sha256(file_bytes)).

Verification is fully offline / Google-independent:
    python scripts/verify_report_signature.py signature.json
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any, Protocol, runtime_checkable

import structlog

from phoenix_audit_agent._time import utc_now_iso

_log = structlog.get_logger(__name__)

ALGORITHM = "EC_SIGN_ED25519"
MESSAGE_CONVENTION = "ed25519_sign(sha256(file_bytes))"


@runtime_checkable
class KmsClient(Protocol):
    """Narrow protocol of google.cloud.kms.KeyManagementServiceClient we use."""

    def asymmetric_sign(self, request: dict[str, Any]) -> Any: ...

    def get_public_key(self, request: dict[str, Any]) -> Any: ...


def make_kms_client() -> KmsClient:
    from google.cloud import kms  # deferred: heavy native import

    return kms.KeyManagementServiceClient()


def _crc32c(data: bytes) -> int:
    import google_crc32c

    return google_crc32c.value(data)


class KmsReportSigner:
    """Signs artifact bytes and assembles the detached-signature sidecar."""

    def __init__(self, key_version: str, client: KmsClient | None = None) -> None:
        if not key_version.strip():
            msg = "KMS signing key version is empty — refusing to emit unsigned artifacts"
            raise ValueError(msg)
        self._key_version = key_version
        self._client = client if client is not None else make_kms_client()

    def _sign_one(self, payload: bytes) -> bytes:
        message = hashlib.sha256(payload).digest()
        response = self._client.asymmetric_sign(
            request={
                "name": self._key_version,
                "data": message,  # Ed25519 => raw data, NEVER digest
                "data_crc32c": _crc32c(message),
            }
        )
        if not getattr(response, "verified_data_crc32c", False):
            # Integrity of the request was not confirmed server-side — a
            # signature emitted anyway could cover corrupted input.
            msg = "Cloud KMS did not verify the request CRC32C — refusing the signature"
            raise RuntimeError(msg)
        # Response integrity (KMS guidance): the signature must come back
        # uncorrupted and from THE key we asked for — a wrong-key signature
        # would only fail at the regulator's desk. ABSENT integrity fields
        # also refuse: "could not verify" must never pass as "verified".
        response_name = getattr(response, "name", None)
        if not response_name:
            msg = "Cloud KMS response carried no key name — cannot confirm signing key; refusing"
            raise RuntimeError(msg)
        if response_name != self._key_version:
            msg = (
                f"Cloud KMS signed with unexpected key {response_name!r} "
                f"(requested {self._key_version!r}) — refusing the signature"
            )
            raise RuntimeError(msg)
        signature = bytes(response.signature)
        response_crc = getattr(response, "signature_crc32c", None)
        if response_crc is None:
            msg = (
                "Cloud KMS response carried no signature_crc32c — cannot confirm "
                "signature integrity in transit; refusing"
            )
            raise RuntimeError(msg)
        if _crc32c(signature) != int(response_crc):
            msg = "Cloud KMS signature failed CRC32C verification in transit — refusing"
            raise RuntimeError(msg)
        return signature

    def public_key_pem(self) -> str:
        response = self._client.get_public_key(request={"name": self._key_version})
        return str(response.pem)

    def sign_artifacts(self, artifacts: dict[str, bytes]) -> dict[str, Any]:
        """Sign every artifact; return the sidecar dict (JSON-serializable)."""
        pem = self.public_key_pem()
        fingerprint = hashlib.sha256(pem.encode("utf-8")).hexdigest()
        entries = []
        for name, payload in artifacts.items():
            signature = self._sign_one(payload)
            entries.append(
                {
                    "file": name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "signature_b64": base64.b64encode(signature).decode("ascii"),
                }
            )
            _log.info("artifact_signed", file=name, key_version=self._key_version)
        return {
            "version": 1,
            "algorithm": ALGORITHM,
            "message_convention": MESSAGE_CONVENTION,
            "kms_key_version": self._key_version,
            "public_key_pem": pem,
            "public_key_fingerprint_sha256": fingerprint,
            "artifacts": entries,
            "signed_at": utc_now_iso(),
        }
