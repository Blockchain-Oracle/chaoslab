"""Export HardeningRecipe JSON Schema to packages/shared-types/.

The exported artifact is committed to git so the frontend build doesn't
have to run Python to type-check against the recipe contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps/phoenix-audit-agent/src"))

from phoenix_audit_agent.patcher.recipe import HardeningRecipe  # noqa: E402


def main() -> int:
    schema = HardeningRecipe.model_json_schema()
    out_path = REPO_ROOT / "packages/shared-types/hardening-recipe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys gives deterministic diffs; trailing newline keeps editors quiet.
    expected = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    out_path.write_text(expected, encoding="utf-8")
    # Round-trip read to surface CRLF / encoding / umask corruption before
    # the script reports success.
    actual = out_path.read_text(encoding="utf-8")
    if actual != expected:
        sys.stderr.write(f"::error::export wrote corrupted bytes (umask/CRLF?) at {out_path}\n")
        return 1
    # Use stderr for the success line so the script stays quiet on stdout
    # when wired into pre-commit hooks.
    sys.stderr.write(f"wrote {out_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
