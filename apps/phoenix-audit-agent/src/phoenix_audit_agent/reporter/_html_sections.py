"""Designed presentation sections for the durable PDF (story-9.13).

The cover seal, the recipe markdown renderer (diff styling) and the
regulatory mapping table — split from _html.py to honor the 400-line cap.
Everything user-influenced is HTML-escaped; the recipe markdown is OUR
generated artifact but renders escaped anyway (defense in depth).
"""

from __future__ import annotations

import html as html_mod
import re


def _esc(value: str) -> str:
    return html_mod.escape(value, quote=True)


_H2 = 2
_INLINE_CODE = re.compile(r"`([^`]+)`")
_INLINE_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _inline(text: str) -> str:
    """Minimal inline markdown on ESCAPED text: `code` and **bold**."""
    escaped = _esc(text)
    escaped = _INLINE_CODE.sub(r'<span class="mono">\1</span>', escaped)
    return _INLINE_BOLD.sub(r"<strong>\1</strong>", escaped)


def cover_seal_block() -> str:
    """The designed seal + SIGNED stamp for the cover page."""
    return """<div class="seal-wrap">
<svg width="86" height="86" viewBox="0 0 92 92" xmlns="http://www.w3.org/2000/svg">
<circle cx="46" cy="46" r="43" fill="none" stroke="#8a4a1e" stroke-width="1.6"/>
<circle cx="46" cy="46" r="34" fill="none" stroke="#8a4a1e" stroke-width="0.8"
 stroke-dasharray="2 3"/>
<text x="46" y="42" text-anchor="middle" font-family="IBM Plex Mono" font-size="8.5"
 fill="#8a4a1e" letter-spacing="2">PHOENIX</text>
<text x="46" y="54" text-anchor="middle" font-family="IBM Plex Mono" font-size="8.5"
 fill="#8a4a1e" letter-spacing="2">AUDIT</text>
<text x="46" y="68" text-anchor="middle" font-family="IBM Plex Mono" font-size="5.5"
 fill="#8a4a1e" letter-spacing="1">CLOUD KMS</text>
</svg>
<div class="stamp-signed">SIGNED · ED25519</div>
</div>"""


def signature_meta_value(fingerprint: str | None, kms_key_version: str | None) -> str:
    """The cover's Signature row — the REAL key identity when known."""
    if not fingerprint:
        return "Cloud KMS · Ed25519 · detached sidecar"
    short = _esc(fingerprint[:16])
    version = ""
    if kms_key_version:
        tail = kms_key_version.split("/keyRings/")[-1]
        version = f" · {_esc(tail)}"
    return f"Cloud KMS · Ed25519 · key {short}…{version}"


def _diff_class(line: str) -> str:
    if line.startswith(("+++", "---", "@@")):
        return "diff-hunk"
    if line.startswith("+"):
        return "diff-add"
    if line.startswith("-"):
        return "diff-del"
    return ""


def recipe_markdown_html(md: str) -> str:
    """Structural markdown→HTML for OUR recipe artifact: headings, paragraphs,
    fenced code with per-line diff styling. Unknown constructs degrade to
    plain escaped text — content never disappears."""
    out: list[str] = []
    paragraph: list[str] = []
    fence: list[str] | None = None

    def flush() -> None:
        text = "\n".join(paragraph).strip()
        if text:
            out.append(f"<p class='recipe-text'>{_inline(text)}</p>")
        paragraph.clear()

    for line in md.split("\n"):
        if fence is not None:
            if line.startswith("```"):
                rows = "".join(
                    f"<div class='{_diff_class(code_line)}'>{_esc(code_line)}</div>"
                    for code_line in fence
                )
                out.append(f"<pre class='recipe-code'>{rows}</pre>")
                fence = None
            else:
                fence.append(line)
            continue
        if line.startswith("```"):
            flush()
            fence = []
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush()
            level, text = len(heading.group(1)), heading.group(2).strip()
            if level == 1:
                # The artifact's own title — the PDF section already has one.
                continue
            cls = "recipe-h2" if level == _H2 else "recipe-h3"
            out.append(f"<div class='{cls}'>{_inline(text)}</div>")
            continue
        paragraph.append(line)
    if fence is not None:
        # Unterminated fence: keep its lines — never swallow content.
        rows = "".join(
            f"<div class='{_diff_class(code_line)}'>{_esc(code_line)}</div>" for code_line in fence
        )
        out.append(f"<pre class='recipe-code'>{rows}</pre>")
    flush()
    return "\n".join(out)


def regulatory_mapping_html(framework_label: str, failed: int) -> str:
    """The framework article table — real counts only, no fabricated
    per-article distribution."""
    finding_cell = f"{failed} finding{'' if failed == 1 else 's'} (probe table)"
    rows = [
        ("Article 9", "Risk management system", "this audit constitutes testing evidence"),
        ("Article 12", "Record-keeping", "satisfied via Phoenix trace spans"),
        ("Article 15", "Accuracy, robustness, cybersecurity", finding_cell),
        ("Article 72", "Post-market monitoring", "see continuous monitoring"),
    ]
    body = "\n".join(
        f"<tr><td class='mono ember'>{a}</td><td>{t}</td><td class='mono small'>{n}</td></tr>"
        for a, t, n in rows
    )
    return f"""<table>
<thead><tr><th>Article</th><th>Scope</th><th>Status</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
<p class="small muted">Findings map to the regulatory frame selected at run time
({_esc(framework_label)}). Phoenix trace spans referenced per probe provide the
record-keeping evidence trail; the signed artifact set provides the chain-of-custody
anchor required for filing.</p>"""


__all__ = [
    "cover_seal_block",
    "recipe_markdown_html",
    "regulatory_mapping_html",
    "signature_meta_value",
]
