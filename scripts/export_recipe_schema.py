"""Export HardeningRecipe JSON Schema to packages/shared-types/.

The exported artifact is committed to git so the frontend build doesn't
have to run Python to type-check against the recipe contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps/chaoslab-agent/src"))

from chaoslab_agent.patcher.recipe import HardeningRecipe  # noqa: E402


def main() -> int:
    schema = HardeningRecipe.model_json_schema()
    out_path = REPO_ROOT / "packages/shared-types/hardening-recipe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys gives deterministic diffs; trailing newline keeps editors quiet.
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(f"wrote {out_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
