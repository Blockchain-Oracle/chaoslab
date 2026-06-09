"""Renders a HardeningRecipe to Markdown, uploads to GCS, returns a signed URL."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import HardeningRecipe

if TYPE_CHECKING:
    from google.cloud import storage

logger = logging.getLogger(__name__)


class EmitResult(BaseModel):
    """Outcome of uploading the rendered recipe to GCS."""

    model_config = ConfigDict(frozen=True)

    recipe_id: str
    # gs://<bucket>/<recipe_id>.md — the canonical artifact location.
    gcs_uri: str = Field(pattern=r"^gs://[a-z0-9][a-z0-9._-]*/.+\.md$")
    # Long-lived signed URL; pydantic.HttpUrl rejects v4 GCS URLs (>2083 chars)
    # so we validate with a prefix guard at the model boundary.
    signed_url: str = Field(min_length=1)
    markdown_bytes: int = Field(ge=1)
    ttl_seconds: int = Field(ge=1)

    @classmethod
    def build(
        cls,
        *,
        recipe_id: str,
        gcs_uri: str,
        signed_url: str,
        markdown_bytes: int,
        ttl_seconds: int,
    ) -> EmitResult:
        if not signed_url.startswith("https://"):
            msg = f"signed_url must be https:// (got {signed_url[:32]}...)"
            raise ValueError(msg)
        return cls(
            recipe_id=recipe_id,
            gcs_uri=gcs_uri,
            signed_url=signed_url,
            markdown_bytes=markdown_bytes,
            ttl_seconds=ttl_seconds,
        )


class MarkdownEmitter:
    """Renders a HardeningRecipe to Markdown, uploads to GCS, returns a signed URL."""

    def __init__(self, storage_client: Any | None = None) -> None:
        settings = get_settings()
        self._bucket_name = settings.GCS_RECIPES_BUCKET
        self._ttl = timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS)
        self._client = storage_client or _build_default_client()

    async def emit(self, recipe: HardeningRecipe) -> EmitResult:
        markdown = render_recipe(recipe)
        markdown_bytes = markdown.encode("utf-8")
        blob_name = f"{recipe.recipe_id}.md"

        # google-cloud-storage is sync-only; offload to a thread so we don't
        # block the orchestrator event loop during the 200-500 ms upload.
        signed_url = await asyncio.to_thread(self._upload_and_sign, blob_name, markdown_bytes)

        gcs_uri = f"gs://{self._bucket_name}/{blob_name}"
        logger.info(
            "markdown_emitted recipe_id=%s gcs_uri=%s bytes=%d",
            recipe.recipe_id,
            gcs_uri,
            len(markdown_bytes),
        )
        return EmitResult.build(
            recipe_id=recipe.recipe_id,
            gcs_uri=gcs_uri,
            signed_url=signed_url,
            markdown_bytes=len(markdown_bytes),
            ttl_seconds=int(self._ttl.total_seconds()),
        )

    def _upload_and_sign(self, blob_name: str, content: bytes) -> str:
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type="text/markdown; charset=utf-8")
        return blob.generate_signed_url(
            version="v4",
            expiration=self._ttl,
            method="GET",
        )


def _build_default_client() -> storage.Client:
    # Lazy-import so unit tests that monkeypatch the emitter can avoid
    # google-cloud-storage's authentication probe at module import time.
    from google.cloud import storage

    return storage.Client()


__all__ = ["EmitResult", "MarkdownEmitter"]
