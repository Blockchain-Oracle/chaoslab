"""Sign → verify round-trip + signer integrity refusals + report disclosures.

The regulator's only trust path is scripts/verify_report_signature.py run
against the sidecar. These tests wire a REAL Ed25519 key as the fake KMS so
the signer's convention (ed25519_sign(sha256(file_bytes))) and the verifier's
check are proven against each other — not just against copied strings.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from phoenix_audit_agent.reporter import (
    ReportData,
    ReportProbe,
    build_report_html,
    render_pdf,
)
from phoenix_audit_agent.reporter.signer import KmsReportSigner

_KEY_VERSION = "projects/p/locations/l/keyRings/r/cryptoKeys/k/cryptoKeyVersions/1"
_REPO_ROOT = Path(__file__).resolve().parents[5]
_VERIFY_SCRIPT = _REPO_ROOT / "scripts" / "verify_report_signature.py"


def _crc(data: bytes) -> int:
    import google_crc32c

    return google_crc32c.value(data)


class _RealEd25519Kms:
    """Fake KMS backed by a real in-memory Ed25519 key (PureEdDSA, like KMS)."""

    def __init__(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        self._private = Ed25519PrivateKey.generate()
        self._pem = (
            self._private.public_key()
            .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
            .decode("ascii")
        )

    def asymmetric_sign(self, request: dict[str, Any]) -> Any:
        signature = self._private.sign(request["data"])
        return SimpleNamespace(
            signature=signature,
            verified_data_crc32c=True,
            name=request["name"],
            signature_crc32c=_crc(signature),
        )

    def get_public_key(self, request: dict[str, Any]) -> Any:
        return SimpleNamespace(pem=self._pem)


def _verify_main() -> Any:
    spec = importlib.util.spec_from_file_location("verify_report_signature", _VERIFY_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def _data() -> ReportData:
    return ReportData(
        run_id="run_9f3c2ab81d4e",
        target_url="https://target.example/agent",
        framework_label="EU AI Act · high-risk system",
        created_at="2026-06-10T00:00:00Z",
        probes=[
            ReportProbe(
                n=1, fault_class="prompt_injection", verdict="pass", span_id="a" * 16, score=1.0
            ),
        ],
        passed=1,
        failed=0,
        errored=0,
        transport_failed=0,
        cluster_ids=[],
        root_causes=[],
        excluded_transport_failures=0,
        annotation_writeback_failed=False,
        clustering_skipped=None,
        recipe_id=None,
        markdown_url=None,
        honored_missing_count=1,
    )


def _sign_to_dir(tmp_path: Path) -> Path:
    """Sign a real rendered PDF + JSON into tmp_path; return the sidecar path."""
    pdf_bytes = render_pdf(build_report_html(_data()))
    json_bytes = json.dumps(_data().model_dump(), indent=2, sort_keys=True).encode()
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_RealEd25519Kms())
    sidecar = signer.sign_artifacts({"report.pdf": pdf_bytes, "report.json": json_bytes})
    (tmp_path / "report.pdf").write_bytes(pdf_bytes)
    (tmp_path / "report.json").write_bytes(json_bytes)
    sidecar_path = tmp_path / "signature.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True))
    return sidecar_path


def test_roundtrip_verifies_clean_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sidecar_path = _sign_to_dir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify", str(sidecar_path)])
    assert _verify_main()() == 0


def test_roundtrip_fails_on_tampered_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar_path = _sign_to_dir(tmp_path)
    pdf = tmp_path / "report.pdf"
    raw = bytearray(pdf.read_bytes())
    raw[len(raw) // 2] ^= 0xFF  # flip one byte mid-document
    pdf.write_bytes(bytes(raw))
    monkeypatch.setattr(sys, "argv", ["verify", str(sidecar_path)])
    assert _verify_main()() == 1


def test_roundtrip_fails_on_swapped_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signature from a DIFFERENT key must not verify — guards convention drift
    (e.g. signer signing sha256 while verifier checks raw bytes would also die here)."""
    sidecar_path = _sign_to_dir(tmp_path)
    sidecar = json.loads(sidecar_path.read_text())
    other = _RealEd25519Kms()
    sig = other.asymmetric_sign(
        {"name": _KEY_VERSION, "data": b"\x00" * 32, "data_crc32c": 0}
    ).signature
    import base64

    sidecar["artifacts"][0]["signature_b64"] = base64.b64encode(sig).decode()
    sidecar_path.write_text(json.dumps(sidecar))
    monkeypatch.setattr(sys, "argv", ["verify", str(sidecar_path)])
    assert _verify_main()() == 1


# ---------------------------------------------------------------------------
# Signer refusals on ABSENT integrity fields ("could not verify" != "verified")


class _NoNameKms(_RealEd25519Kms):
    def asymmetric_sign(self, request: dict[str, Any]) -> Any:
        response = super().asymmetric_sign(request)
        response.name = None
        return response


class _NoCrcKms(_RealEd25519Kms):
    def asymmetric_sign(self, request: dict[str, Any]) -> Any:
        response = super().asymmetric_sign(request)
        response.signature_crc32c = None
        return response


def test_signer_refuses_response_without_key_name() -> None:
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_NoNameKms())
    with pytest.raises(RuntimeError, match="no key name"):
        signer.sign_artifacts({"report.pdf": b"%PDF"})


def test_signer_refuses_response_without_signature_crc() -> None:
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_NoCrcKms())
    with pytest.raises(RuntimeError, match="no signature_crc32c"):
        signer.sign_artifacts({"report.pdf": b"%PDF"})


# ---------------------------------------------------------------------------
# Unreadable-span disclosure + PDF text survival


def test_unreadable_spans_disclosed_outside_locked_warning() -> None:
    data = _data().model_copy(update={"honored_unreadable_count": 2})
    html = build_report_html(data)
    assert "HEADER VERIFICATION INCOMPLETE" in html
    assert "2 probe-response span(s) could not be" in html


def test_no_unreadable_disclosure_when_all_spans_read() -> None:
    html = build_report_html(_data())
    assert "HEADER VERIFICATION INCOMPLETE" not in html


def test_pdf_text_carries_locked_paragraph_and_run_id() -> None:
    """A WeasyPrint/font regression that garbles text would still produce
    valid-looking PDF bytes — assert the words actually survive rendering."""
    from pypdf import PdfReader

    pdf_bytes = render_pdf(build_report_html(_data()))
    import io

    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    normalized = " ".join(text.split())
    assert "run_9f3c2ab81d4e" in normalized
    assert "cryptographically erased via Cloud KMS key-shred" in normalized
    assert "GDPR Article 28 data" in normalized
