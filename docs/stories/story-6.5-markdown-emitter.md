# Story — Markdown Emitter (HardeningRecipe → GCS Markdown + signed URL)

**ID:** story-6.5-markdown-emitter
**Epic:** Epic 6 — Judge + clustering + hardening recipe
**Depends on:** story-6.4-patcher-sub-agent (consumes `HardeningRecipe`)
**Estimate:** ~1.5h
**Status:** PENDING
**tags:** [backend, p0, patcher]

---

## User story

**As a** ChaosLab Receipt card (frontend, `chaoslab-web/_components/receipt-card.tsx`) that needs to surface a clickable link to the hardening recipe at the end of the demo
**I want to** call `MarkdownEmitter.emit(recipe)` and receive `{markdown_url: "https://storage.googleapis.com/...?X-Goog-Signature=..."}` pointing to a rendered Markdown artifact in GCS bucket `chaoslab-recipes/<recipe_id>.md`, valid for 7 days (so judges can re-open the demo link during the 4-week judging window)
**So that** the demo's Receipt card has a real artifact URL judges can click, the Markdown is human-readable (per `architecture/04 §6.3` shape), and the artifact persists beyond the 60-180s demo run window — per ADR-011 (Markdown emission is the always-on demo path; GitLab MR is the bonus partner-credit path)

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py` — NEW — defines `MarkdownEmitter` class with `async emit(recipe: HardeningRecipe) -> EmitResult` entry point. Renders Markdown, uploads to GCS, generates signed URL. ≤250 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py` — NEW — pure-function `render_recipe(recipe: HardeningRecipe) -> str` that returns the Markdown string (no I/O). Sections: Summary, Root Causes, Prompt Patches (code blocks), Tool Validation Diffs (unified-diff code blocks), Regression Test Cases, Estimated Improvement. ≤200 LOC.
- `apps/chaoslab-agent/src/chaoslab_agent/patcher/__init__.py` — UPDATE — append `from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitter, EmitResult`
- `apps/chaoslab-agent/src/chaoslab_agent/config.py` — UPDATE — append `GCS_RECIPES_BUCKET: str = "chaoslab-recipes"` and `GCS_SIGNED_URL_TTL_DAYS: int = 7` to `Settings`
- `apps/chaoslab-agent/pyproject.toml` — UPDATE — append `google-cloud-storage` dep (`uv add google-cloud-storage`)
- `apps/chaoslab-agent/tests/unit/patcher/test_markdown_renderer.py` — NEW — ≥10 behavioral tests on the pure `render_recipe` function: every recipe section appears in the output, code blocks are properly fenced, unified-diff blocks use ```diff fence, recipe_id appears in header, estimated_resilience_improvement is formatted as percentage
- `apps/chaoslab-agent/tests/integration/test_markdown_emitter_gcs.py` — NEW — ≥3 integration tests against a real GCS bucket (marked `@pytest.mark.online`); CI skips by default. Uploads a real recipe, fetches signed URL, asserts HTTPS GET returns the Markdown content.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

````
Given apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py exists
When  `uv run python -c "from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitter, EmitResult; print('ok')"` runs
Then  stdout contains "ok" and exit code is 0

Given a HardeningRecipe with recipe_id="recipe_abc123def456" and 3 clusters
When  `render_recipe(recipe)` is called
Then  the returned string contains "recipe_abc123def456"
And   contains "## Summary"
And   contains "## Root Causes"
And   contains "## Prompt Patches"
And   contains "## Tool Validation Diffs"
And   contains "## Regression Test Cases"
And   contains "## Estimated Resilience Improvement"

Given a HardeningRecipe with 2 PromptPatch entries
When  render_recipe(recipe) is called
Then  the output contains exactly 2 ``` fenced text code blocks under "## Prompt Patches"

