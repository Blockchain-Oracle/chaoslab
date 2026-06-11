"""Story-9.15 — `/datasets` router.

Routes:
- `GET  /datasets`            — listing scoped to the caller (battery + owned)
- `GET  /datasets/{slug}`     — detail (index + Phoenix-side items); 503 on
                                Phoenix outage with index in the body
- `POST /datasets`            — upload JSONL/CSV → Phoenix dataset + index row
- `DELETE /datasets/{slug}`   — uploaded only (204); battery/regression → 409

All routes carry `require_user`. Foreign datasets surface as 404 — never 403 —
so existence doesn't leak (story-9.15 BDD).

The `PhoenixDatasetClient` is module-globaled via `set_phoenix_client` so
tests swap the fake in. The store seam is `storage.datasets.set_dataset_index_store`.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from phoenix_audit_agent._time import utc_now_iso
from phoenix_audit_agent.api.auth import AuthedUser, require_user
from phoenix_audit_agent.api.datasets_validation import (
    UploadValidationError,
    parse_and_validate,
)
from phoenix_audit_agent.phoenix_tools.dataset_client import (
    PhoenixDatasetClient,
    PhoenixDatasetClientImpl,
    PhoenixUnavailableError,
)
from phoenix_audit_agent.storage.datasets import get_dataset_index_store
from phoenix_audit_agent.storage.models import DatasetIndex, DatasetKind

router = APIRouter()


# --- module-level PhoenixDatasetClient seam ---------------------------------

_PHX_CLIENT: PhoenixDatasetClient | None = None


def set_phoenix_client(client: PhoenixDatasetClient | None) -> None:
    """Test/bootstrap seam. `None` resets to the lazy SDK-backed default."""
    global _PHX_CLIENT  # noqa: PLW0603 — module singleton is the documented seam
    _PHX_CLIENT = client


def get_phoenix_client() -> PhoenixDatasetClient:
    global _PHX_CLIENT  # noqa: PLW0603 — module singleton is the documented seam
    if _PHX_CLIENT is None:
        _PHX_CLIENT = PhoenixDatasetClientImpl()
    return _PHX_CLIENT


# --- response shapes --------------------------------------------------------


class DatasetListRow(BaseModel):
    """Listing wire shape — Phoenix-side ids are intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    name: str
    kind: DatasetKind
    row_count: int
    source_url: str | None
    agent_id: str | None
    created_at: str
    updated_at: str


class DatasetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasets: list[DatasetListRow]


class DatasetItemDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    prompt: str
    fault_class: str
    expected: str
    source: str
    severity: str | None = None
    notes: str | None = None


class DatasetDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    name: str
    kind: DatasetKind
    row_count: int
    source_url: str | None
    agent_id: str | None
    created_at: str
    updated_at: str
    items: list[DatasetItemDto]


