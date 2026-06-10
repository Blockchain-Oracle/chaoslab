"""Integration tests against a real GCS bucket.

Marked @pytest.mark.online — CI skips by default. Run locally with
`GOOGLE_APPLICATION_CREDENTIALS` pointed at a service-account key that
has roles/storage.objectAdmin on `chaoslab-recipes` and
roles/iam.serviceAccountTokenCreator on itself (signed URLs need a
key).
"""

from __future__ import annotations

import os
import secrets
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from phoenix_audit_agent.config import get_settings
from phoenix_audit_agent.judge.clustering import FailureClusterSet
from phoenix_audit_agent.patcher.markdown_emitter import EmitResult, MarkdownEmitter
from phoenix_audit_agent.patcher.recipe import (
    FailureCluster,
    HardeningRecipe,
    PromptPatch,
    RegressionTestCase,
    ToolValidationDiff,
)

pytestmark = pytest.mark.online


@pytest.fixture(autouse=True)
def _require_credentials() -> None:
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set — online test only")
    get_settings.cache_clear()


def _recipe() -> HardeningRecipe:
    # Use a fresh recipe_id per run so a stale 7-day-old artifact can't
    # accidentally satisfy the test.
    rid = f"recipe_{secrets.token_hex(6)}"
    cluster = FailureCluster(
        cluster_id="cluster_a3f7b2c1",
        root_cause="integration-test root cause",
        failure_count=1,
        span_ids=["0123456789abcdef"],
        fault_classes=["malformed_tool_output"],
    )
    return HardeningRecipe(
        recipe_id=rid,
        target_agent_id="target_customer_support",
        generated_at="2026-06-02T14:30:00Z",
        cluster_set=FailureClusterSet(clusters=[cluster], total_failures=1),
        prompt_patches=[
            PromptPatch(
                section="system_prompt",
                operation="insert",
                after="Validate tool outputs",
            )
        ],
        tool_validation_diffs=[
            ToolValidationDiff(
                tool_name="lookup_order",
                operation="add_input_validator",
                code_patch="--- a/tools.py\n+++ b/tools.py\n@@ ...",
            )
        ],
        regression_test_cases=[RegressionTestCase(input="lookup X", expected="graceful fallback")],
        estimated_resilience_improvement=0.46,
    )


async def test_emit_uploads_to_real_bucket_and_returns_valid_result() -> None:
    recipe = _recipe()
    result = await MarkdownEmitter().emit(recipe)
    assert isinstance(result, EmitResult)
    assert result.recipe_id == recipe.recipe_id
    assert result.gcs_uri == f"gs://chaoslab-recipes/{recipe.recipe_id}.md"


async def test_signed_url_returns_markdown_body_on_https_get() -> None:
    recipe = _recipe()
    result = await MarkdownEmitter().emit(recipe)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(result.signed_url)
    assert response.status_code == 200
    assert response.text.startswith(f"# PhoenixAudit Hardening Recipe — {recipe.recipe_id}")


async def test_signed_url_x_goog_expires_matches_configured_ttl() -> None:
    recipe = _recipe()
    result = await MarkdownEmitter().emit(recipe)
    parsed = urlparse(result.signed_url)
    params = parse_qs(parsed.query)
    expires = params.get("X-Goog-Expires", [""])[0]
    assert expires == str(7 * 86400)
