#!/usr/bin/env python3
"""Enforce 400-line maximum per source file.

Walks ROOTS, counts significant lines (skipping blanks + line-comment prefixes),
and exits non-zero if any file exceeds MAX_LINES. Per architecture.md ADR-010.

The 400-line rule scopes to source directories (apps/, packages/, scripts/) —
docs/ and tests/ are intentionally exempt because spec completeness > brevity
for orchestrator + coding-agent comprehension. Resolves audit-notes.md IF-7.

Exit codes:
  0  all source files ≤ 400 significant lines
  1  one or more files exceed the limit (rule violation; printed to stderr)
  2  configuration error (missing ROOT dir, invalid args, unreadable file)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_LINES = 400
ROOTS = ["apps/", "packages/", "scripts/"]
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}

# Exclusion sets split by shape so substring-match silent failures
# can't happen (e.g., `build/` falsely matching `apps/foo/rebuild/widget.ts`).
# Addresses PR #3 silent-failure-hunter F3 + pr-test-analyzer GAP-1.
EXCLUDE_FILENAMES = {"__init__.py"}
EXCLUDE_SUFFIXES = {".d.ts"}
EXCLUDE_DIR_COMPONENTS = {"_vendored", "node_modules", ".next", "dist", "build"}

LINE_COMMENT_PREFIXES = ("#", "//", "/*", "*", "<!--")


def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDE_FILENAMES:
        return True
    if any(path.name.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return True
    return any(part in EXCLUDE_DIR_COMPONENTS for part in path.parts)


def count_significant_lines(path: Path) -> int:
    # Strict UTF-8: a non-UTF-8 source file is a configuration error, not a
    # silent decode-skip. Raises UnicodeDecodeError → bubbles to main() → exit 2.
    text = path.read_text(encoding="utf-8")
    return sum(
        1
        for raw in text.splitlines()
        if (stripped := raw.strip()) and not stripped.startswith(LINE_COMMENT_PREFIXES)
    )


def iter_source_files() -> tuple[list[Path], list[str]]:
    """Return (files_found, missing_roots). Caller decides how to handle missing."""
    found: list[Path] = []
    missing: list[str] = []
    for root in ROOTS:
        root_path = Path(root)
        if not root_path.is_dir():
            missing.append(root)
            continue
        for path in root_path.rglob("*"):
            if path.is_file() and path.suffix in EXTENSIONS and not is_excluded(path):
                found.append(path)
    return found, missing


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="check_max_lines.py",
        description=f"Enforce {MAX_LINES}-line max per source file under {ROOTS}.",
    )
    # --strict is the documented canonical invocation. Today a no-op; reserved
    # for forward-compat (e.g., future --max-lines override or --json output).
    # argparse rejects unknown flags loud (exit 2) instead of silently accepting.
    p.add_argument(
        "--strict",
        action="store_true",
        help="Reserved for forward-compat; currently default behavior.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(sys.argv[1:] if argv is None else argv)

    files, missing = iter_source_files()
    if missing:
        # Missing ROOT is a config error, not a silent pass. Audit charter: every
        # silent failure forbidden. See PR #3 silent-failure-hunter Q2.
        print(
            f"[FAIL] configured ROOTS missing from cwd ({Path.cwd()}): {missing}",
            file=sys.stderr,
        )
        return 2

    failures: list[tuple[Path, int]] = []
    for path in files:
        count = count_significant_lines(path)
        if count > MAX_LINES:
            failures.append((path, count))

    if failures:
        # Failure output to stderr (Unix discipline). Q6.
        print(f"[FAIL] {len(failures)} file(s) exceed {MAX_LINES} lines:", file=sys.stderr)
        for p, c in sorted(failures, key=lambda x: -x[1]):
            print(f"  {p}: {c} lines (over by {c - MAX_LINES})", file=sys.stderr)
        return 1
    print(f"[PASS] All files ≤ {MAX_LINES} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
