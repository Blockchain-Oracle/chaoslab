"""Renders a HardeningRecipe to Markdown, uploads to GCS, returns a signed URL."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Protocol, cast, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.errors import PhoenixAuditError
from phoenix_audit_agent.patcher._markdown_renderer import render_recipe
from phoenix_audit_agent.patcher.recipe import HardeningRecipe
from phoenix_audit_agent.storage.gcs import get_storage_client, signed_get_url

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed errors so an on-call engineer can grep Cloud Logging by exception
# class rather than parsing tracebacks.
# ---------------------------------------------------------------------------


class MarkdownEmitterError(PhoenixAuditError, RuntimeError):
    """Base class for Markdown-emitter failures."""


class RecipeAlreadyExistsError(MarkdownEmitterError):
    """A blob with this recipe_id is already in the bucket — refusing to clobber."""


class BucketProbeError(MarkdownEmitterError):
    """Bucket probe failed for any reason. Catch this when you want to
    handle 'something is wrong with the bucket' generically; catch the
    subclasses below when the operator response differs (config fix vs
    transient retry)."""


class BucketMissingError(BucketProbeError):
    """Configured GCS bucket does not exist in the deployed project. The
    operator response is a terraform / Secret Manager config change."""


class BucketUnreachableError(BucketProbeError):
    """Bucket exists but credentials, IAM, or network prevented the probe.
    The operator response is checking IAM bindings or retry — often
    transient, distinct from BucketMissingError to avoid masking flaky
    IAM as a config bug."""


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
        self._client: StorageClient = storage_client or cast(StorageClient, get_storage_client())

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
        # Story-9.17 sidecar: the STRUCTURED recipe, so the review-first MR
        # endpoint can rehydrate it after the run. Contained — a sidecar
        # failure only disables MR filing for this run (disclosed via the
        # endpoint's 409), never fails the audit.
        try:
            await asyncio.to_thread(
                self._upload_sidecar,
                f"{recipe.recipe_id}.json",
                recipe.model_dump_json(indent=2).encode("utf-8"),
            )
        except Exception:
            logger.exception(
                "recipe_json_sidecar_failed recipe_id=%s — MR filing will 409 for this run",
                recipe.recipe_id,
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
            exists = bucket.exists()
        except Exception as exc:
            msg = (
                f"GCS bucket {self._bucket_name!r} unreachable "
                f"({type(exc).__name__}: {exc}) — check IAM/network"
            )
            raise BucketUnreachableError(msg) from exc
        if not exists:
            msg = f"GCS bucket {self._bucket_name!r} does not exist"
            raise BucketMissingError(msg)

    def _upload_sidecar(self, blob_name: str, content: bytes) -> None:
        """Plain upload, no signing, clobber-tolerant — the sidecar mirrors
        whatever recipe the run last produced."""
        bucket = self._client.bucket(self._bucket_name)
        bucket.blob(blob_name).upload_from_string(content, content_type="application/json")

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
            if _is_already_exists_error(exc):
                msg = f"recipe_id={blob_name} already exists in bucket"
                raise RecipeAlreadyExistsError(msg) from exc
            raise
        # Use the shared helper — it transparently routes Cloud Run's
        # token-only compute-engine credentials through IAM signBlob so a
        # raw generate_signed_url AttributeError never reaches prod again
        # (project_iam_gotcha_gcs). reporter/emitter.py + api/runs.py
        # already use this helper; markdown_emitter was the lone holdout.
        return signed_get_url(blob, ttl=self._ttl)


# google-api-core signals "this blob already exists" across versions / transports
# in several incompatible shapes. We treat ALL of these as the same semantic:
#   - HTTP REST: PreconditionFailed (412) on if_generation_match=0; Conflict (409)
#     on older variants.
#   - gRPC: FailedPrecondition (class name) with grpc.StatusCode.FAILED_PRECONDITION
#     (status enum). Some SDK versions stringify status codes as "412 Precondition
#     Failed" on `.code`.
_ALREADY_EXISTS_CLASS_NAMES = frozenset({"PreconditionFailed", "Conflict", "FailedPrecondition"})
_ALREADY_EXISTS_HTTP_CODES = frozenset({409, 412})
_ALREADY_EXISTS_GRPC_NAMES = frozenset({"FAILED_PRECONDITION", "ALREADY_EXISTS"})


def _is_already_exists_error(exc: BaseException) -> bool:
    """Match SDK variants of 'this blob already exists' precondition signaling.

    The function answers 'should we raise RecipeAlreadyExistsError?' — NOT
    'is this a 412'. Either an HTTP precondition failure OR a gRPC
    FailedPrecondition OR a 409 Conflict means the recipe_id is already
    taken under if_generation_match=0 semantics.
    """
    if type(exc).__name__ in _ALREADY_EXISTS_CLASS_NAMES:
        return True
    response = getattr(exc, "response", None)
    for candidate in (
        getattr(exc, "code", None),
        getattr(exc, "status_code", None),
        getattr(response, "status_code", None),
        getattr(exc, "grpc_status_code", None),
    ):
        if isinstance(candidate, int) and candidate in _ALREADY_EXISTS_HTTP_CODES:
            return True
        if isinstance(candidate, str):
            # Some SDKs format codes as "412 Precondition Failed" instead of bare int.
            head = candidate.strip().split(maxsplit=1)[0] if candidate.strip() else ""
            if head.isdigit() and int(head) in _ALREADY_EXISTS_HTTP_CODES:
                return True
        # grpc.StatusCode enum: has .name like "FAILED_PRECONDITION" / "ALREADY_EXISTS".
        name = getattr(candidate, "name", None)
        if isinstance(name, str) and name in _ALREADY_EXISTS_GRPC_NAMES:
            return True
    return False


__all__ = [
    "BucketMissingError",
    "BucketProbeError",
    "BucketUnreachableError",
    "EmitResult",
    "MarkdownEmitter",
    "MarkdownEmitterError",
    "RecipeAlreadyExistsError",
    "StorageClient",
]
