"""Story-9.15 — narrow Protocol over `AsyncClient.datasets`.

API routes + the audit runner never import `phoenix.client.AsyncClient`
directly. They depend on `PhoenixDatasetClient` (Protocol). The production
impl `PhoenixDatasetClientImpl` calls the SDK; the test fake
`FakePhoenixDatasetClient` (in tests/unit/storage/fakes.py) implements the
same Protocol so the unit suite is offline by construction.

Flat-row contract: our code passes a list of `FlatDatasetItem`-shaped
mappings (the columns the operator sees — `case_id / prompt / fault_class /
expected / source / severity / notes`). The wrapper VALIDATES each row and
slices it into the pre-bucketed `{input, output, metadata}` example shape the
SDK's `examples=` parameter requires (the `*_keys` kwargs apply only to the
dataframe/CSV ingestion paths). The buckets never leak out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, ConfigDict, Field

_HTTP_NOT_FOUND = 404

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

    async def get_current_version_id(self, phoenix_dataset_id: str) -> str:
        """Return the Phoenix `version_id` of the dataset's current version.
        The audit finalize path snapshots this onto the RunRecord so the
        signed report cover pins evidence to a specific Phoenix version
        (H-NEW-2). Raises the same error families as `get_examples`."""
        ...

    async def delete(self, phoenix_dataset_id: str) -> None:
        """Delete the Phoenix dataset. Best-effort: a NotFound is treated
        as already-deleted (the Firestore index row is what hides the
        dataset from the user anyway)."""
        ...


def _normalize_row(row: dict[str, Any] | FlatDatasetItem) -> dict[str, Any]:
    """Coerce either input shape into a flat dict."""
    if isinstance(row, FlatDatasetItem):
        return row.model_dump()
    return dict(row)


def _bucket_row(row: dict[str, Any] | FlatDatasetItem) -> dict[str, dict[str, Any]]:
    """Validate a flat row, then slice it into the SDK's pre-bucketed shape.

    The SDK's `examples=` parameter REQUIRES `{input, output, metadata}`
    dicts — the `input_keys`/`output_keys`/`metadata_keys` kwargs apply only
    to the dataframe/CSV ingestion paths. Passing flat rows raised
    ValueError on the first real call (staging seed, 2026-06-11); the fake
    had accepted the flat shape, masking it.

    Validation is write-time ON PURPOSE (PR #118 HIGH-1): an invalid row
    (e.g. a regression row missing `prompt`) must fail HERE, loudly, not
    write `None` into Phoenix and detonate every later read of the dataset
    as an unpartitioned ValidationError."""
    flat = FlatDatasetItem.model_validate(_normalize_row(row)).model_dump()
    return {
        "input": {k: flat.get(k) for k in _INPUT_KEYS},
        "output": {k: flat.get(k) for k in _OUTPUT_KEYS},
        "metadata": {k: flat.get(k) for k in _METADATA_KEYS},
    }


async def _partition_sdk_call(phoenix_dataset_id: str, coro: Any) -> Any:
    """Round-4 HIGH-2: uniform error partitioning for every SDK call. Every
    `PhoenixDatasetClientImpl` method routes through here so 404 always
    becomes `PhoenixDatasetNotFoundError` and other-HTTP/Network always
    becomes `PhoenixUnavailableError`. Without this, `create()` and
    `add_examples()` leaked raw `httpx.HTTPStatusError` to the caller,
    making the contained-finalize path's bridge-drift catch unreachable
    in production (it only fired in tests that used the fake)."""
    try:
        return await coro
    except httpx.HTTPStatusError as e:
        # Round-5 LOW-2: defensive — every well-formed HTTPStatusError carries
        # `.response`, but a malformed instance shouldn't crash us into the
        # wrong typed error.
        response = getattr(e, "response", None)
        status_code = response.status_code if response is not None else None
        if status_code == _HTTP_NOT_FOUND:
            raise PhoenixDatasetNotFoundError(phoenix_dataset_id) from e
        raise PhoenixUnavailableError(str(e)) from e
    except (httpx.HTTPError, TimeoutError) as e:
        # Round-5 MED-1: broadened from RequestError to the httpx.HTTPError
        # base class so sibling families (InvalidURL, CookieConflict,
        # StreamError) also surface as a typed PhoenixUnavailableError
        # instead of escaping the wrapper as raw httpx exceptions.
        raise PhoenixUnavailableError(str(e)) from e


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
        rows = [_bucket_row(r) for r in examples]
        # `source_url` is appended to the description for now — Phoenix's
        # Dataset has a description field but no native source_url. The
        # Firestore index carries the canonical source_url.
        full_desc = description or ""
        if source_url:
            full_desc = f"{full_desc}\nSource: {source_url}".strip()
        # Uniform partitioning per `_partition_sdk_call` — create() now
        # raises typed errors instead of leaking httpx.HTTPStatusError.
        ds = await _partition_sdk_call(
            "<create>",
            self._client().datasets.create_dataset(
                name=name,
                examples=rows,
                dataset_description=full_desc or None,
            ),
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
        rows = [_bucket_row(r) for r in examples]
        # Uniform partitioning: a stale `phoenix_dataset_id` (the bridge-
        # drift case) now raises `PhoenixDatasetNotFoundError`, making the
        # `try_regression_upsert` bridge_drift log event reachable in prod.
        ds = await _partition_sdk_call(
            phoenix_dataset_id,
            self._client().datasets.add_examples_to_dataset(
                dataset=phoenix_dataset_id,
                examples=rows,
            ),
        )
        return ds.version_id  # type: ignore[no-any-return]

    async def get_examples(self, phoenix_dataset_id: str) -> list[FlatDatasetItem]:
        # Uniform partitioning via `_partition_sdk_call` (round-4 HIGH-2).
        # Programming bugs (AttributeError / TypeError) surface naturally.
        ds = await _partition_sdk_call(
            phoenix_dataset_id,
            self._client().datasets.get_dataset(dataset=phoenix_dataset_id),
        )
        return [_flat_from_example(ex) for ex in ds.examples]

    async def get_current_version_id(self, phoenix_dataset_id: str) -> str:
        """Read the current `version_id` off the SDK's `Dataset` object."""
        ds = await _partition_sdk_call(
            phoenix_dataset_id,
            self._client().datasets.get_dataset(dataset=phoenix_dataset_id),
        )
        # `Dataset.version_id` is the canonical wire field per the SDK.
        # Round-3 LOW: defensive str-coerce + non-empty check so an SDK
        # shape drift (returning None / int) raises a typed error here
        # instead of corrupting the downstream Pydantic str field.
        version_id = ds.version_id
        if not isinstance(version_id, str) or not version_id:
            msg = (
                f"Phoenix SDK returned non-string version_id "
                f"for {phoenix_dataset_id}: {version_id!r}"
            )
            raise PhoenixUnavailableError(msg)
        return version_id

    async def delete(self, phoenix_dataset_id: str) -> None:
        # H4 (review-fleet): the SDK doesn't yet expose dataset delete in
        # v1.x. Raise NotImplementedError so the route's best-effort catch
        # logs the no-op explicitly — silently returning would let an
        # operator believe the Phoenix-side row was removed.
        msg = (
            f"Phoenix dataset delete not implemented in SDK v1; index row removed "
            f"but Phoenix dataset {phoenix_dataset_id} persists"
        )
        raise NotImplementedError(msg)


__all__ = [
    "CreatedDataset",
    "FlatDatasetItem",
    "PhoenixDatasetClient",
    "PhoenixDatasetClientImpl",
    "PhoenixDatasetError",
    "PhoenixDatasetNotFoundError",
    "PhoenixUnavailableError",
]
