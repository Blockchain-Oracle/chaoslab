"""Settings loader for chaoslab-agent (Phoenix Audit orchestrator).

Amended for Patch #22 (ADR-017 hybrid Phoenix-hosting):
- `phoenix_provider` defaults to "phoenix-audit" (we host); "customer" enables BYO.
- `phoenix_api_key` is OPTIONAL by default; REQUIRED only when phoenix_provider == "customer".
- `phoenix_collector_endpoint` defaults to the self-hosted Phoenix Docker URL
  (`http://localhost:6006/v1/traces`); BYO mode overrides via env.

Loaded via `functools.lru_cache`-wrapped `get_settings()`; identical instance across
the FastAPI app + tests.
"""

from __future__ import annotations

import functools
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Per ADR-007 (cost model, AMENDED Day-3 audit A10), Flash is the locked judge model.
# Pro is 1.33x cost not 17x, but Flash is the default; Flash-Lite is the cost-overrun fallback.
JUDGE_LLM_LOCKED: str = "gemini-3.5-flash"

PhoenixProvider = Literal["phoenix-audit", "customer"]
Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Phoenix Audit runtime settings. Loaded from env (with .env fallback for local dev)."""

    # -- Phoenix hosting (ADR-017 hybrid mode) ---------------------------------
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
            "Phoenix Docker URL per ADR-004 (amended); BYO mode overrides to Customer's "
            "Phoenix Cloud project URL."
        ),
    )

    # -- Judge LLM (ADR-007 hard rule) -----------------------------------------
    gemini_api_key: SecretStr
    judge_llm: str = Field(
        default=JUDGE_LLM_LOCKED,
        description="Locked to 'gemini-3.5-flash' per ADR-007 + CLAUDE.md hard rule.",
    )

    # -- Target + auxiliary services -------------------------------------------
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
        description="Cloud Storage bucket for signed-PDF archival. Renamed post-S1.6.",
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
        # ADR-007 + CLAUDE.md: ONLY gemini-3.5-flash. Pro is for spec-author use; Flash-Lite is
        # the documented cost-overrun fallback — both must opt in explicitly via a future
        # config option, not via this field.
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


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached Settings accessor — same instance across the process."""
    return Settings()  # ty: ignore[missing-argument]
