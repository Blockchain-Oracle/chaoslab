"""Phoenix Cloud OpenInference instrumentation for the target agent.

Wires the target agent's tool + LLM spans to Phoenix Cloud so Phoenix Audit's
clusterer (and the demo Attack Matrix) can read them back.

**Import-order constraint** (per research/.../architecture/02-phoenix-deep-dive.md §3.5
and OpenInference instrumentor docs): this module must be imported and
`setup_observability()` must be invoked BEFORE any `google.adk.*` import in
calling modules. Empirically verified — see the acceptance-test AST check.

**Flag rationale** (per architecture/02 §3.5, NOT ADR-005 — see Day-4 amendment
D4-8 in audit-notes correcting the prior miscitation):

- `batch=False`  — forces `SimpleSpanProcessor` (synchronous export); the 90-
  second demo cannot tolerate the default `BatchSpanProcessor`'s 5s flush
  interval. This flag CARRIES THROUGH to Cloud Run and is mandatory for us.
- `set_global_tracer_provider=False` — keeps `register()` from clobbering an
  externally-installed global (Vertex Agent Engine installs its own; the flag
  preserves portability there). On Cloud Run we IMMEDIATELY install the global
  ourselves on the next line so consumers using `trace.get_tracer()` see the
  Phoenix-wired provider. Without this we'd need `tools.py` to lazy-import the
  tracer per-call — see test_observability::test_global_tracer_provider_is_phoenix_wired.
- `auto_instrument=False` — we explicitly wire `GoogleADKInstrumentor`; do not
  let Phoenix hook every installed openinference-* package and pollute spans.

**Credential resolution for `PHOENIX_API_KEY`:**

  1. `os.environ["PHOENIX_API_KEY"]` if set (local dev convenience)
  2. Google Secret Manager `phoenix-api-key/versions/latest` under `$GCP_PROJECT_ID`
  3. Raise `ConfigurationError` UNLESS:
     - Running on Cloud Run (`K_SERVICE` env var set): always fail loud
     - `PHOENIX_OBSERVABILITY_OPTIONAL=1`: log warning + return no-op provider
     - Default (local dev): log warning + return no-op provider
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider as _TPType

_DEFAULT_PROJECT_NAME = "target-agent"
_DEFAULT_COLLECTOR_ENDPOINT = "https://app.phoenix.arize.com"
# Name of the secret in Google Secret Manager — not the secret value.
_SECRET_NAME = "phoenix-api-key"  # noqa: S105
# 4 chars is the industry-standard "redacted prefix" length for log emission.
_API_KEY_LOG_PREFIX_LEN = 4

_logger = structlog.get_logger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when Phoenix credentials cannot be resolved from env or Secret Manager."""


class DegradedTracerProvider:
    """Sentinel wrapper around a no-op TracerProvider.

    Returned by `setup_observability()` when credentials are missing AND
    fail-loud mode is not active. Lets callers + tests `isinstance`-check
    whether observability is actually live vs silently dead.
    """

    def __init__(self, inner: _TPType) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> object:
        # Delegate every attribute lookup to the wrapped provider so this is
        # transparent to code that calls force_flush(), get_tracer(), etc.
        return getattr(self._inner, name)


