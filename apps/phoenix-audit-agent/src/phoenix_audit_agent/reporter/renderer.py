"""HTML -> PDF via WeasyPrint.

WeasyPrint needs Pango at runtime (Dockerfile installs libpango-1.0-0
libpangoft2-1.0-0 libharfbuzz-subset0 — ~19 MB on python-slim). Import is
deferred so the rest of phoenix_audit_agent works in environments without it;
the failure mode is a loud ImportError at render time, never a silent skip.
"""

from __future__ import annotations


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML  # deferred: Pango-dependent native import

    pdf = HTML(string=html).write_pdf()
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF"):
        msg = "WeasyPrint returned non-PDF output"
        raise RuntimeError(msg)
    return pdf
