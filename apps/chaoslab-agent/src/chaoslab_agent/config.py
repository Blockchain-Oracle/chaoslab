"""Settings loader for chaoslab-agent (Phoenix Audit orchestrator).

Defaults to Phoenix Audit-hosted Phoenix (ADR-017). BYO mode (`phoenix_provider="customer"`)
requires `phoenix_api_key`. Settings instances are cached via `lru_cache`-wrapped
`get_settings()`; same instance across the FastAPI app + tests.
"""

from __future__ import annotations

import functools
import logging
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# JUDGE_LLM is locked to Flash by ADR-007. Flash-Lite is the documented cost-overrun fallback;
# both Pro and Flash-Lite must opt in via a future config option, not via this field.
JUDGE_LLM_LOCKED: str = "gemini-3.5-flash"

PhoenixProvider = Literal["phoenix-audit", "customer"]
Environment = Literal["dev", "staging", "prod"]

# Name of the GCS-probe escape-hatch env var. Exported as a module-level
# constant so `main.py`'s startup CRITICAL log can reference it without
# string-literal drift. The module-load drift check below ensures any
# future field rename crashloops Cloud Run at startup (loud > silent).
GCS_PROBE_ENV_NAME: str = "GCS_PROBE_AT_STARTUP"


class Settings(BaseSettings):
    """Phoenix Audit runtime settings. Loaded from env (with .env fallback for local dev)."""

    phoenix_provider: PhoenixProvider = Field(
        default="phoenix-audit",
        description="ADR-017: 'phoenix-audit' (we host) or 'customer' (BYO key).",
    )
    phoenix_api_key: SecretStr | None = Field(
        default=None,
        description="BYO Phoenix API key. REQUIRED only when phoenix_provider == 'customer'.",
    )
    phoenix_collector_endpoint: str = Field(
        default="http://localhost:6006/v1/traces",
        description=(
            "Phoenix OTLP HTTP collector endpoint. Defaults to the self-hosted "
            "Phoenix Docker URL per ADR-004; BYO mode overrides to Customer's "
            "Phoenix Cloud project URL."
        ),
    )

    # Vertex AI is the hosted default — Cloud Run mounts ADC via the runtime
    # service account, so no key is needed. AI Studio (BYO `gemini_api_key`)
    # stays available for OSS self-hosters without GCP.
    google_genai_use_vertexai: bool = Field(
        default=False,
        description="True → google-genai SDK routes through Vertex AI (ADC).",
    )
    google_cloud_project: str | None = Field(
        default=None,
        description="GCP project id for Vertex AI; required when use_vertexai is True.",
    )
    google_cloud_location: str = Field(
        default="us-central1",
        description="Vertex AI region; us-central1 is the default Gemini home.",
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="AI Studio key. Optional — required only when not using Vertex AI.",
    )
    judge_llm: str = Field(
        default=JUDGE_LLM_LOCKED,
        description="Locked to 'gemini-3.5-flash' per ADR-007 + CLAUDE.md hard rule.",
    )
    LATENCY_SLA_MS: float = Field(
        default=5000.0,
        gt=0.0,
        description="Per-tool latency SLA in ms. F4 rubric scores against this threshold.",
    )
    MAX_CLUSTERS: int = Field(
        default=5,
        ge=1,
        description="Upper bound on the clusterer output.",
    )
    GCS_RECIPES_BUCKET: str = Field(
        default="chaoslab-recipes",
        min_length=1,
        description="GCS bucket the Markdown emitter writes recipe artifacts to.",
    )
    GCS_SIGNED_URL_TTL_DAYS: int = Field(
        default=7,
        ge=1,
        description="Signed URL validity for recipe Markdown — covers a typical judging cadence.",
    )
    KMS_SIGNING_KEY_VERSION: str = Field(
        default="",
        description=(
            "Full Cloud KMS key-version resource name for Ed25519 report signing "
            "(projects/<p>/locations/<l>/keyRings/<r>/cryptoKeys/<k>/cryptoKeyVersions/<v>). "
            "Empty => report generation is SKIPPED LOUDLY (CRITICAL log + "
            "report_skipped SSE event); never silently unsigned (ADR-014)."
        ),
    )
    GCS_PROBE_AT_STARTUP: bool = Field(
        default=True,
        description=(
            "Production-safe default: probe the recipe bucket at boot so a "
            "misconfigured deploy fails loud instead of mid-/run. The Dockerfile "
            "smoke test sets this to false because it has no real bucket; a "
            "WARNING is emitted at startup whenever this is disabled, so an "
            "accidental production set is grep-able in Cloud Logging."
        ),
    )

    @property
    def JUDGE_LLM(self) -> str:  # noqa: N802 — uppercase per story-6.1 spec convention
        """Spec alias for ``judge_llm`` — exposes the locked judge model under the
        uppercase name story-6.1's BDD checks via ``get_settings().JUDGE_LLM``."""
        return self.judge_llm

    target_default_url: str = Field(
        default="http://localhost:8001",
        description="Demo target-agent URL for local dev; per-run override via /run payload.",
    )
    gitlab_token: SecretStr | None = Field(
        default=None,
        description="Optional — only needed when emitting hardening recipes to GitLab.",
    )
    GITLAB_MCP_ENDPOINT: str = Field(
        default="https://gitlab.com/api/v4/mcp",
        description=(
            "OFFICIAL GitLab MCP endpoint (ADR-011 + partner-gitlab.md). NEVER "
            "override to a community MCP server (zereight/mcpland/wadew) — "
            "judging penalty. _gitlab_mcp_client.GitLabMcpClient enforces the "
            "constraint at construction time."
        ),
    )
    GITLAB_DEFAULT_BRANCH: str = Field(
        default="main",
        min_length=1,
        description="Target branch for hardening-recipe MRs (typical: 'main').",
    )
    environment: Environment = Field(
        default="dev",
        description="dev | staging | prod — gates fail-loud vs degraded paths.",
    )
    service_version: str = Field(
        default="0.0.0",
        description="${GITHUB_SHA} at build time; '0.0.0' for local dev.",
    )
    gcs_bucket: str = Field(
        default="chaoslab-artifacts",
        description="Cloud Storage bucket for signed audit PDFs.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        frozen=True,
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("judge_llm")
    @classmethod
    def _judge_llm_locked(cls, v: str) -> str:
        if v != JUDGE_LLM_LOCKED:
            msg = (
                f"judge_llm must be {JUDGE_LLM_LOCKED!r} per ADR-007 / CLAUDE.md "
                f"hard rule; got {v!r}"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _gemini_backend_wired(self) -> Settings:
        # One of the two judge-LLM paths must be wired. Vertex needs the
        # project id (location has a default); AI Studio needs the API key.
        if self.google_genai_use_vertexai:
            if not self.google_cloud_project:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT is REQUIRED when GOOGLE_GENAI_USE_VERTEXAI=true"
                )
        elif self.gemini_api_key is None:
            raise ValueError(
                "Set GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT for the "
                "hosted Vertex path, or GEMINI_API_KEY for the BYO AI Studio path"
            )
        return self

    @model_validator(mode="after")
    def _phoenix_provider_byo_requires_key(self) -> Settings:
        # ADR-017 hybrid: BYO mode demands Customer-supplied key. Default mode tolerates
        # no key (we host our own Phoenix; auth lives inside our infra).
        if self.phoenix_provider == "customer" and self.phoenix_api_key is None:
            raise ValueError(
                "phoenix_api_key is REQUIRED when phoenix_provider == 'customer' (ADR-017 BYO mode)"
            )
        return self

    @model_validator(mode="after")
    def _gcs_probe_disabled_only_outside_prod(self) -> Settings:
        # The escape hatch exists for the Dockerfile smoke test (no real GCS
        # available). In production, the bucket probe is the round-3 fail-loud
        # gate for the regulator-facing recipe pipeline — silently allowing it
        # to be disabled would defeat the audit posture entirely. Raise loud.
        if self.environment == "prod" and not self.GCS_PROBE_AT_STARTUP:
            raise ValueError(
                f"{GCS_PROBE_ENV_NAME}=false is FORBIDDEN when environment='prod'. "
                "This escape hatch exists for the Dockerfile smoke test only; the "
                "Markdown emitter bucket probe must run at boot in production."
            )
        return self

    @model_validator(mode="after")
    def _warn_on_unused_api_key(self) -> Settings:
        # Misconfig signal: a user set PHOENIX_API_KEY thinking BYO is active, but
        # phoenix_provider is still the default. The key will be silently ignored
        # by the Phoenix Audit-hosted path. Warn so operators see the mismatch.
        if self.phoenix_provider == "phoenix-audit" and self.phoenix_api_key is not None:
            logger.warning(
                "phoenix_api_key set but phoenix_provider != 'customer'; key will be ignored. "
                "Set PHOENIX_PROVIDER=customer to enable BYO mode."
            )
        return self


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached Settings accessor — same instance across the process."""
    return Settings()


# Module-load drift guard: if the field name diverges from GCS_PROBE_ENV_NAME,
# Cloud Run crashloops at import time. Loud > silent — the constant is what
# main.py logs in its "should never be set in production" message; a silent
# divergence would defeat the grep-for-accidental-prod-set safety net.
if GCS_PROBE_ENV_NAME not in Settings.model_fields:
    raise RuntimeError(
        f"GCS_PROBE_ENV_NAME={GCS_PROBE_ENV_NAME!r} drifted from Settings field. "
        "A field rename happened — update the constant to match."
    )
