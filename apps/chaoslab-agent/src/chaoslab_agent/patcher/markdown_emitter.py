"""Renders a HardeningRecipe to Markdown, uploads to GCS, returns a signed URL."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import HardeningRecipe

if TYPE_CHECKING:
    from google.cloud import storage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed errors so an on-call engineer can grep Cloud Logging by exception
# class rather than parsing tracebacks.
# ---------------------------------------------------------------------------


class MarkdownEmitterError(RuntimeError):
    """Base class for Markdown-emitter failures."""


class RecipeAlreadyExistsError(MarkdownEmitterError):
    """A blob with this recipe_id is already in the bucket — refusing to clobber."""


class BucketNotConfiguredError(MarkdownEmitterError):
    """Configured GCS bucket missing or runtime SA lacks objectAdmin."""


# ---------------------------------------------------------------------------
# Narrow Protocol of the google-cloud-storage surface the emitter touches.
# Stops the test stub silently drifting from the SDK.
# ---------------------------------------------------------------------------


@runtime_checkable
class _Blob(Protocol):
    def upload_from_string(
        self, data: bytes, content_type: str, if_generation_match: int = ...
    ) -> None: ...

    def generate_signed_url(self, *, version: str, expiration: timedelta, method: str) -> str: ...


@runtime_checkable
class _Bucket(Protocol):
    def blob(self, name: str) -> _Blob: ...

    def exists(self) -> bool: ...


@runtime_checkable
class StorageClient(Protocol):
    def bucket(self, name: str) -> _Bucket: ...


class EmitResult(BaseModel):
    """Outcome of uploading the rendered recipe to GCS."""

    model_config = ConfigDict(frozen=True)

    recipe_id: str
    # gs://<bucket>/<recipe_id>.md
    gcs_uri: str = Field(pattern=r"^gs://[a-z0-9][a-z0-9._-]*/.+\.md$")
    # Plain str — v4 GCS signed URLs routinely exceed 2083 chars, which
    # pydantic.HttpUrl rejects. The field_validator below enforces the
    # https scheme + googleapis.com host on EVERY construction path,
    # not just the build-factory call site.
    signed_url: str = Field(min_length=1)
    markdown_bytes: int = Field(ge=1)
    ttl_seconds: int = Field(ge=1, le=604800)

    @field_validator("signed_url")
    @classmethod
    def _signed_url_is_https_googleapis(cls, value: str) -> str:
        if not value.startswith("https://"):
            msg = f"signed_url must be https:// (got {value[:32]}...)"
            raise ValueError(msg)
        # `storage.googleapis.com` covers both the per-bucket host
        # `<bucket>.storage.googleapis.com` and the global host.
        if "storage.googleapis.com" not in value:
            msg = "signed_url host must be storage.googleapis.com"
            raise ValueError(msg)
        return value


class MarkdownEmitter:
    """Renders a HardeningRecipe to Markdown, uploads to GCS, returns a signed URL."""

    def __init__(self, storage_client: StorageClient | None = None) -> None:
        settings = get_settings()
        self._bucket_name = settings.GCS_RECIPES_BUCKET
        self._ttl = timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS)
        # Defaults are deferred to construction time (not module import),
        # so unit tests that inject a stub don't trigger the GCS auth probe.
        self._client: StorageClient = storage_client or cast(StorageClient, _build_default_client())

    async def health_check(self) -> None:
        """Fail fast if the bucket is missing or the runtime SA can't reach it.

        Invoke at app startup so a misconfigured deploy raises before the
        first demo button-press instead of bubbling a raw NotFound.
        """
        await asyncio.to_thread(self._probe_bucket)

    async def emit(self, recipe: HardeningRecipe) -> EmitResult:
        markdown = render_recipe(recipe)
        markdown_bytes = markdown.encode("utf-8")
        blob_name = f"{recipe.recipe_id}.md"

        try:
            # google-cloud-storage is sync-only; offload to a thread so we
            # don't block the orchestrator event loop during the upload.
            signed_url = await asyncio.to_thread(self._upload_and_sign, blob_name, markdown_bytes)
        except RecipeAlreadyExistsError:
            raise
        except Exception as exc:
            logger.exception(
                "markdown_emit_failed recipe_id=%s bucket=%s",
                recipe.recipe_id,
                self._bucket_name,
            )
            msg = f"Markdown emit failed: {type(exc).__name__}: {exc}"
            raise MarkdownEmitterError(msg) from exc

        gcs_uri = f"gs://{self._bucket_name}/{blob_name}"
        logger.info(
            "markdown_emitted recipe_id=%s gcs_uri=%s bytes=%d",
            recipe.recipe_id,
            gcs_uri,
            len(markdown_bytes),
        )
        return EmitResult(
            recipe_id=recipe.recipe_id,
            gcs_uri=gcs_uri,
            signed_url=signed_url,
            markdown_bytes=len(markdown_bytes),
            ttl_seconds=int(self._ttl.total_seconds()),
        )

    def _probe_bucket(self) -> None:
        try:
            bucket = self._client.bucket(self._bucket_name)
            if not bucket.exists():
                msg = f"GCS bucket {self._bucket_name!r} does not exist"
                raise BucketNotConfiguredError(msg)
        except BucketNotConfiguredError:
            raise
        except Exception as exc:
            msg = (
                f"GCS bucket {self._bucket_name!r} unreachable "
                f"({type(exc).__name__}: {exc}) — check IAM/network"
            )
            raise BucketNotConfiguredError(msg) from exc

    def _upload_and_sign(self, blob_name: str, content: bytes) -> str:
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(blob_name)
        # if_generation_match=0 = "create only"; clobbering a previous
        # recipe_id (cosmically unlikely at 2^48 but trivial to retry-bug)
        # would silently swap signed-URL content. Refuse instead.
        try:
            blob.upload_from_string(
                content,
                content_type="text/markdown; charset=utf-8",
                if_generation_match=0,
            )
        except Exception as exc:
            if _is_precondition_failed(exc):
                msg = f"recipe_id={blob_name} already exists in bucket"
                raise RecipeAlreadyExistsError(msg) from exc
            raise
        return blob.generate_signed_url(
            version="v4",
            expiration=self._ttl,
            method="GET",
        )


_HTTP_PRECONDITION_FAILED = 412


def _is_precondition_failed(exc: BaseException) -> bool:
    # google-api-core's typed PreconditionFailed / 412 surface depends on
    # the SDK version. Detect by class name to stay robust without
    # importing the exception type at module load.
    return type(exc).__name__ in {"PreconditionFailed", "Conflict"} or (
        hasattr(exc, "code") and getattr(exc, "code", None) == _HTTP_PRECONDITION_FAILED
    )


def _build_default_client() -> storage.Client:
    # Deferred-import so test stubs avoid google-cloud-storage's auth
    # probe entirely; the import only runs when a real client is needed.
    from google.cloud import storage

    return storage.Client()


__all__ = [
    "BucketNotConfiguredError",
    "EmitResult",
    "MarkdownEmitter",
    "MarkdownEmitterError",
    "RecipeAlreadyExistsError",
    "StorageClient",
]
