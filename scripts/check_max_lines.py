#!/usr/bin/env python3
"""Enforce 400-line maximum per source file.

Walks ROOTS, counts significant lines (skipping blanks + line-comment prefixes),
and exits non-zero if any file exceeds MAX_LINES. Per ADR-010 and
docs/best-practices/03 §1.1.

The 400-line rule scopes to source directories (apps/, packages/, scripts/) —
docs/ is intentionally exempt because spec completeness > brevity for
orchestrator + coding-agent comprehension. Resolves audit-notes.md IF-7.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 400
ROOTS = ["apps/", "packages/", "scripts/"]
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}
EXCLUDE_PATTERNS = {
    "__init__.py",
    ".d.ts",
    "_vendored/",
    "node_modules/",
    ".next/",
    "dist/",
    "build/",
}

LINE_COMMENT_PREFIXES = ("#", "//", "/*", "*", "<!--")


def is_excluded(path: Path) -> bool:
    s = str(path)
    return any(pat in s for pat in EXCLUDE_PATTERNS)


def count_significant_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return sum(
        1
        for raw in text.splitlines()
        if (stripped := raw.strip()) and not stripped.startswith(LINE_COMMENT_PREFIXES)
    )


def iter_source_files() -> list[Path]:
    found: list[Path] = []
    for root in ROOTS:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for path in root_path.rglob("*"):
            if path.is_file() and path.suffix in EXTENSIONS and not is_excluded(path):
                found.append(path)
    return found


def main() -> int:
    # --strict is the canonical invocation per the pre-commit hook; we accept
    # it as a no-op so the hook config doesn't need to drop the flag. Any other
    # arg is ignored (forward-compat).
    failures: list[tuple[Path, int]] = []
    for path in iter_source_files():
        count = count_significant_lines(path)
        if count > MAX_LINES:
            failures.append((path, count))

    if failures:
        print(f"[FAIL] {len(failures)} file(s) exceed {MAX_LINES} lines:")
        for p, c in sorted(failures, key=lambda x: -x[1]):
            print(f"  {p}: {c} lines (over by {c - MAX_LINES})")
        return 1
    print(f"[PASS] All files ≤ {MAX_LINES} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
