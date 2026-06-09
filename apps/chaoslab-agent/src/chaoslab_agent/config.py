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

    gemini_api_key: SecretStr
    judge_llm: str = Field(
        default=JUDGE_LLM_LOCKED,
        description="Locked to 'gemini-3.5-flash' per ADR-007 + CLAUDE.md hard rule.",
    )
    LATENCY_SLA_MS: float = Field(
        default=5000.0,
        gt=0.0,
        description="Per-tool latency SLA in ms. F4 rubric scores against this threshold.",
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
    def _phoenix_provider_byo_requires_key(self) -> Settings:
        # ADR-017 hybrid: BYO mode demands Customer-supplied key. Default mode tolerates
        # no key (we host our own Phoenix; auth lives inside our infra).
        if self.phoenix_provider == "customer" and self.phoenix_api_key is None:
            raise ValueError(
                "phoenix_api_key is REQUIRED when phoenix_provider == 'customer' (ADR-017 BYO mode)"
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
    return Settings()  # ty: ignore[missing-argument]
