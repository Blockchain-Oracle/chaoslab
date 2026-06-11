"""Story-9.15 slice 7 — `scripts/seed_datasets.py` idempotency.

The script seeds the 3 battery datasets via the swap-able PhoenixDatasetClient
+ DatasetIndexStore seams. We exercise it offline against the in-memory
fakes — the same seams the API tests use — and assert (a) all three sets
land on first run and (b) a second run touches nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def seeded_stores(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple]:
    """Wire the in-memory PhoenixDatasetClient + InMemoryDatasetIndexStore."""
    from phoenix_audit_agent.api import datasets as datasets_api
    from phoenix_audit_agent.storage import datasets as dataset_storage

    from .fakes import FakePhoenixDatasetClient, InMemoryDatasetIndexStore

    phoenix = FakePhoenixDatasetClient()
    index = InMemoryDatasetIndexStore()
    datasets_api.set_phoenix_client(phoenix)
    dataset_storage.set_dataset_index_store(index)
    yield phoenix, index
    datasets_api.set_phoenix_client(None)
    dataset_storage.set_dataset_index_store(None)


@pytest.mark.asyncio
async def test_seed_writes_all_three_on_first_run(seeded_stores) -> None:
    """First-time seed: every battery slug lands in both stores."""
    phoenix, index = seeded_stores

    seed = _load_seed_module()

    rc = await seed.main_async(_args(dry_run=False))
    assert rc == 0

    for slug in ("harmbench-v1-sample", "owasp-llm-top10", "mitre-atlas-min"):
        idx = await index.get_by_slug(slug)
        assert idx is not None
        assert idx.kind == "battery"
        assert idx.row_count > 0
        # Phoenix-side dataset exists too.
        items = await phoenix.get_examples(idx.phoenix_dataset_id)
        assert len(items) == idx.row_count


@pytest.mark.asyncio
async def test_second_run_is_a_noop(seeded_stores) -> None:
    """Idempotency contract: re-running the seed against an already-seeded
    store creates NO new Phoenix datasets."""
    phoenix, _index = seeded_stores

    seed = _load_seed_module()

    await seed.main_async(_args(dry_run=False))
    phoenix_ids_after_first = sorted(phoenix._datasets.keys())

    # Re-seed: every slug skips.
    rc = await seed.main_async(_args(dry_run=False))
    assert rc == 0
    assert sorted(phoenix._datasets.keys()) == phoenix_ids_after_first


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(seeded_stores) -> None:
    """`--dry-run` decides what would happen without writing."""
    phoenix, index = seeded_stores

    seed = _load_seed_module()

    rc = await seed.main_async(_args(dry_run=True))
    assert rc == 0
    assert phoenix._datasets == {}
    assert await index.get_by_slug("harmbench-v1-sample") is None


def _load_seed_module():
    """Load `scripts/seed_datasets.py` by file path — the repo's pytest
    config sets the app dir as the rootdir, so `import scripts.*` is not
    on the path. Path-based import keeps the test colocated with the
    package without leaking script paths into prod code."""
    import importlib.util

    script_path = Path(__file__).resolve().parents[5] / "scripts" / "seed_datasets.py"
    spec = importlib.util.spec_from_file_location("seed_datasets_mod", script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _args(*, dry_run: bool):
    import argparse

    ns = argparse.Namespace()
    ns.dry_run = dry_run
    return ns


def test_script_path_exists() -> None:
    """The script ships at the documented path so `uv run python
    scripts/seed_datasets.py` works."""
    repo_root = Path(__file__).resolve().parents[5]
    assert (repo_root / "scripts" / "seed_datasets.py").exists()
