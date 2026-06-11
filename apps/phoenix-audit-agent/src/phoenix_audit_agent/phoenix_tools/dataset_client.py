"""Story-9.15 — narrow Protocol over `AsyncClient.datasets`.

API routes + the audit runner never import `phoenix.client.AsyncClient`
directly. They depend on `PhoenixDatasetClient` (Protocol). The production
impl `PhoenixDatasetClientImpl` calls the SDK; the test fake
`FakePhoenixDatasetClient` (in tests/unit/storage/fakes.py) implements the
same Protocol so the unit suite is offline by construction.

Flat-row contract: our code passes a list of `FlatDatasetItem`-shaped
mappings (the columns the operator sees — `case_id / prompt / fault_class /
expected / source / severity / notes`). The wrapper slices them into
Phoenix's `input / output / metadata` buckets via `input_keys` / `output_keys`
/ `metadata_keys` per the SDK convention. The buckets never leak out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Sequence

# Buckets per docs/stories/story-9.15-phoenix-datasets.md (architecture decision).
_INPUT_KEYS: tuple[str, ...] = ("case_id", "prompt", "fault_class")
_OUTPUT_KEYS: tuple[str, ...] = ("expected",)
_METADATA_KEYS: tuple[str, ...] = ("source", "severity", "notes")


class FlatDatasetItem(BaseModel):
    """The flat row shape our code reads and writes. Phoenix's `DatasetExample`
    has `input/output/metadata` mappings; this is the un-bucketed view we
    pass around inside the app."""

    model_config = ConfigDict(extra="ignore")

    case_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=10_000)
    fault_class: str = Field(min_length=1)
    expected: str = Field(min_length=1)
    source: str = Field(min_length=1)
    severity: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CreatedDataset:
    """Result of `PhoenixDatasetClient.create`. Carries the bridge fields the
    Firestore index row will store."""

    phoenix_dataset_id: str
    version_id: str
    example_count: int


class PhoenixDatasetError(Exception):
    """Base class for typed wrapper failures."""


class PhoenixDatasetNotFoundError(PhoenixDatasetError):
    """The named Phoenix dataset does not exist (or was deleted)."""


class PhoenixUnavailableError(PhoenixDatasetError):
    """Phoenix is unreachable (5xx, timeout, network). The detail page's
    503-graceful-degrade path catches this."""


@runtime_checkable
class PhoenixDatasetClient(Protocol):
    """Narrow Protocol our code depends on."""

    async def create(
        self,
        *,
        name: str,
        examples: Sequence[dict[str, Any]] | Sequence[FlatDatasetItem],
        description: str | None,
        source_url: str | None,
    ) -> CreatedDataset:
        """Create a new Phoenix dataset; return the bridge ids and count."""
        ...

    async def add_examples(
        self,
        phoenix_dataset_id: str,
        examples: Sequence[dict[str, Any]] | Sequence[FlatDatasetItem],
    ) -> str:
        """Append examples; return the new Phoenix version_id (Phoenix's
        `add_examples_to_dataset` creates a new VERSION per call)."""
        ...

    async def get_examples(self, phoenix_dataset_id: str) -> list[FlatDatasetItem]:
        """Read all examples for the current version. Raises
        `PhoenixDatasetNotFoundError` if the dataset doesn't exist;
        `PhoenixUnavailableError` if Phoenix is unreachable."""
        ...

    async def delete(self, phoenix_dataset_id: str) -> None:
        """Delete the Phoenix dataset. Best-effort: a NotFound is treated
        as already-deleted (the Firestore index row is what hides the
        dataset from the user anyway)."""
        ...


def _normalize_row(row: dict[str, Any] | FlatDatasetItem) -> dict[str, Any]:
    """Coerce either input shape into a flat dict the SDK accepts."""
    if isinstance(row, FlatDatasetItem):
        return row.model_dump()
    return dict(row)


def _flat_from_example(example: dict[str, Any]) -> FlatDatasetItem:
    """Pull a Phoenix `DatasetExample` back into our flat shape. The example
    is the v1 wire form: `{id, node_id, input, output, metadata}`."""
    merged = {
        **example.get("input", {}),
        **example.get("output", {}),
        **example.get("metadata", {}),
    }
    return FlatDatasetItem.model_validate(merged)


class PhoenixDatasetClientImpl:
    """Production wrapper. Uses `_build_client` from `run_experiment.py` —
    the same canonical settings-driven constructor."""

    def __init__(self) -> None:
        # Late-bind so the unit suite doesn't pull in the SDK when tests use
        # the fake. The constructor is no-arg for Protocol compliance.
        pass

    def _client(self) -> Any:
        from phoenix_audit_agent.config import get_settings
        from phoenix_audit_agent.phoenix_tools.run_experiment import _build_client

        return _build_client(get_settings())

    async def create(
        self,
        *,
        name: str,
        examples: Sequence[dict[str, Any]] | Sequence[FlatDatasetItem],
        description: str | None,
        source_url: str | None,
    ) -> CreatedDataset:
        rows = [_normalize_row(r) for r in examples]
        # `source_url` is appended to the description for now — Phoenix's
        # Dataset has a description field but no native source_url. The
        # Firestore index carries the canonical source_url.
        full_desc = description or ""
        if source_url:
            full_desc = f"{full_desc}\nSource: {source_url}".strip()
        ds = await self._client().datasets.create_dataset(
            name=name,
            examples=rows,
            input_keys=_INPUT_KEYS,
            output_keys=_OUTPUT_KEYS,
            metadata_keys=_METADATA_KEYS,
            dataset_description=full_desc or None,
        )
        return CreatedDataset(
            phoenix_dataset_id=ds.id,
            version_id=ds.version_id,
            example_count=len(rows),
        )

    async def add_examples(
        self,
        phoenix_dataset_id: str,
        examples: Sequence[dict[str, Any]] | Sequence[FlatDatasetItem],
    ) -> str:
        rows = [_normalize_row(r) for r in examples]
        ds = await self._client().datasets.add_examples_to_dataset(
            dataset=phoenix_dataset_id,
            examples=rows,
            input_keys=_INPUT_KEYS,
            output_keys=_OUTPUT_KEYS,
            metadata_keys=_METADATA_KEYS,
        )
        return ds.version_id  # type: ignore[no-any-return]

    async def get_examples(self, phoenix_dataset_id: str) -> list[FlatDatasetItem]:
        try:
            ds = await self._client().datasets.get_dataset(dataset=phoenix_dataset_id)
        except Exception as e:
            # The SDK doesn't expose a typed NotFound, so we partition by
            # message content. 5xx / connection errors raise Unavailable so
            # the route can return 503; everything else is treated as Not Found.
            text = str(e).lower()
            if "404" in text or "not found" in text:
                raise PhoenixDatasetNotFoundError(phoenix_dataset_id) from e
            raise PhoenixUnavailableError(str(e)) from e
        return [_flat_from_example(ex) for ex in ds.examples]

    async def delete(self, phoenix_dataset_id: str) -> None:
        # Phoenix's public SDK does not (yet) expose a dataset delete in
        # v1.x. We log + no-op; the Firestore index delete is what hides
        # the dataset from the user. A future SDK version can wire this in.
        return None


__all__ = [
    "CreatedDataset",
    "FlatDatasetItem",
    "PhoenixDatasetClient",
    "PhoenixDatasetClientImpl",
    "PhoenixDatasetError",
    "PhoenixDatasetNotFoundError",
    "PhoenixUnavailableError",
]