def _resolve_api_key() -> str:
    """Resolve PHOENIX_API_KEY from env first, then Secret Manager.

    Returns the key string. Raises `ConfigurationError` with an actionable
    operator message keyed to the specific failure mode (NotFound,
    PermissionDenied, Unauthenticated, transient API error, etc.).
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

    try:
        from google.api_core import exceptions as gcp_exc  # noqa: PLC0415
    except ImportError as e:
        # If google-cloud-secret-manager is present, google-api-core must be too,
        # but guard defensively for partial-install scenarios.
        msg = "google-api-core not installed; cannot classify Secret Manager errors."
        raise ConfigurationError(msg) from e

    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{gcp_project}/secrets/{_SECRET_NAME}/versions/latest"
    try:
        response = client.access_secret_version(name=secret_path)
    except gcp_exc.NotFound as e:
        _logger.error("secret_manager_secret_missing", secret_path=secret_path)
        msg = (
            f"Secret '{_SECRET_NAME}' not found in project {gcp_project}. "
            f"Create it: gcloud secrets create {_SECRET_NAME} --data-file=- "
            f"--project={gcp_project}"
        )
        raise ConfigurationError(msg) from e
    except gcp_exc.PermissionDenied as e:
        _logger.error("secret_manager_permission_denied", secret_path=secret_path)
        msg = (
            f"Permission denied reading {secret_path}. Grant "
            f"roles/secretmanager.secretAccessor to the Cloud Run service account."
        )
        raise ConfigurationError(msg) from e
    except gcp_exc.Unauthenticated as e:
        _logger.error("secret_manager_unauthenticated", secret_path=secret_path)
        msg = (
            f"Unauthenticated reading {secret_path}. Workload Identity "
            f"Federation may be broken; check service account binding."
        )
        raise ConfigurationError(msg) from e
    except gcp_exc.GoogleAPIError as e:
        _logger.error(
            "secret_manager_api_error",
            error_type=type(e).__name__,
            secret_path=secret_path,
        )
        msg = f"Secret Manager API error ({type(e).__name__}) for {secret_path}: {e}"
        raise ConfigurationError(msg) from e

    secret = response.payload.data.decode("utf-8").strip()
    if not secret:
        msg = f"Secret Manager returned empty payload for {secret_path}"
        raise ConfigurationError(msg)
    _logger.info("phoenix_api_key_resolved", source="secret_manager", path=secret_path)
    return secret


def _should_fail_loud() -> bool:
    """Return True if missing credentials should crash the boot.

    Cloud Run sets `K_SERVICE` in every container; presence implies production.
    `PHOENIX_OBSERVABILITY_OPTIONAL=1` is the explicit local-dev opt-in for
    the graceful-degradation path.
    """
    on_cloud_run = bool(os.environ.get("K_SERVICE"))
    opted_in = os.environ.get("PHOENIX_OBSERVABILITY_OPTIONAL") == "1"
    return on_cloud_run and not opted_in


def setup_observability(
    project_name: str = _DEFAULT_PROJECT_NAME,
) -> _TPType:
    """Wire Phoenix Cloud + GoogleADKInstrumentor for the target agent.

    Resolves PHOENIX_API_KEY (env → Secret Manager), registers a Phoenix
    tracer provider, sets it as the global, attaches the ADK instrumentor.
    Returns the provider so callers can hold a reference (prevents GC of
    the span processor in long-running ASGI apps).

    **Graceful degradation:** if credentials are missing AND we're not on
    Cloud Run (or `PHOENIX_OBSERVABILITY_OPTIONAL=1` opts in), logs a
    warning and returns a `DegradedTracerProvider` sentinel so callers can
    distinguish "Phoenix live" from "Phoenix silently dead."

    Must be called BEFORE any `google.adk.*` import — see module docstring.
    """
    try:
        api_key = _resolve_api_key()
    except ConfigurationError as e:
        if _should_fail_loud():
            _logger.error(
                "phoenix_observability_required_but_missing",
                reason=str(e),
                env="cloud_run",
            )
            raise
        _logger.warning(
            "phoenix_observability_disabled",
            reason=str(e),
            note=(
                "Server will start but emit no Phoenix spans. "
                "Set PHOENIX_API_KEY (local) or configure Secret Manager (Cloud Run). "
                "To force this path on Cloud Run, set PHOENIX_OBSERVABILITY_OPTIONAL=1."
            ),
        )
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415

        return DegradedTracerProvider(TracerProvider())  # type: ignore[return-value]

    # Side-effect: writes PHOENIX_API_KEY + PHOENIX_COLLECTOR_ENDPOINT to
    # os.environ because phoenix.otel.register() reads them from the env,
    # not from kwargs. Idempotent across re-invocation.
    os.environ["PHOENIX_API_KEY"] = api_key
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", _DEFAULT_COLLECTOR_ENDPOINT)
    os.environ.setdefault("PHOENIX_COLLECTOR_ENDPOINT", endpoint)

    # Phoenix wiring. register() returns the SDK TracerProvider with a span
    # processor already attached for the Phoenix OTLP endpoint. Wrapped in
    # try/except so ImportError surfaces as ConfigurationError with a
    # clear remedy (symmetric with the secretmanager handling above).
    try:
        from phoenix.otel import register  # noqa: PLC0415
    except ImportError as e:
        msg = (
            "arize-phoenix-otel is not installed; cannot wire Phoenix tracing. "
            "Run `uv sync` from the workspace root."
        )
        raise ConfigurationError(msg) from e

    tracer_provider = register(
        project_name=project_name,
        set_global_tracer_provider=False,
        batch=False,
        auto_instrument=False,
    )

    # Explicitly install the Phoenix-wired provider as the global so
    # `trace.get_tracer(...)` (used at module load in tools.py) routes to
    # Phoenix instead of the no-op default. Why this is necessary
    # empirically: the S2.3 integration test was failing with 404
    # "project not found" before this line was added — manual tool spans
    # were emitting to the no-op default, never reaching Phoenix.
    from opentelemetry import trace as _otel_trace  # noqa: PLC0415

    _otel_trace.set_tracer_provider(tracer_provider)

    # ADK auto-instrumentor. Must run AFTER register() (needs the provider)
    # and BEFORE any ADK import in calling modules. Deferred so the
    # instrumentor never gets attached to a no-op global provider. Wrapped
    # the same way as register() so partial installs surface clearly.
    try:
        from openinference.instrumentation.google_adk import (  # noqa: PLC0415
            GoogleADKInstrumentor,
        )
    except ImportError as e:
        msg = (
            "openinference-instrumentation-google-adk is not installed; "
            "ADK spans will not surface. Run `uv sync` from the workspace root."
        )
        raise ConfigurationError(msg) from e

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