Given a HardeningRecipe with 1 ToolValidationDiff entry
When  render_recipe(recipe) is called
Then  the output contains at least 1 ```diff fenced block under "## Tool Validation Diffs"
And   the block content includes the code_patch text byte-for-byte

Given a HardeningRecipe with estimated_resilience_improvement=0.467
When  render_recipe(recipe) is called
Then  the output contains "46.7%" (formatted as percentage)

Given a HardeningRecipe with cluster_set containing 3 FailureCluster entries
When  render_recipe(recipe) is called
Then  the output contains 3 occurrences of "cluster_" prefix (one per cluster)
And   each cluster's root_cause appears verbatim

Given the rendered Markdown is empty for an edge-case recipe with zero patches
When  render_recipe is called with recipe.prompt_patches == []
Then  the output contains "_(no prompt patches generated)_" under "## Prompt Patches"

Given a configured GCS client and a fully-populated HardeningRecipe with recipe_id="recipe_abc123def456"
When  `await MarkdownEmitter().emit(recipe)` runs
Then  result is an EmitResult instance
And   result.gcs_uri == "gs://chaoslab-recipes/recipe_abc123def456.md"
And   result.signed_url starts with "https://"
And   result.signed_url contains "X-Goog-Signature" or "X-Goog-Algorithm" query params
And   result.markdown_bytes > 0

Given the integration test uploads recipe_abc123def456.md to a real GCS bucket
When  the test performs HTTPS GET on result.signed_url
Then  the response status_code == 200
And   the response body starts with "# ChaosLab Hardening Recipe — recipe_abc123def456"

Given the signed URL TTL config is GCS_SIGNED_URL_TTL_DAYS=7
When  the signed URL is generated
Then  the URL's X-Goog-Expires parameter equals 604800 (7 * 86400 seconds)

Given `uv run pytest apps/chaoslab-agent/tests/unit/patcher/test_markdown_renderer.py -v` runs
When  the test suite completes
Then  ≥10 behavioral tests pass

Given `uv run pytest apps/chaoslab-agent/tests/integration/test_markdown_emitter_gcs.py -v -m online` runs (with GCP creds)
When  the test suite completes
Then  ≥3 integration tests pass

Given the markdown_emitter.py and _markdown_renderer.py source files
When  `python3 scripts/check_max_lines.py apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py` runs
Then  exit code is 0 (markdown_emitter.py ≤250 LOC, _markdown_renderer.py ≤200 LOC per task)

Given `grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py` runs
When  output is checked
Then  zero results appear (§14 gate clean)
````

---

## Shell verification

```bash
set -e
cd /Users/abu/dev/hackathon/rapid-agents

# Files exist
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py
test -f apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py
test -f apps/chaoslab-agent/tests/unit/patcher/test_markdown_renderer.py
test -f apps/chaoslab-agent/tests/integration/test_markdown_emitter_gcs.py

# Imports resolve
uv run python -c "from chaoslab_agent.patcher.markdown_emitter import MarkdownEmitter, EmitResult; from chaoslab_agent.patcher._markdown_renderer import render_recipe; print('ok')"

# Unit tests (renderer is pure — no GCS needed)
cd apps/chaoslab-agent && uv run pytest tests/unit/patcher/test_markdown_renderer.py -v 2>&1 | tee /tmp/md-renderer-test.log && cd -
PASS_COUNT=$(grep -E "PASSED" /tmp/md-renderer-test.log | wc -l | tr -d ' ')
[ "$PASS_COUNT" -ge 10 ] || { echo "expected ≥10 unit tests, got $PASS_COUNT"; exit 1; }

