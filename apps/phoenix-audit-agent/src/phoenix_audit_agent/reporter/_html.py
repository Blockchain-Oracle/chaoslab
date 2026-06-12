"""Report HTML builder — the locked-paragraph discipline lives here.

The two legally-locked paragraphs render VERBATIM from the canonical
fixtures in docs/run-config-schema.md and docs/header-convention.md.
Only declared placeholders substitute ({N}); any other rewording is a
spec violation gated by tests/unit/reporter/test_reporter.py.
"""

from __future__ import annotations

import html as html_mod
import re
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from phoenix_audit_agent.reporter._html_sections import (
    cover_seal_block,
    recipe_markdown_html,
    regulatory_mapping_html,
    signature_meta_value,
)

_FONT_DIR = Path(__file__).parent / "fonts"

# docs/run-config-schema.md §"Canonical fixture (default mode)" — VERBATIM.
DEFAULT_RESIDENCY_PARAGRAPH = (
    "Audit traces are retained in Phoenix Audit's hosted Phoenix project for 24 hours "
    "after this report's cryptographic signature is emitted, then cryptographically "
    "erased via Cloud KMS key-shred. Phoenix Audit acts as a GDPR Article 28 data "
    "processor for the duration of the retention window. This signed PDF is the durable "
    "artifact; all underlying probe-and-response data is destroyed after the retention "
    "window closes."
)

# docs/header-convention.md §"Canonical fixture" — VERBATIM, {N} only.
HEADER_WARNING_TEMPLATE = (
    "Target did not signal it honored the X-Phoenix-Audit-* headers "
    "(`phoenix_audit.honored = true` was absent from {N} probe-response spans). "
    "Side-effecting tool calls during this audit run MAY have been executed for real "
    "against the target. To opt into dry-run behavior, the target must read "
    "`X-Phoenix-Audit-Dry-Run` and short-circuit side-effecting tools when its value "
    "is `true`, AND emit `phoenix_audit.honored = true` as a span attribute on every "
    "response."
)


class ReportProbe(BaseModel):
    model_config = ConfigDict(frozen=True)

    n: int = Field(ge=1)
    fault_class: str
    verdict: str  # pass | fail | error
    span_id: str
    score: float = Field(ge=0.0, le=1.0)
    transport_error: bool = False
    rubric_error: bool = False
    # Default False so transport-fail / rubric-error / pass-by-avoidance
    # probes don't silently claim the fault executed. Only the post-rubric
    # pass-by-firing path sets this to True (positive-evidence polarity per
    # PR #129 code-review #3). Disambiguates "agent defended a real attack"
    # (True) from "agent dodged a never-sprung trap" (False).
    fault_triggered: bool = False


