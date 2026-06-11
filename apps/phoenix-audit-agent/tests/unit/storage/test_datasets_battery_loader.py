"""Story-9.15 slice 7 — battery dataset loader contract."""

from __future__ import annotations


def test_battery_definitions_pin_three_launch_datasets() -> None:
    """The 3 launch sets are documented + checked in by slug."""
    from phoenix_audit_agent.storage.datasets_battery import BATTERY_DATASETS

    slugs = [d.slug for d in BATTERY_DATASETS]
    assert slugs == ["harmbench-v1-sample", "owasp-llm-top10", "mitre-atlas-min"]


def test_each_battery_dataset_loads_with_valid_items() -> None:
    """Every checked-in JSON file parses and produces valid FlatDatasetItem-
    shaped rows that pass the upload validator."""
    from phoenix_audit_agent.api.datasets_validation import KNOWN_FAULT_CLASSES
    from phoenix_audit_agent.phoenix_tools.dataset_client import FlatDatasetItem
    from phoenix_audit_agent.storage.datasets_battery import (
        BATTERY_DATASETS,
        load_battery_dataset,
    )

    for definition in BATTERY_DATASETS:
        loaded = load_battery_dataset(definition)
        assert loaded.name
        assert loaded.items
        for row in loaded.items:
            # Same canon as the upload validator — drift here means a bad seed.
            assert row["fault_class"] in KNOWN_FAULT_CLASSES, (
                f"{definition.slug}/{row['case_id']}: unknown fault_class {row['fault_class']!r}"
            )
            FlatDatasetItem.model_validate(row)
        # case_id uniqueness inside each set.
        case_ids = [r["case_id"] for r in loaded.items]
        assert len(case_ids) == len(set(case_ids)), f"duplicate case_id in {definition.slug}"


def test_content_hash_stable_across_loads() -> None:
    """Two loads of the same file produce the same content_hash — that's the
    idempotency contract the seed script relies on."""
    from phoenix_audit_agent.storage.datasets_battery import (
        BATTERY_DATASETS,
        load_battery_dataset,
    )

    for definition in BATTERY_DATASETS:
        h1 = load_battery_dataset(definition).content_hash
        h2 = load_battery_dataset(definition).content_hash
        assert h1 == h2
        assert h1.startswith("sha256:")