# Integration tests (online — only if GCP creds available)
if [ -n "$GCP_CREDS_AVAILABLE" ] || [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  cd apps/chaoslab-agent && uv run pytest tests/integration/test_markdown_emitter_gcs.py -v -m online 2>&1 | tee /tmp/md-emitter-int-test.log && cd -
  INT_PASS=$(grep -E "PASSED" /tmp/md-emitter-int-test.log | wc -l | tr -d ' ')
  [ "$INT_PASS" -ge 3 ] || { echo "expected ≥3 integration tests, got $INT_PASS"; exit 1; }
else
  echo "[skip] integration tests — set GOOGLE_APPLICATION_CREDENTIALS to run"
fi

# Lint + type-check + per-task LOC ceilings
uv run ruff check apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py
uv run ruff format --check apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py
uv run ty check apps/chaoslab-agent/src/chaoslab_agent/patcher/ || uv run mypy --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/
python3 scripts/check_max_lines.py --strict apps/chaoslab-agent/src/chaoslab_agent/patcher/

LOC_EMITTER=$(wc -l < apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py | tr -d ' ')
[ "$LOC_EMITTER" -le 250 ] || { echo "markdown_emitter.py has $LOC_EMITTER lines, exceeds 250 LOC ceiling"; exit 1; }
LOC_RENDERER=$(wc -l < apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py | tr -d ' ')
[ "$LOC_RENDERER" -le 200 ] || { echo "_markdown_renderer.py has $LOC_RENDERER lines, exceeds 200 LOC ceiling"; exit 1; }

# §14 clean
! grep -rE "(mock|fake|dummy|hardcoded|simulated)" apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py

echo "story-6.5 verification: PASS"
```

---

## Notes for coding agent

### `EmitResult` schema + `MarkdownEmitter` class shape

```python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/markdown_emitter.py
from __future__ import annotations
from datetime import timedelta
import asyncio

import structlog
from google.cloud import storage  # type: ignore[attr-defined]
from pydantic import BaseModel, Field, HttpUrl

from chaoslab_agent.config import get_settings
from chaoslab_agent.patcher._markdown_renderer import render_recipe
from chaoslab_agent.patcher.recipe import HardeningRecipe

log = structlog.get_logger(__name__)


class EmitResult(BaseModel):
    recipe_id: str
    gcs_uri: str = Field(pattern=r"^gs://[a-z0-9][a-z0-9._-]*/.+\.md$")
    signed_url: HttpUrl
    markdown_bytes: int = Field(ge=1)
    ttl_seconds: int = Field(ge=1)


class MarkdownEmitter:
    """Renders a HardeningRecipe to Markdown, uploads to GCS, returns signed URL."""

    def __init__(self, storage_client: storage.Client | None = None) -> None:
        settings = get_settings()
        self._bucket_name = settings.GCS_RECIPES_BUCKET
        self._ttl = timedelta(days=settings.GCS_SIGNED_URL_TTL_DAYS)
        self._client = storage_client or storage.Client()

    async def emit(self, recipe: HardeningRecipe) -> EmitResult:
        markdown = render_recipe(recipe)
        markdown_bytes = markdown.encode("utf-8")
        blob_name = f"{recipe.recipe_id}.md"

        # GCS SDK is sync; run in default executor to avoid blocking the event loop
        signed_url = await asyncio.to_thread(
            self._upload_and_sign, blob_name, markdown_bytes
        )

        log.info(
            "markdown_emitted",
            recipe_id=recipe.recipe_id,
            gcs_uri=f"gs://{self._bucket_name}/{blob_name}",
            bytes=len(markdown_bytes),
        )
        return EmitResult(
            recipe_id=recipe.recipe_id,
            gcs_uri=f"gs://{self._bucket_name}/{blob_name}",
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
```

### `render_recipe` pure-function shape

````python
# apps/chaoslab-agent/src/chaoslab_agent/patcher/_markdown_renderer.py
"""Pure-function Markdown rendering for HardeningRecipe. NO I/O.

Separated from markdown_emitter.py so unit tests run without GCS creds.
"""
from __future__ import annotations
from chaoslab_agent.patcher.recipe import HardeningRecipe


def render_recipe(recipe: HardeningRecipe) -> str:
    parts: list[str] = []
    parts.append(f"# ChaosLab Hardening Recipe — {recipe.recipe_id}\n")
    parts.append(f"**Target agent:** `{recipe.target_agent_id}`")
    parts.append(f"**Generated:** {recipe.generated_at}")
    parts.append(f"**Estimated resilience improvement:** {recipe.estimated_resilience_improvement * 100:.1f}%\n")

    parts.append("## Summary\n")
    parts.append(
        f"ChaosLab identified {len(recipe.cluster_set)} root cause(s) across "
        f"{sum(c.failure_count for c in recipe.cluster_set)} failed attack runs. "
        f"This recipe applies {len(recipe.prompt_patches)} prompt patch(es) and "
        f"{len(recipe.tool_validation_diffs)} tool validation diff(s).\n"
    )

    parts.append("## Root Causes\n")
    for c in recipe.cluster_set:
        parts.append(
            f"### {c.cluster_id}\n"
            f"- **Root cause:** {c.root_cause}\n"
            f"- **Failure count:** {c.failure_count}\n"
            f"- **Fault classes:** {', '.join(c.fault_classes)}\n"
            f"- **Affected span IDs:** `{', '.join(c.span_ids[:5])}`"
            f"{' ...' if len(c.span_ids) > 5 else ''}\n"
        )

    parts.append("## Prompt Patches\n")
    if not recipe.prompt_patches:
        parts.append("_(no prompt patches generated)_\n")
    for p in recipe.prompt_patches:
        parts.append(f"**Section:** `{p.section}` | **Operation:** `{p.operation}`\n")
        if p.before is not None:
            parts.append("Before:\n```text\n" + p.before + "\n```\n")
        parts.append("After:\n```text\n" + p.after + "\n```\n")

    parts.append("## Tool Validation Diffs\n")
    if not recipe.tool_validation_diffs:
        parts.append("_(no tool validation diffs generated)_\n")
    for d in recipe.tool_validation_diffs:
        parts.append(f"**Tool:** `{d.tool_name}` | **Operation:** `{d.operation}`\n")
        parts.append("```diff\n" + d.code_patch + "\n```\n")

    parts.append("## Regression Test Cases\n")
    if not recipe.regression_test_cases:
        parts.append("_(no regression test cases)_\n")
    for i, tc in enumerate(recipe.regression_test_cases, 1):
        parts.append(f"{i}. ```json\n{tc!r}\n```\n")

    parts.append("## Estimated Resilience Improvement\n")
    parts.append(f"**{recipe.estimated_resilience_improvement * 100:.1f}%** "
                 f"(based on cluster coverage × patch density heuristic; "
                 f"validated by re-attack phase in ChaosLab's closed loop)\n")

    return "\n".join(parts)
````

### Architecture context

- **ADR-011 (mandatory):** Markdown emission is the ALWAYS-ON demo path. GitLab MR (S6.6) is the optional partner-credit path. This story's path MUST work for every demo run, regardless of GitLab config — Markdown URL goes into the Receipt card always.
- **GCS signed URL TTL = 7 days:** judges may evaluate over 4 weeks but each link only needs to be valid within a "open after demo run" window. 7 days covers the typical judging cadence. If a judge bookmarks past day 7, they can re-run the demo to regenerate. Per ADR-011 fallback intent.
- **Bucket name `chaoslab-recipes`:** lives in the `chaoslab-prod` GCP project. Created during S1.4 (`infra/secret-manager-setup.sh` augmented to provision the bucket). Workload Identity Federation gives `chaoslab-agent` service account `roles/storage.objectAdmin` on this bucket only.
- **`v4` signed URLs:** the default `version="v4"` produces query-string-signed URLs with `X-Goog-Algorithm`, `X-Goog-Credential`, `X-Goog-Date`, `X-Goog-Expires`, `X-Goog-SignedHeaders`, `X-Goog-Signature`. v2 is deprecated. The BDD asserts on `X-Goog-Signature` or `X-Goog-Algorithm` presence.
- **Pure-function renderer + I/O wrapper split:** `_markdown_renderer.py` is pure — no GCS, no httpx, no env vars. This is the unit-testable surface (≥10 tests pass without creds). `markdown_emitter.py` is the I/O wrapper — integration-tested under `@pytest.mark.online`.
- **`asyncio.to_thread` for sync GCS calls:** the `google-cloud-storage` SDK is sync-only. Wrapping in `asyncio.to_thread` keeps the orchestrator's event loop responsive during the 200-500ms upload. Per `coding-standards.md` Python conventions ("prefer async-by-default for I/O").
- **`text/markdown; charset=utf-8` content-type:** judges clicking the signed URL get a rendered Markdown view if their browser has a Markdown viewer extension; otherwise the raw text downloads. Either way is acceptable.
- **§14 gate:** zero mocks. Unit tests for the renderer use real recipe instances (no fakes). Integration tests use a real GCS bucket (online-only).

### Test guidance

- **Renderer tests are pure:** no GCS, no env vars, no httpx. Construct a `HardeningRecipe` directly, call `render_recipe`, assert on string contents. Coverage: every section header appears, every cluster's `root_cause` text appears verbatim, code blocks are properly fenced.
- **Edge cases:** empty `prompt_patches`, empty `tool_validation_diffs`, empty `regression_test_cases` — each should render the `_(no ...)_` italic placeholder text, not crash.
- **Integration tests:** `@pytest.mark.online`. Skip in CI default. When run locally with `GOOGLE_APPLICATION_CREDENTIALS` set:
  1. Upload a real recipe
  2. `httpx.get(result.signed_url)` and assert 200 + body content match
  3. Verify signed URL expires after the TTL (use `parse_qs` on the URL to extract `X-Goog-Expires`, assert == 604800)
- **TTL test (unit-level, no GCS):** mock `storage.Client` only at the integration boundary; for unit-level TTL verification, instantiate `MarkdownEmitter()` with a real `storage_client` parameter that's a real `storage.Client()` pointed at a non-existent project; the `generate_signed_url` call still returns a URL even without bucket existence (it doesn't validate). Then parse the URL.

### Known pitfalls

- **GCS signed URL requires a service-account private key, NOT default ADC.** On Cloud Run, the Workload Identity Federation grants access but `generate_signed_url` needs an actual private key OR the IAM `iam.serviceAccountTokenCreator` role on the running service account to call the `SignBlob` API. Per `best-practices/02` WIF setup: grant `roles/iam.serviceAccountTokenCreator` to `chaoslab-agent@chaoslab-prod.iam` on itself. Without this, `generate_signed_url(version="v4")` raises `AttributeError: you need a private key to sign credentials` or hangs.
- **`storage.Client()` reads `GOOGLE_APPLICATION_CREDENTIALS` env var.** On Cloud Run this is auto-set by ADC. In local dev, point it at a service-account key JSON. In CI, use WIF.
- **`blob.upload_from_string` overwrites by default.** That's fine for ChaosLab — `recipe_id` is unique. But if a future story bumps recipe versions, add `if_generation_match=0` for create-only semantics.
- **The Markdown renderer must NOT include the GCS signed URL inside the Markdown** — the URL is generated AFTER upload, and embedding it would create a cyclic dependency. The signed URL is returned alongside the Markdown bytes, not within them.
- **`repr(tc)` for `regression_test_cases`** is hostile-readable. If a test case is `{"input": "lookup X", "expected": "graceful"}`, prefer `json.dumps(tc, indent=2)` over `repr(tc)`. (The example code above uses `{tc!r}` for brevity; the actual implementation should use `json.dumps(tc, indent=2)` and adjust BDD if needed.)
- **`HttpUrl` validation on `signed_url`** — GCS signed URLs are very long (>2000 chars). pydantic `HttpUrl` has a default max length around 2083 (browser URL limit). If you hit this, swap to plain `str` with a manual `assert signed_url.startswith("https://")` guard.
- **Cross-reference:** `architecture/04 §6.3` (sample recipe Markdown shape); `architecture.md` ADR-011 (Markdown + GitLab dual-path); `architecture.md` ADR-009 (WIF for GCS auth); `best-practices/02 §3 + §13` (WIF gotchas).
