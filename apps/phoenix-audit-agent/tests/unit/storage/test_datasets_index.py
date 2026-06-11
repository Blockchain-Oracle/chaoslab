"""Story-9.15 — `DatasetIndexStore` Protocol contract.

Mirror of `storage/profiles.py`'s pattern: a thin Protocol, a Firestore
impl, and an in-memory fake for unit tests. The store owns ONLY the index
rows (slug → phoenix_dataset_id + ownership + kind). Example rows live in
Phoenix — that's the `PhoenixDatasetClient` Protocol, exercised by slice 2.

Visibility rule (story-9.15 BDD): `list_visible(uid)` returns every battery
dataset (owner_uid is None) + every uploaded dataset where
`owner_uid == uid` + every regression dataset whose `owner_uid == uid`.
The store does not know about agents; the visibility filter on regression
sets uses `owner_uid` directly (regression sets always carry the linked
agent's `owner_uid` per the model invariant).
"""

from __future__ import annotations

import pytest


def _idx(
    *,
    slug: str,
    kind: str,
    owner_uid: str | None = None,
    agent_id: str | None = None,
    name: str | None = None,
):
    """Helper that builds a valid `DatasetIndex` for the given kind."""
    from phoenix_audit_agent.storage.models import DatasetIndex

    return DatasetIndex(
        dataset_id=slug,
        phoenix_dataset_id=f"phx_ds_{slug}",
        name=name or slug,
        kind=kind,  # ty: ignore[invalid-argument-type]
        owner_uid=owner_uid,
        agent_id=agent_id,
        row_count=0,
        source_url=None,
        content_hash=f"sha256:{slug}",
        created_at="2026-06-11T07:00:00+00:00",
        updated_at="2026-06-11T07:00:00+00:00",
    )


async def test_upsert_then_get_by_slug_round_trips() -> None:
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    row = _idx(slug="harmbench-v1-sample", kind="battery")
    await store.upsert(row)

    got = await store.get_by_slug("harmbench-v1-sample")
    assert got is not None
    assert got.kind == "battery"
    assert got.phoenix_dataset_id == "phx_ds_harmbench-v1-sample"


async def test_get_by_slug_missing_returns_none() -> None:
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    assert await store.get_by_slug("does-not-exist") is None


async def test_list_visible_filters_by_owner_and_kind() -> None:
    """The visibility rule: every user sees battery, their own uploaded,
    their own regression. Foreign uploaded/regression must NOT leak."""
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    # Battery — visible to everyone.
    await store.upsert(_idx(slug="harmbench-v1-sample", kind="battery"))
    await store.upsert(_idx(slug="owasp-llm-top10", kind="battery"))
    # Alice's stuff.
    await store.upsert(_idx(slug="ds_alice1", kind="uploaded", owner_uid="uid_alice"))
    await store.upsert(
        _idx(
            slug="regression-alice-bot", kind="regression", owner_uid="uid_alice", agent_id="agt_a"
        )
    )
    # Bob's stuff — must not appear in Alice's list.
    await store.upsert(_idx(slug="ds_bob1", kind="uploaded", owner_uid="uid_bob"))
    await store.upsert(
        _idx(slug="regression-bob-bot", kind="regression", owner_uid="uid_bob", agent_id="agt_b")
    )

    visible = await store.list_visible("uid_alice")
    slugs = {row.dataset_id for row in visible}

    assert "harmbench-v1-sample" in slugs
    assert "owasp-llm-top10" in slugs
    assert "ds_alice1" in slugs
    assert "regression-alice-bot" in slugs
    # Foreign sets EXCLUDED.
    assert "ds_bob1" not in slugs
    assert "regression-bob-bot" not in slugs


async def test_list_visible_for_anonymous_returns_only_battery() -> None:
    """`uid=None` is the "no signed-in user" case — only battery shows."""
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    await store.upsert(_idx(slug="harmbench-v1-sample", kind="battery"))
    await store.upsert(_idx(slug="ds_alice1", kind="uploaded", owner_uid="uid_alice"))

    visible = await store.list_visible(None)
    assert {r.dataset_id for r in visible} == {"harmbench-v1-sample"}


async def test_delete_by_slug_removes_row() -> None:
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    await store.upsert(_idx(slug="ds_x", kind="uploaded", owner_uid="uid_alice"))
    assert await store.get_by_slug("ds_x") is not None

    await store.delete_by_slug("ds_x")
    assert await store.get_by_slug("ds_x") is None


async def test_delete_by_slug_missing_is_noop() -> None:
    """Deleting a non-existent row must not raise — the API DELETE
    endpoint is idempotent."""
    from ..storage.fakes import InMemoryDatasetIndexStore

    store = InMemoryDatasetIndexStore()
    await store.delete_by_slug("never-existed")  # must not raise


async def test_module_seam_set_and_reset() -> None:
    """`set_dataset_index_store(None)` resets to the lazy Firestore default,
    mirroring the profiles store seam."""
    from phoenix_audit_agent.storage import datasets as dataset_storage

    from ..storage.fakes import InMemoryDatasetIndexStore

    sentinel = InMemoryDatasetIndexStore()
    dataset_storage.set_dataset_index_store(sentinel)
    assert dataset_storage.get_dataset_index_store() is sentinel

    dataset_storage.set_dataset_index_store(None)
    # The lazy default is constructed on demand; we don't actually exercise
    # Firestore here, just confirm a non-None instance comes back.
    fresh = dataset_storage.get_dataset_index_store()
    assert fresh is not None
    assert fresh is not sentinel
    # Clean up so other tests don't see our Firestore instance.
    dataset_storage.set_dataset_index_store(None)


@pytest.fixture(autouse=True)
def _reset_store_seam():
    """Make sure tests can't leak the module-level store across runs."""
    from phoenix_audit_agent.storage import datasets as dataset_storage

    dataset_storage.set_dataset_index_store(None)
    yield
    dataset_storage.set_dataset_index_store(None)
