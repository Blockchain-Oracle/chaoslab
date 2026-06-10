"""Reporter — the signed regulator-ready audit report (story-6.7).

Render pipeline: ReportData -> HTML (locked-paragraph discipline) ->
WeasyPrint PDF -> Cloud KMS Ed25519 detached signatures -> GCS delivery.
"""

from phoenix_audit_agent.reporter._html import (
    DEFAULT_RESIDENCY_PARAGRAPH,
    HEADER_WARNING_TEMPLATE,
    ReportData,
    ReportProbe,
    build_report_html,
)
from phoenix_audit_agent.reporter.renderer import render_pdf
from phoenix_audit_agent.reporter.signer import KmsReportSigner

# Single source of truth for the signed artifact set — generate_signed_report
# uploads exactly these; the read API derives blob paths from the same tuple.
REPORT_ARTIFACT_NAMES = ("report.pdf", "report.json", "signature.json")

__all__ = [
    "DEFAULT_RESIDENCY_PARAGRAPH",
    "HEADER_WARNING_TEMPLATE",
    "REPORT_ARTIFACT_NAMES",
    "KmsReportSigner",
    "ReportData",
    "ReportProbe",
    "build_report_html",
    "render_pdf",
]
