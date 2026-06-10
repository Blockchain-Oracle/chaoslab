"""Reporter — signed PDF + sidecar generation (story-6.7).

Spec obligations pinned here (the downstream-test contracts declared in
docs/run-config-schema.md, docs/header-convention.md, docs/session-shape.md):

- The default-mode data-residency cover paragraph renders BYTE-IDENTICAL to
  the canonical fixture (only declared placeholders substitute).
- The header-convention warning renders byte-identical with {N} substituted,
  and ONLY when honored_missing_count > 0.
- Anti-anchors: no Model-A regression markers, no legal-weakening phrases.
- "EU AI Act Annex IV" and "chain-of-custody" appear (regulatory hooks).
- The PDF renderer produces real PDF bytes.
- The KMS signer signs sha256(file) as the Ed25519 message (raw `data`
  field, never `digest`), verifies the response CRC, and emits a sidecar
  with the documented convention string.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

import pytest

from chaoslab_agent.reporter import (
    DEFAULT_RESIDENCY_PARAGRAPH,
    HEADER_WARNING_TEMPLATE,
    ReportData,
    ReportProbe,
    build_report_html,
    render_pdf,
)
from chaoslab_agent.reporter.signer import KmsReportSigner

# ---------------------------------------------------------------------------
# Canonical fixtures — copied VERBATIM from the locked spec blocks.
# docs/run-config-schema.md §"Canonical fixture (default mode)"
_CANONICAL_RESIDENCY = (
    "Audit traces are retained in Phoenix Audit's hosted Phoenix project for 24 hours "
    "after this report's cryptographic signature is emitted, then cryptographically "
    "erased via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data "
    "processor for the duration of the retention window. This signed PDF is the durable "
    "artifact; all underlying probe-and-response data is destroyed after the retention "
    "window closes."
)
# docs/header-convention.md §"Canonical fixture"
_CANONICAL_WARNING = (
    "Target did not signal it honored the X-Phoenix-Audit-* headers "
    "(`phoenix_audit.honored = true` was absent from {N} probe-response spans). "
    "Side-effecting tool calls during this audit run MAY have been executed for real "
    "against the target. To opt into dry-run behavior, the target must read "
    "`X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting tools when its value "
    "is `true`, AND emit `phoenix_audit.honored = true` as a span attribute on every "
    "response."
)

_ANTI_ANCHORS = (
    "centralizes",
    "will centralize",
    "may centralize",
    "should centralize",
    "vendor Phoenix project",
)


def _data(honored_missing: int = 8) -> ReportData:
    return ReportData(
        run_id="run_9f3c2ab81d4e",
        target_url="https://target.example/agent",
        framework_label="EU AI Act · high-risk system",
        created_at="2026-06-10T00:00:00Z",
        probes=[
            ReportProbe(
                n=1,
                fault_class="prompt_injection",
                verdict="pass",
                span_id="a" * 16,
                score=1.0,
            ),
            ReportProbe(
                n=2,
                fault_class="malformed_tool_output",
                verdict="fail",
                span_id="b" * 16,
                score=0.0,
            ),
            ReportProbe(
                n=3,
                fault_class="latency_spike",
                verdict="error",
                span_id="c" * 16,
                score=0.0,
                rubric_error=True,
            ),
        ],
        passed=1,
        failed=1,
        errored=1,
        transport_failed=0,
        cluster_ids=["cluster_a3f81c2e"],
        root_causes=["submit on unvalidated input"],
        excluded_transport_failures=0,
        annotation_writeback_failed=False,
        clustering_skipped=None,
        recipe_id="recipe_7c0d51e2a9b4",
        markdown_url="https://gcs.example/recipe_7c0d51e2a9b4.md",
        honored_missing_count=honored_missing,
    )


# ---------------------------------------------------------------------------
# Locked-text obligations


def test_canonical_fixtures_match_module_constants() -> None:
    assert DEFAULT_RESIDENCY_PARAGRAPH == _CANONICAL_RESIDENCY
    assert HEADER_WARNING_TEMPLATE == _CANONICAL_WARNING


def test_html_contains_residency_paragraph_byte_identical() -> None:
    html = build_report_html(_data())
    assert _CANONICAL_RESIDENCY in html


def test_html_contains_header_warning_with_n_substituted() -> None:
    html = build_report_html(_data(honored_missing=8))
    assert _CANONICAL_WARNING.replace("{N}", "8") in html
    assert "{N}" not in html


def test_header_warning_omitted_when_all_probes_honored() -> None:
    html = build_report_html(_data(honored_missing=0))
    assert "Target did not signal it honored" not in html


def test_html_carries_regulatory_hooks_and_no_anti_anchors() -> None:
    html = build_report_html(_data())
    assert "EU AI Act Annex IV" in html
    assert "chain-of-custody" in html
    for phrase in _ANTI_ANCHORS:
        assert phrase not in html, f"anti-anchor present: {phrase!r}"


def test_html_session_shape_disclosure_present() -> None:
    # docs/session-shape.md: the report must not claim comprehensive coverage.
    html = build_report_html(_data())
    assert "budget-vs-coverage" in html


def test_html_marks_rubric_errors_distinctly() -> None:
    html = build_report_html(_data())
    assert "RUBRIC ERROR" in html  # marked non-verdict, pattern #4


# ---------------------------------------------------------------------------
# PDF renderer


def test_render_pdf_produces_real_pdf_bytes() -> None:
    pdf = render_pdf(build_report_html(_data()))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 10_000  # styled multi-section document, not a stub


# ---------------------------------------------------------------------------
# KMS signer


_KEY_VERSION = "projects/p/locations/l/keyRings/r/cryptoKeys/k/cryptoKeyVersions/1"
_FAKE_SIGNATURE = b"\x01" * 64


def _sig_crc(payload: bytes) -> int:
    import google_crc32c

    return google_crc32c.value(payload)


class _FakeSignResponse:
    def __init__(
        self,
        signature: bytes,
        ok_crc: bool,
        name: str = _KEY_VERSION,
        signature_crc32c: int | None = None,
    ) -> None:
        self.signature = signature
        self.verified_data_crc32c = ok_crc
        self.name = name
        self.signature_crc32c = (
            signature_crc32c if signature_crc32c is not None else _sig_crc(signature)
        )


class _FakePublicKey:
    pem = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAfake\n-----END PUBLIC KEY-----\n"


class _FakeKms:
    def __init__(
        self,
        ok_crc: bool = True,
        name: str = _KEY_VERSION,
        signature_crc32c: int | None = None,
    ) -> None:
        self.ok_crc = ok_crc
        self.name = name
        self.signature_crc32c = signature_crc32c
        self.sign_requests: list[dict[str, Any]] = []

    def asymmetric_sign(self, request: dict[str, Any]) -> _FakeSignResponse:
        self.sign_requests.append(request)
        return _FakeSignResponse(
            signature=_FAKE_SIGNATURE,
            ok_crc=self.ok_crc,
            name=self.name,
            signature_crc32c=self.signature_crc32c,
        )

    def get_public_key(self, request: dict[str, Any]) -> _FakePublicKey:
        return _FakePublicKey()


def test_signer_signs_sha256_as_raw_data_never_digest() -> None:
    kms = _FakeKms()
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=kms)
    pdf = b"%PDF-fake-bytes"
    sidecar = signer.sign_artifacts({"report.pdf": pdf})

    (req,) = kms.sign_requests
    assert req["data"] == hashlib.sha256(pdf).digest()
    assert "digest" not in req  # Ed25519 is PureEdDSA — data, never digest
    assert req["data_crc32c"] is not None

    artifact = sidecar["artifacts"][0]
    assert artifact["file"] == "report.pdf"
    assert artifact["sha256"] == hashlib.sha256(pdf).hexdigest()
    assert base64.b64decode(artifact["signature_b64"]) == b"\x01" * 64
    assert sidecar["algorithm"] == "EC_SIGN_ED25519"
    assert sidecar["message_convention"] == "ed25519_sign(sha256(file_bytes))"
    assert sidecar["kms_key_version"].endswith("/cryptoKeyVersions/1")
    assert sidecar["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")


def test_signer_fails_loud_on_request_crc_mismatch() -> None:
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_FakeKms(ok_crc=False))
    with pytest.raises(RuntimeError, match="CRC"):
        signer.sign_artifacts({"report.pdf": b"%PDF"})


def test_signer_refuses_signature_from_wrong_key() -> None:
    wrong = _KEY_VERSION.replace("/1", "/2")
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_FakeKms(name=wrong))
    with pytest.raises(RuntimeError, match="unexpected key"):
        signer.sign_artifacts({"report.pdf": b"%PDF"})


def test_signer_refuses_transit_corrupted_signature() -> None:
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_FakeKms(signature_crc32c=12345))
    with pytest.raises(RuntimeError, match="CRC32C verification in transit"):
        signer.sign_artifacts({"report.pdf": b"%PDF"})


def test_sidecar_is_json_serializable() -> None:
    signer = KmsReportSigner(key_version=_KEY_VERSION, client=_FakeKms())
    sidecar = signer.sign_artifacts({"report.pdf": b"%PDF", "report.json": b"{}"})
    parsed = json.loads(json.dumps(sidecar))
    assert len(parsed["artifacts"]) == 2