class DatasetUnavailableResponse(BaseModel):
    """503 body for the Phoenix-outage path. Carries the index so the page
    can still render a header."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    name: str
    kind: DatasetKind
    row_count: int
    source_url: str | None
    agent_id: str | None
    created_at: str
    updated_at: str
    reason: str


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    format: Literal["jsonl", "csv"]
    body: str = Field(min_length=1, description="base64-encoded raw bytes")


# --- helpers ----------------------------------------------------------------


def _to_list_row(idx: DatasetIndex) -> DatasetListRow:
    return DatasetListRow(
        dataset_id=idx.dataset_id,
        name=idx.name,
        kind=idx.kind,
        row_count=idx.row_count,
        source_url=idx.source_url,
        agent_id=idx.agent_id,
        created_at=idx.created_at,
        updated_at=idx.updated_at,
    )


def _new_uploaded_slug() -> str:
    # 8 hex chars: 32 bits, far below the slug-collision risk threshold for
    # per-user upload counts. Slug format pinned by DatasetIndex regex.
    return "ds_" + secrets.token_hex(4)


def _can_see(idx: DatasetIndex, uid: str) -> bool:
    return idx.kind == "battery" or idx.owner_uid == uid


def _upload_error_response(err: UploadValidationError) -> dict[str, object]:
    return {
        "parse_error": err.parse_error,
        "row_errors": [{"row": r.row, "reason": r.reason} for r in err.row_errors],
    }


# --- routes -----------------------------------------------------------------


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    user: Annotated[AuthedUser, Depends(require_user)],
) -> DatasetListResponse:
    store = get_dataset_index_store()
    rows = await store.list_visible(user.uid)
    return DatasetListResponse(datasets=[_to_list_row(r) for r in rows])


@router.get("/datasets/{slug}")
async def get_dataset(
    slug: str,
    user: Annotated[AuthedUser, Depends(require_user)],
):
    store = get_dataset_index_store()
    idx = await store.get_by_slug(slug)
    if idx is None or not _can_see(idx, user.uid):
        # 404 — NEVER 403 — so existence does not leak.
        raise HTTPException(status_code=404, detail="dataset not found")
    try:
        items = await get_phoenix_client().get_examples(idx.phoenix_dataset_id)
    except PhoenixUnavailableError:
        # Render the index header + a banner client-side; the page must not 500.
        from fastapi.responses import JSONResponse

        body = DatasetUnavailableResponse(
            dataset_id=idx.dataset_id,
            name=idx.name,
            kind=idx.kind,
            row_count=idx.row_count,
            source_url=idx.source_url,
            agent_id=idx.agent_id,
            created_at=idx.created_at,
            updated_at=idx.updated_at,
            reason="dataset rows temporarily unavailable",
        )
        return JSONResponse(status_code=503, content=body.model_dump())
    return DatasetDetailResponse(
        dataset_id=idx.dataset_id,
        name=idx.name,
        kind=idx.kind,
        row_count=idx.row_count,
        source_url=idx.source_url,
        agent_id=idx.agent_id,
        created_at=idx.created_at,
        updated_at=idx.updated_at,
        items=[DatasetItemDto.model_validate(i.model_dump()) for i in items],
    )


@router.post("/datasets", status_code=status.HTTP_201_CREATED, response_model=DatasetListRow)
async def upload_dataset(
    payload: UploadRequest,
    user: Annotated[AuthedUser, Depends(require_user)],
):
    items, err = parse_and_validate(payload.body.encode("ascii"), body_format=payload.format)
    if err is not None:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content=_upload_error_response(err))
    assert items is not None

    created = await get_phoenix_client().create(
        name=payload.name,
        examples=items,
        description=None,
        source_url=None,
    )
    slug = _new_uploaded_slug()
    now = utc_now_iso()
    idx = DatasetIndex(
        dataset_id=slug,
        phoenix_dataset_id=created.phoenix_dataset_id,
        name=payload.name,
        kind="uploaded",
        owner_uid=user.uid,
        agent_id=None,
        row_count=created.example_count,
        source_url=None,
        content_hash=f"sha256:upload:{slug}",
        created_at=now,
        updated_at=now,
    )
    await get_dataset_index_store().upsert(idx)
    return _to_list_row(idx)


@router.delete("/datasets/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    slug: str,
    user: Annotated[AuthedUser, Depends(require_user)],
) -> None:
    store = get_dataset_index_store()
    idx = await store.get_by_slug(slug)
    if idx is None or not _can_see(idx, user.uid):
        raise HTTPException(status_code=404, detail="dataset not found")
    if idx.kind == "battery":
        raise HTTPException(status_code=409, detail="battery datasets are read-only")
    if idx.kind == "regression":
        raise HTTPException(
            status_code=409,
            detail="regression datasets are managed by the system — delete the agent to remove",
        )
    # Uploaded — best-effort Phoenix delete, authoritative Firestore delete.
    # Phoenix outage must not block the index delete (the index is what hides
    # the dataset from the user). Log + continue.
    try:
        await get_phoenix_client().delete(idx.phoenix_dataset_id)
    except Exception as e:
        import structlog

        structlog.get_logger(__name__).warning(
            "datasets.phoenix_delete_failed",
            slug=slug,
            phoenix_dataset_id=idx.phoenix_dataset_id,
            error=str(e),
        )
    await store.delete_by_slug(slug)


__all__ = ["get_phoenix_client", "router", "set_phoenix_client"]
