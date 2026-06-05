"""Phoenix Cloud OpenInference instrumentation for the target agent.

Wires the target agent's tool + LLM spans to Phoenix Cloud so Phoenix Audit's
clusterer (and the demo Attack Matrix) can read them back. Per ADR-005, this
module MUST be imported and `setup_observability()` MUST be invoked BEFORE
any `google.adk.*` import — otherwise `GoogleADKInstrumentor` patches modules
that other consumers already hold pre-patch references to, and spans silently
vanish.

The `register()` call uses `set_global_tracer_provider=False, batch=False`
(mandatory per ADR-005 Agent Engine caveat; carries through to Cloud Run for
synchronous flush during the 90-second demo) and `auto_instrument=False` so we
explicitly wire `GoogleADKInstrumentor` ourselves instead of letting Phoenix
hook every installed openinference-* package.

Credential resolution for `PHOENIX_API_KEY`:
  1. `os.environ["PHOENIX_API_KEY"]` if set (local dev convenience)
  2. Google Secret Manager `phoenix-api-key/versions/latest` under `$GCP_PROJECT_ID`
  3. Raise `ConfigurationError`
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

_DEFAULT_PROJECT_NAME = "target-agent"
_DEFAULT_COLLECTOR_ENDPOINT = "https://app.phoenix.arize.com"
# The NAME of the secret in Google Secret Manager — not the secret value itself.
_SECRET_NAME = "phoenix-api-key"  # noqa: S105
_API_KEY_LOG_PREFIX_LEN = 8

_logger = structlog.get_logger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when Phoenix credentials cannot be resolved from env or Secret Manager."""


def _resolve_api_key() -> str:
    """Resolve PHOENIX_API_KEY from env first, then Secret Manager.

    Returns the key string. Raises ConfigurationError if neither source works.
    """
    env_key = os.environ.get("PHOENIX_API_KEY")
    if env_key:
        _logger.info("phoenix_api_key_resolved", source="env")
        return env_key

    gcp_project = os.environ.get("GCP_PROJECT_ID")
    if not gcp_project:
        msg = (
            "PHOENIX_API_KEY not in env and GCP_PROJECT_ID also unset; "
            "Secret Manager fallback unreachable."
        )
        raise ConfigurationError(msg)

    # Deferred import: gates the GCP client import on actually needing it, so
    # local dev with PHOENIX_API_KEY in env doesn't pay the GCP libs' cost.
    try:
        from google.cloud import secretmanager  # noqa: PLC0415
    except ImportError as e:
        msg = (
            "google-cloud-secret-manager is not installed; cannot resolve "
            "PHOENIX_API_KEY via Secret Manager fallback."
        )
        raise ConfigurationError(msg) from e

    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{gcp_project}/secrets/{_SECRET_NAME}/versions/latest"
    try:
        response = client.access_secret_version(name=secret_path)
    except Exception as e:
        msg = f"Secret Manager access_secret_version failed for {secret_path}: {e}"
        raise ConfigurationError(msg) from e

    secret = response.payload.data.decode("utf-8").strip()
    if not secret:
        msg = f"Secret Manager returned empty payload for {secret_path}"
        raise ConfigurationError(msg)
    _logger.info("phoenix_api_key_resolved", source="secret_manager", path=secret_path)
    return secret


def setup_observability(
    project_name: str = _DEFAULT_PROJECT_NAME,
) -> TracerProvider:
    """Wire Phoenix Cloud + GoogleADKInstrumentor for the target agent.

    Resolves PHOENIX_API_KEY (env → Secret Manager), registers a Phoenix
    tracer provider, and attaches the ADK auto-instrumentor. Returns the
    tracer provider so callers can hold a reference (prevents GC of the
    span processor in long-running ASGI apps).

    **Graceful degradation:** if no credentials are reachable (local dev
    without env var or GCP creds), logs a warning and returns a plain
    TracerProvider with no Phoenix span processor attached. The server
    still starts; spans are emitted but not exported. Production Cloud
    Run gets credentials via Secret Manager so this path won't fire there.

    Must be called BEFORE any `google.adk.*` import — see module docstring.
    """
    try:
        api_key = _resolve_api_key()
    except ConfigurationError as e:
        _logger.warning(
            "phoenix_observability_disabled",
            reason=str(e),
            note=(
                "Server will start but emit no Phoenix spans. "
                "Set PHOENIX_API_KEY (local) or configure Secret Manager (Cloud Run)."
            ),
        )
        from opentelemetry.sdk.trace import TracerProvider as _NoopTracerProvider  # noqa: PLC0415

        return _NoopTracerProvider()

    os.environ["PHOENIX_API_KEY"] = api_key

    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", _DEFAULT_COLLECTOR_ENDPOINT)
    os.environ.setdefault("PHOENIX_COLLECTOR_ENDPOINT", endpoint)

    # Phoenix wiring. register() returns the SDK TracerProvider with a span
    # processor already attached for the Phoenix OTLP endpoint. Deferred
    # import: must happen AFTER PHOENIX_API_KEY is set in the env above.
    from phoenix.otel import register  # noqa: PLC0415

    tracer_provider = register(
        project_name=project_name,
        set_global_tracer_provider=False,
        batch=False,
        auto_instrument=False,
    )

    # ADK auto-instrumentor. Must run AFTER register() (needs the provider)
    # and BEFORE any ADK import in calling modules (per ADR-005). Deferred
    # so the instrumentor never gets attached to a no-op global provider.
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor  # noqa: PLC0415

    GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

    _logger.info(
        "phoenix_observability_setup",
        project_name=project_name,
        endpoint=endpoint,
        api_key_prefix=(
            api_key[:_API_KEY_LOG_PREFIX_LEN] + "..."
            if len(api_key) > _API_KEY_LOG_PREFIX_LEN
            else "***"
        ),
    )
    return tracer_provider