class ReportData(BaseModel):
    """Everything the report renders — REAL run data only, no fixtures."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    target_url: str
    framework_label: str
    created_at: str
    probes: list[ReportProbe]
    passed: int
    failed: int
    errored: int
    transport_failed: int
    cluster_ids: list[str]
    root_causes: list[str]
    excluded_transport_failures: int
    annotation_writeback_failed: bool
    clustering_skipped: str | None
    recipe_id: str | None
    markdown_url: str | None
    honored_missing_count: int = Field(ge=0)
    # Response spans the auditor could NOT read from Phoenix. Disclosed so the
    # report never implies "verified compliant" for spans nobody inspected.
    honored_unreadable_count: int = Field(default=0, ge=0)
    # Story-9.21: when set, span-id cells in the probe table become real
    # PDF hyperlinks (WeasyPrint emits link annotations) to the Phoenix UI.
    # Empty ⇒ today's plain monospace text — never a dead link.
    phoenix_ui_base: str | None = None
    phoenix_project: str | None = None


def _esc(value: str) -> str:
    return html_mod.escape(value, quote=True)


def _verdict_cell(p: ReportProbe) -> str:
    if p.verdict == "error":
        # Marked non-verdict — a regulator must never mistake this for a
        # scored outcome (docs/architecture.md silent-failure pattern #4).
        return '<span class="stamp warn">ERROR</span> <span class="marker">RUBRIC ERROR</span>'
    cls = "pass" if p.verdict == "pass" else "fail"
    suffix = ' <span class="marker">TRANSPORT</span>' if p.transport_error else ""
    return f'<span class="stamp {cls}">{p.verdict.upper()}</span>{suffix}'


def _span_cell(data: ReportData, span_id: str) -> str:
    """Story-9.21: real PDF hyperlink when Phoenix UI is configured;
    otherwise the existing plain monospace cell. Quoted URL-safe pieces
    only — empty config never emits a dead link."""
    if data.phoenix_ui_base and data.phoenix_project:
        base = data.phoenix_ui_base.rstrip("/")
        project = quote(data.phoenix_project, safe="")
        sid = quote(span_id, safe="")
        href = f"{base}/projects/{project}/spans/{sid}"
        return f"<td class='mono small'><a href='{_esc(href)}'>{_esc(span_id)}</a></td>"
    return f"<td class='mono small'>{_esc(span_id)}</td>"


def _probe_rows(data: ReportData) -> str:
    rows = []
    for p in data.probes:
        rows.append(
            "<tr>"
            f"<td class='mono'>{p.n:02d}</td>"
            f"<td class='mono'>{_esc(p.fault_class)}</td>"
            f"<td>{_verdict_cell(p)}</td>"
            f"{_span_cell(data, p.span_id)}"
            f"<td class='mono small'>{p.score:.2f}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _clusters_section(data: ReportData) -> str:
    if data.clustering_skipped:
        return (
            "<p>Failures occurred, but none produced usable span evidence "
            f"({data.excluded_transport_failures} transport-level, "
            f"{data.errored} rubric errors) — root-cause clustering was skipped. "
            "This is stated explicitly rather than shaped as a clean audit.</p>"
        )
    if not data.cluster_ids:
        return "<p>Every probe passed — no failures to cluster.</p>"
    causes = "\n".join(
        f"<div class='cluster'><div class='mono small ember'>{_esc(cid)}</div>"
        f"<p class='serif'>{_esc(rc)}</p></div>"
        for cid, rc in zip(data.cluster_ids, data.root_causes, strict=False)
    )
    writeback = (
        "<p class='marker-block'>PHOENIX ANNOTATION WRITE-BACK FAILED — the clustering "
        "result is valid; span annotations were not persisted to Phoenix.</p>"
        if data.annotation_writeback_failed
        else ""
    )
    excluded = (
        f"<p class='small muted'>{data.excluded_transport_failures} transport-level "
        "failures carried no span evidence and were excluded from clustering.</p>"
        if data.excluded_transport_failures
        else ""
    )
    return causes + writeback + excluded


def _cluster_summary_sentence(data: ReportData) -> str:
    if not data.cluster_ids:
        return ""
    return f"One or more failures collapsed into {len(data.cluster_ids)} root-cause cluster(s)."


_SAFE_RUN_ID = re.compile(r"^[a-zA-Z0-9_\-]+$")


def build_report_html(
    data: ReportData,
    *,
    signing_key_fingerprint: str | None = None,
    kms_key_version: str | None = None,
    recipe_markdown: str | None = None,
) -> str:
    """The full report document. Verbatim-locked paragraphs render as-is.

    signing_key_fingerprint/kms_key_version put the REAL key identity on the
    cover (the PDF renders before the sidecar is signed, so only the key —
    not signed_at — is known here). recipe_markdown renders the recipe's
    actual content; the expiring signed URL never enters the durable PDF.
    """
    # run_id interpolates into the @page CSS content string where html.escape
    # is the wrong escaper (entities aren't decoded in CSS; backslashes pass
    # through). Server-generated ids are hex today — this guard keeps a future
    # id-shape change from becoming a CSS-string breakout.
    if not _SAFE_RUN_ID.fullmatch(data.run_id):
        msg = f"run_id contains CSS-unsafe characters: {data.run_id!r}"
        raise ValueError(msg)
    warning_block = ""
    if data.honored_missing_count > 0:
        warning_text = HEADER_WARNING_TEMPLATE.replace("{N}", str(data.honored_missing_count))
        # Locked text embeds UNescaped — it contains no HTML-unsafe characters
        # and html.escape would break the byte-identical snapshot obligation.
        warning_block = (
            "<div class='locked'><div class='locked-title'>HEADER CONVENTION WARNING — "
            f"INCLUDED FOR THIS RUN</div><p>{warning_text}</p></div>"
        )
    if data.honored_unreadable_count > 0:
        # NOT part of the locked paragraph — a separate factual disclosure so
        # the regulator can tell "verified" apart from "unverifiable".
        warning_block += (
            "<p class='marker-block'>HEADER VERIFICATION INCOMPLETE — "
            f"{data.honored_unreadable_count} probe-response span(s) could not be "
            "read from Phoenix; their header-convention status is unverified and "
            "they are excluded from the warning count above.</p>"
        )

    # The expiring signed URL must NEVER enter the durable PDF — it is a dead
    # link by filing time. The recipe id is the durable reference; the content
    # renders inline when provided.
    if data.recipe_id:
        recipe_block = (
            f"<p>Hardening recipe <span class='mono'>{_esc(data.recipe_id)}</span> was "
            "generated and delivered as a Markdown artifact alongside this report.</p>"
        )
        if recipe_markdown:
            recipe_block += recipe_markdown_html(recipe_markdown)
    else:
        recipe_block = "<p>No hardening recipe was generated for this run.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
@font-face {{
  font-family: "Newsreader";
  src: url("file://{_FONT_DIR}/Newsreader-Regular.ttf");
}}
@font-face {{
  font-family: "IBM Plex Mono";
  src: url("file://{_FONT_DIR}/IBMPlexMono-Regular.ttf");
}}
@font-face {{
  font-family: "IBM Plex Mono";
  font-weight: 600;
  src: url("file://{_FONT_DIR}/IBMPlexMono-SemiBold.ttf");
}}
@page {{
  size: A4;
  margin: 22mm 18mm;
  background: #faf7f0;
  @bottom-right {{
    content: "Phoenix Audit · {_esc(data.run_id)} · page " counter(page);
    font-family: "IBM Plex Mono";
    font-size: 7pt;
    color: #8f8674;
  }}
}}
body {{ font-family: "Newsreader", serif; color: #1c1712; font-size: 10.5pt; line-height: 1.55; }}
h1 {{ font-size: 22pt; font-weight: 400; letter-spacing: -0.01em; margin: 0 0 4mm; }}
h2 {{ font-size: 13pt; font-weight: 500; border-bottom: 0.5pt solid #1c1712;
     padding-bottom: 1.5mm; margin: 8mm 0 3mm; page-break-after: avoid; }}
.mono {{ font-family: "IBM Plex Mono", monospace; font-size: 8.5pt; }}
.small {{ font-size: 7.5pt; }}
.muted {{ color: #8f8674; }}
.ember {{ color: #8a4a1e; }}
.serif {{ font-family: "Newsreader", serif; }}
.kicker {{ font-family: "IBM Plex Mono"; font-size: 7.5pt; letter-spacing: 0.18em;
          text-transform: uppercase; color: #8f8674; margin-bottom: 2mm; }}
table {{ width: 100%; border-collapse: collapse; margin: 2mm 0; page-break-inside: avoid; }}
th {{ font-family: "IBM Plex Mono"; font-size: 7pt; letter-spacing: 0.12em;
     text-transform: uppercase; color: #8f8674; text-align: left;
     border-bottom: 0.7pt solid #1c1712; padding: 1.5mm 2mm; }}
td {{ border-bottom: 0.25pt solid rgba(28,23,18,0.16); padding: 2mm; font-size: 9pt;
     vertical-align: middle; }}
.stamp {{ font-family: "IBM Plex Mono"; font-size: 7pt; font-weight: 600;
         letter-spacing: 0.18em; border: 0.8pt solid currentColor; border-radius: 1pt;
         padding: 0.5mm 1.5mm; }}
.stamp.pass {{ color: #2e6b4f; }}
.stamp.fail {{ color: #9c3a22; }}
.stamp.warn {{ color: #8a6414; }}
.marker {{ font-family: "IBM Plex Mono"; font-size: 6.5pt; letter-spacing: 0.08em;
          color: #8a6414; border: 0.6pt dashed #8a6414; padding: 0.4mm 1.2mm; }}
.marker-block {{ font-family: "IBM Plex Mono"; font-size: 8pt; color: #8a6414;
               border: 0.6pt dashed #8a6414; padding: 2mm 3mm; }}
.locked {{ border: 0.5pt dashed rgba(28,23,18,0.3); background: #f2ede1;
          padding: 3mm 4mm; margin: 3mm 0; page-break-inside: avoid; }}
.locked-title {{ font-family: "IBM Plex Mono"; font-size: 6.5pt; letter-spacing: 0.14em;
               color: #8f8674; margin-bottom: 1.5mm; }}
.locked p {{ font-style: italic; font-size: 9pt; margin: 0; }}
.meta-row {{ display: flex; justify-content: space-between;
            border-bottom: 0.25pt dotted rgba(28,23,18,0.3); padding: 1.2mm 0; }}
.cluster {{ border-left: 1.5pt solid #8a4a1e; padding: 2mm 4mm; margin: 2mm 0;
           background: rgba(255,255,255,0.5); page-break-inside: avoid; }}
.cover-foot {{ margin-top: 6mm; }}
.pagebreak {{ page-break-before: always; }}
.cover-head {{ position: relative; padding-right: 36mm; }}
.stamp-foot {{ text-align: right; margin: 1mm 0 2mm; }}
.seal-wrap {{ position: absolute; top: 0; right: 0; width: 32mm; text-align: center;
             transform: rotate(-7deg); }}
.meta-row span:last-child {{ text-align: right; max-width: 72%; }}
.stamp-signed {{ font-family: "IBM Plex Mono"; font-size: 6.5pt; font-weight: 600;
               letter-spacing: 0.18em; color: #2e6b4f; border: 1pt solid #2e6b4f;
               border-radius: 1pt; padding: 1mm 1.5mm; margin-top: 1.5mm;
               display: inline-block; }}
.recipe-h2 {{ font-family: "Newsreader", serif; font-size: 11.5pt; font-weight: 500;
             margin: 4mm 0 1.5mm; page-break-after: avoid; }}
.recipe-h3 {{ font-family: "IBM Plex Mono"; font-size: 7.5pt; letter-spacing: 0.1em;
             color: #8a4a1e; margin: 3mm 0 1mm; page-break-after: avoid; }}
.recipe-text {{ font-size: 9pt; margin: 0 0 2mm; }}
.recipe-code {{ font-family: "IBM Plex Mono"; font-size: 7.5pt; line-height: 1.6;
              background: #f2ede1; border: 0.5pt solid rgba(28,23,18,0.16);
              border-radius: 1pt; padding: 2mm 3mm; margin: 0 0 3mm;
              white-space: pre-wrap; page-break-inside: avoid; }}
.recipe-code .diff-add {{ color: #2e6b4f; background: rgba(46,107,79,0.08); }}
.recipe-code .diff-del {{ color: #9c3a22; background: rgba(156,58,34,0.07); }}
.recipe-code .diff-hunk {{ color: #8f8674; }}
</style>
</head>
<body>

<!-- §1 cover & attestation -->
<div class="cover-head">
{cover_seal_block()}
<div class="kicker">Signed audit report · Phoenix Audit</div>
<h1>{_esc(data.framework_label)}</h1>
<div class="meta-row"><span>Audit run</span><span class="mono">{_esc(data.run_id)}</span></div>
<div class="meta-row"><span>Target agent</span>
<span class="mono">{_esc(data.target_url)}</span></div>
<div class="meta-row"><span>Filed</span><span class="mono">{_esc(data.created_at)}</span></div>
<div class="meta-row"><span>Signature</span>
<span class="mono">{signature_meta_value(signing_key_fingerprint, kms_key_version)}</span></div>
</div>

<div class="stamp-foot"><span class="stamp-signed">SIGNED · ED25519 · CLOUD KMS</span></div>

<div class="locked">
<div class="locked-title">DATA RESIDENCY — DEFAULT HOSTING VARIANT · LEGALLY LOCKED ·
RENDERS VERBATIM</div>
<p>{DEFAULT_RESIDENCY_PARAGRAPH}</p>
</div>
{warning_block}

<p class="cover-foot small muted">This document constitutes part of the EU AI Act Annex IV
technical documentation pack. Artifact integrity and chain-of-custody are established by
the detached Ed25519 signature sidecar (sha256-of-file message convention) verifiable
offline against the published public key. Erasure requests (GDPR Art. 17):
erasure@phoenix-audit.example · honored within 72 h.</p>

<!-- §2 executive summary -->
<h2>Executive summary</h2>
<p>Phoenix Audit ran {len(data.probes)} adversarial probes against the target agent.
{data.passed} passed, {data.failed} failed, {data.errored} could not be scored
(judge rubric errors — marked, never silently counted as pass or fail).
{_cluster_summary_sentence(data)}</p>

<!-- §3 adversarial probes -->
<h2>Adversarial probes</h2>
<table>
<thead><tr><th>#</th><th>Fault class</th><th>Verdict</th>
<th>Phoenix span</th><th>Score</th></tr></thead>
<tbody>
{_probe_rows(data)}
</tbody>
</table>
<p class="small muted">Methodology: probes are generated per fault class against the live
target; verdicts come from per-fault LLM-as-judge rubrics over the target's Phoenix trace
spans. The probe set is a deliberate budget-vs-coverage tradeoff, not comprehensive
coverage of any attack category.</p>

<!-- §4 failure clusters -->
<h2>Root-cause clusters</h2>
{_clusters_section(data)}

<!-- §5 hardening recipe -->
<h2>Hardening recipe</h2>
{recipe_block}

<!-- §6 regulatory mapping -->
<h2>Regulatory mapping</h2>
{regulatory_mapping_html(data.framework_label, data.failed)}

</body>
</html>"""
