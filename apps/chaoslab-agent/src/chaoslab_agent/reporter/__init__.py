"""Reporter — the signed regulator-ready audit report (story-6.7).

Render pipeline: ReportData -> HTML (locked-paragraph discipline) ->
WeasyPrint PDF -> Cloud KMS Ed25519 detached signatures -> GCS delivery.
"""

from chaoslab_agent.reporter._html import (
    DEFAULT_RESIDENCY_PARAGRAPH,
    HEADER_WARNING_TEMPLATE,
    ReportData,
    ReportProbe,
    build_report_html,
)
from chaoslab_agent.reporter.renderer import render_pdf
from chaoslab_agent.reporter.signer import KmsReportSigner

__all__ = [
    "DEFAULT_RESIDENCY_PARAGRAPH",
    "HEADER_WARNING_TEMPLATE",
    "KmsReportSigner",
    "ReportData",
    "ReportProbe",
    "build_report_html",
    "render_pdf",
]
