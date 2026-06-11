"""Story-9.15 — canonical battery dataset metadata + loader.

Three battery datasets ship with Phoenix Audit:

- `harmbench-v1-sample` — 10-row curated HarmBench cut
- `owasp-llm-top10`    — one canonical case per OWASP LLM-Top-10 category
- `mitre-atlas-min`    — 5-row minimum MITRE ATLAS coverage map

Row content lives at `apps/phoenix-audit-agent/data/datasets/<slug>.json`
so a code review sees what changes when the corpus changes.
`scripts/seed_datasets.py` uses these definitions + `load_battery_dataset` to
push the rows into Phoenix and mirror the index row into Firestore.

The seed script is idempotent: it computes a SHA-256 over
`(items + name + description + source_url)` and skips both Phoenix and
Firestore writes when the stored content_hash matches.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "datasets"


@dataclass(frozen=True)
class BatteryDataset:
    """Canonical metadata for one battery dataset (slug + JSON file)."""

    slug: str
    json_file: Path


BATTERY_DATASETS: tuple[BatteryDataset, ...] = (
    BatteryDataset(slug="harmbench-v1-sample", json_file=_DATA_ROOT / "harmbench-v1-sample.json"),
    BatteryDataset(slug="owasp-llm-top10", json_file=_DATA_ROOT / "owasp-llm-top10.json"),
    BatteryDataset(slug="mitre-atlas-min", json_file=_DATA_ROOT / "mitre-atlas-min.json"),
)


@dataclass(frozen=True)
class LoadedBatteryDataset:
    """One battery dataset's parsed JSON contents."""

    slug: str
    name: str
    description: str
    source_url: str | None
    items: list[dict[str, Any]]
    content_hash: str


def load_battery_dataset(definition: BatteryDataset) -> LoadedBatteryDataset:
    """Read + parse a battery dataset JSON file. Computes the content_hash
    over `(items + name + description + source_url)` for idempotency."""
    raw = definition.json_file.read_text(encoding="utf-8")
    payload = json.loads(raw)
    name = payload["name"]
    description = payload.get("description", "")
    source_url = payload.get("source_url")
    items = payload["items"]

    # Hash inputs are sorted-keys JSON for deterministic ordering across
    # editors. Items go through the same canonical dump so a whitespace-only
    # edit in the JSON file doesn't trigger a Phoenix re-seed.
    canonical = json.dumps(
        {"name": name, "description": description, "source_url": source_url, "items": items},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return LoadedBatteryDataset(
        slug=definition.slug,
        name=name,
        description=description,
        source_url=source_url,
        items=items,
        content_hash=f"sha256:{digest}",
    )


__all__ = [
    "BATTERY_DATASETS",
    "BatteryDataset",
    "LoadedBatteryDataset",
    "load_battery_dataset",
]
