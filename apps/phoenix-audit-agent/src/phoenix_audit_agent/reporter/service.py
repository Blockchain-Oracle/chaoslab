"""generate_signed_report — render, sign, deliver.

The single entry the audit driver calls. Returns the signed-URL map, or
None when the signing key is not configured — in which case the SKIP is
loud (CRITICAL log + the caller emits `report_skipped`), never a silently
unsigned artifact. An unsigned regulator-facing report is worse than no
report: it looks like evidence but proves nothing.
"""

from __future__ import annotations

import json
import logging

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.reporter._html import ReportData, build_report_html
from phoenix_audit_agent.reporter.emitter import ReportEmitter
from phoenix_audit_agent.reporter.renderer import render_pdf
from phoenix_audit_agent.reporter.signer import KmsReportSigner

# stdlib logger on purpose: CRITICAL must survive aggressive Cloud Logging
# sink filters (same posture as the GCS-probe escape hatch in main.py).
_logger = logging.getLogger(__name__)


async def generate_signed_report(data: ReportData) -> dict[str, str] | None:
    """Render the PDF + JSON, sign both, upload all three artifacts.

    Returns {"report.pdf": url, "report.json": url, "signature.json": url},
    or None when KMS_SIGNING_KEY_VERSION is unset (loud skip).
    """
    settings = get_settings()
    key_version = settings.KMS_SIGNING_KEY_VERSION
    if not key_version.strip():
        _logger.critical(
            "KMS_SIGNING_KEY_VERSION is not configured — the signed report for run %s "
            "was NOT generated. Provision the Ed25519 key via "
            "infra/workload-identity-federation.sh and set the env var.",
            data.run_id,
        )
        return None

    html = build_report_html(data)
    pdf_bytes = render_pdf(html)
    json_bytes = json.dumps(data.model_dump(), indent=2, sort_keys=True).encode("utf-8")

    signer = KmsReportSigner(key_version=key_version)
    sidecar = signer.sign_artifacts({"report.pdf": pdf_bytes, "report.json": json_bytes})
    sidecar_bytes = json.dumps(sidecar, indent=2, sort_keys=True).encode("utf-8")

    emitter = ReportEmitter()
    # signature.json uploads FIRST: a partial-upload failure can then never
    # leave an unverifiable report.pdf orphaned in the bucket — artifacts
    # without their sidecar are impossible by construction.
    return await emitter.emit(
        data.run_id,
        {
            "signature.json": sidecar_bytes,
            "report.pdf": pdf_bytes,
            "report.json": json_bytes,
        },
    )
