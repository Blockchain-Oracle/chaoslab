"""Unit tests for MarkdownEmitter — stubs the GCS boundary."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from chaoslab_agent.config import get_settings
from chaoslab_agent.judge.clustering import FailureClusterSet
from chaoslab_agent.patcher.markdown_emitter import EmitResult, MarkdownEmitter
from chaoslab_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
)


@pytest.fixture(autouse=True)
def _vertex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    get_settings.cache_clear()


def _recipe() -> HardeningRecipe:
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="no input validation",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    return HardeningRecipe(
        recipe_id="recipe_abc123def456",
        target_agent_id="target_customer_support",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=[],
        tool_validation_diffs=[],
        regression_test_cases=[],
        estimated_resilience_improvement=0.46,
    )


class _RecordingBlob:
    def __init__(self) -> None:
        self.uploaded: tuple[bytes, str] | None = None
        self.signed_args: dict[str, Any] = {}

    def upload_from_string(self, content: bytes, content_type: str) -> None:
        self.uploaded = (content, content_type)

    def generate_signed_url(
        self,
        *,
        version: str,
        expiration: timedelta,
        method: str,
    ) -> str:
        self.signed_args = {
            "version": version,
            "expiration": expiration,
            "method": method,
        }
        return (
            "https://storage.googleapis.com/chaoslab-recipes/recipe_abc123def456.md"
            "?X-Goog-Algorithm=GOOG4-RSA-SHA256"
            "&X-Goog-Credential=fake-sa%40chaoslab.iam.gserviceaccount.com"
            "&X-Goog-Date=20260609T000000Z"
            f"&X-Goog-Expires={int(expiration.total_seconds())}"
            "&X-Goog-SignedHeaders=host"
            "&X-Goog-Signature=deadbeef"
        )


class _RecordingBucket:
    def __init__(self, blob: _RecordingBlob) -> None:
        self._blob = blob
        self.blob_names: list[str] = []

    def blob(self, name: str) -> _RecordingBlob:
        self.blob_names.append(name)
        return self._blob


class _RecordingClient:
    def __init__(self) -> None:
        self.blob = _RecordingBlob()
        self.bucket_obj = _RecordingBucket(self.blob)
        self.bucket_names: list[str] = []

    def bucket(self, name: str) -> _RecordingBucket:
        self.bucket_names.append(name)
        return self.bucket_obj


async def test_emit_uploads_to_gcs_with_correct_uri() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert isinstance(result, EmitResult)
    assert result.gcs_uri == "gs://chaoslab-recipes/recipe_abc123def456.md"
    assert client.bucket_names == ["chaoslab-recipes"]
    assert client.bucket_obj.blob_names == ["recipe_abc123def456.md"]


async def test_emit_uploads_with_markdown_content_type() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    uploaded = client.blob.uploaded
    assert uploaded is not None
    content, content_type = uploaded
    assert content_type == "text/markdown; charset=utf-8"
    assert content.startswith(b"# ChaosLab Hardening Recipe")


async def test_emit_returns_signed_url_with_expected_query_params() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert result.signed_url.startswith("https://")
    assert "X-Goog-Signature" in result.signed_url
    assert "X-Goog-Algorithm" in result.signed_url


async def test_emit_ttl_seconds_match_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GCS_SIGNED_URL_TTL_DAYS", "7")
    get_settings.cache_clear()
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert result.ttl_seconds == 7 * 86400
    assert client.blob.signed_args["expiration"] == timedelta(days=7)


async def test_emit_passes_v4_signing_version() -> None:
    client = _RecordingClient()
    await MarkdownEmitter(storage_client=client).emit(_recipe())
    assert client.blob.signed_args["version"] == "v4"
    assert client.blob.signed_args["method"] == "GET"


async def test_emit_markdown_bytes_count_matches_content() -> None:
    client = _RecordingClient()
    result = await MarkdownEmitter(storage_client=client).emit(_recipe())
    uploaded = client.blob.uploaded
    assert uploaded is not None
    assert result.markdown_bytes == len(uploaded[0])


async def test_emit_result_rejects_non_https_signed_url() -> None:
    class _BadClient:
        def bucket(self, name: str) -> Any:
            class _BadBlob:
                def upload_from_string(self, content: bytes, content_type: str) -> None:
                    return None

                def generate_signed_url(self, **kwargs: Any) -> str:
                    return "http://insecure.example/recipe.md"

            class _BadBucket:
                def blob(self, name: str) -> Any:
                    return _BadBlob()

            return _BadBucket()

    with pytest.raises(ValueError, match="https://"):
        await MarkdownEmitter(storage_client=_BadClient()).emit(_recipe())
