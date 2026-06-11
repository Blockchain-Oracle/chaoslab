"""Phoenix Cloud OpenInference instrumentation for the target agent.

Wires the target agent's tool + LLM spans to Phoenix Cloud so Phoenix Audit's
clusterer (and the demo Attack Matrix) can read them back.

**Import-order constraint** (verified at the source level by the acceptance-test
AST check at `tests/acceptance/test_story_2_3_target_phoenix.sh`): this module
must be imported and `setup_observability()` must be invoked BEFORE any
`google.adk.*` import in calling modules. The OpenInference instrumentor
monkey-patches ADK internals; doing it after consumers have bound module
attributes leaves spans silently uninstrumented. The correct ordering
pattern is shown in `research/.../architecture/02-phoenix-deep-dive.md §3.4`
(minimal Phoenix Cloud + ADK snippet).

**Flag choices** (per architecture/02 §3.5 Cloud Run guidance):

- `set_global_tracer_provider=True` (default) — Cloud Run is our locked
  deploy target per ADR-003. §3.5 explicitly recommends defaults on Cloud
  Run; we honor that. Vertex Agent Engine portability is a non-goal.
- `batch=True` (default) — Phoenix's register() returns a
  `SimpleSpanProcessor` (despite the kwarg name; see the boot banner). On
  Cloud Run this REQUIRES `--no-cpu-throttling` because the SDK's
  synchronous OTLP POST stalls the moment CPU drops below ~5%, and ADK's
  `agent_run` / `call_llm` / `execute_tool` spans end during exactly that
  window (after the HTTP response is on the wire). Diagnosed 2026-06-11
  (IF-19): live target produced 0 spans across 24h+ with the Cloud Run
  default `cpu-throttling=true`, while local target on the same image
  emitted 50 spans per probe. The `--no-cpu-throttling` flag is wired
  per-service via `extra_flags` in `.github/workflows/staging-deploy.yaml`.
- `auto_instrument=False` — we explicitly wire `GoogleADKInstrumentor`;
  do not let Phoenix hook every installed openinference-* package and
  pollute spans.

**Credential resolution for `PHOENIX_API_KEY`:**

  1. `os.environ["PHOENIX_API_KEY"]` if set (local dev convenience)
  2. Google Secret Manager `phoenix-api-key/versions/latest` under
     `$GCP_PROJECT_ID` — planned for S2.4 Cloud Run deploy
  3. Raise `ConfigurationError` UNLESS:
     - Running on Cloud Run (`K_SERVICE` env var set): always fail loud
     - `PHOENIX_OBSERVABILITY_OPTIONAL=1`: log warning + return no-op
     - Default (local dev): log warning + return no-op
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

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
    whether observability is actually live vs silently dead. Transparently
    delegates all TracerProvider methods (`get_tracer`, `force_flush`,
    `shutdown`, `add_span_processor`) to the wrapped instance via
    `__getattr__`.
    """

    def __init__(self, inner: _TPType) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        # `Any` return is correct: this is a transparent proxy and returns
        # whatever the wrapped provider returns (methods, properties, etc.).
        return getattr(self._inner, name)


def _resolve_api_key() -> str:  # noqa: PLR0915 — narrow exception handling needs the statement budget
    """Resolve PHOENIX_API_KEY from env first, then Secret Manager.

    Returns the key string. Raises `ConfigurationError` with an actionable
    operator message keyed to the specific failure mode.
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

    # Deferred import: avoids the import-time CPU cost of
    # google-cloud-secret-manager when the local-dev path resolves
    # PHOENIX_API_KEY from env first. (The package is a hard runtime dep
    # per pyproject.toml; this is purely a startup-latency optimization.)
    try:
        from google.cloud import secretmanager
    except ImportError as e:
        msg = (
            "google-cloud-secret-manager is not installed; cannot resolve "
            "PHOENIX_API_KEY via Secret Manager fallback. Run `uv sync`."
        )
        raise ConfigurationError(msg) from e

    try:
        from google.api_core import exceptions as gcp_exc
    except ImportError as e:
        msg = "google-api-core not installed; cannot classify Secret Manager errors."
        raise ConfigurationError(msg) from e

    # google.auth.exceptions.GoogleAuthError is NOT a subclass of
    # GoogleAPIError, so we import it separately and add it to the catch
    # tuple. Same for grpc.RpcError which can leak past gapic-transport
    # error mapping during channel-shutdown races.
    try:
        from google.auth import exceptions as gcp_auth_exc
    except ImportError as e:
        msg = "google-auth not installed; cannot classify Secret Manager errors."
        raise ConfigurationError(msg) from e

    secret_path = f"projects/{gcp_project}/secrets/{_SECRET_NAME}/versions/latest"

    # Both the client constructor (which triggers ADC resolution) and the
    # access_secret_version call are inside the try-block — ADC failure on
    # Cloud Run with broken Workload Identity raises DefaultCredentialsError
    # at construction time, which is exactly when we want the actionable
    # ConfigurationError message instead of a raw GCP traceback.
    try:
        client = secretmanager.SecretManagerServiceClient()
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
    except (gcp_exc.Unauthenticated, gcp_auth_exc.GoogleAuthError) as e:
        # GoogleAuthError covers DefaultCredentialsError, RefreshError,
        # MutualTLSChannelError, etc. — all the auth-side failure modes
        # that bypass GoogleAPIError. isinstance via the tuple is cleaner
        # than the previous string-name match.
        _logger.error(
            "secret_manager_unauthenticated",
            secret_path=secret_path,
            error_type=type(e).__name__,
        )
        msg = (
            f"Unauthenticated reading {secret_path} ({type(e).__name__}). "
            f"Workload Identity Federation may be broken; check service "
            f"account binding on the Cloud Run revision."
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
    except Exception as e:
        # Defensive: catch grpc.RpcError leaks past gapic-transport mapping.
        # We string-match on type name so `grpc` doesn't have to be a direct
        # import (it's only transitive via google-api-core[grpc]).
        # GoogleAuthError is NOT in this list — it's caught by isinstance
        # in the explicit except clause above, which is cleaner.
        if type(e).__name__ in ("RpcError", "_InactiveRpcError"):
            _logger.error(
                "secret_manager_transport_error",
                error_type=type(e).__name__,
                secret_path=secret_path,
            )
            msg = (
                f"Secret Manager transport error ({type(e).__name__}): {e}. "
                f"This usually means the gRPC channel was reset mid-call; "
                f"retry once. If persistent, check network egress."
            )
            raise ConfigurationError(msg) from e
        raise

    secret = response.payload.data.decode("utf-8").strip()
    if not secret:
        msg = f"Secret Manager returned empty payload for {secret_path}"
        raise ConfigurationError(msg)
    _logger.info("phoenix_api_key_resolved", source="secret_manager", path=secret_path)
    return secret


def _should_fail_loud() -> bool:
    """Return True if missing credentials should crash the boot.

    `K_SERVICE` is set on every Cloud Run SERVICE container (Cloud Run jobs
    use `CLOUD_RUN_JOB` instead). target-agent deploys as a service, so
    presence implies production. `PHOENIX_OBSERVABILITY_OPTIONAL=1` is
    the explicit local-dev opt-in for the graceful-degradation path.
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
        from opentelemetry.sdk.trace import TracerProvider

        # Suppression rationale: DegradedTracerProvider is structurally compatible
        # with TracerProvider (forwards required methods) but ty can't see the
        # duck-typing through the runtime composition.
        return DegradedTracerProvider(TracerProvider())  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    # Side-effect: writes PHOENIX_API_KEY + PHOENIX_COLLECTOR_ENDPOINT to
    # os.environ because the phoenix.otel.register() versions we support
    # (arize-phoenix-otel >=0.10,<1.0.0) read these from the env. Newer
    # 4.x+ versions also accept kwargs, but env-writes are conservative
    # and work across version drift. Idempotent across re-invocation.
    os.environ["PHOENIX_API_KEY"] = api_key
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", _DEFAULT_COLLECTOR_ENDPOINT)
    os.environ.setdefault("PHOENIX_COLLECTOR_ENDPOINT", endpoint)

    # Phoenix wiring. register() returns the SDK TracerProvider with a span
    # processor already attached for the Phoenix OTLP endpoint. Wrapped in
    # try/except so ImportError surfaces as ConfigurationError with a
    # clear remedy (symmetric with the secretmanager handling above).
    try:
        from phoenix.otel import register
    except ImportError as e:
        msg = (
            "arize-phoenix-otel is not installed; cannot wire Phoenix tracing. "
            "Run `uv sync` from the workspace root."
        )
        raise ConfigurationError(msg) from e

    # batch=True is critical on Cloud Run. With Phoenix's default
    # SimpleSpanProcessor, each span exports via a synchronous OTLP POST
    # on `on_end()`. Under audit concurrency (5 baseline probes in flight,
    # ~50 spans each), the synchronous chain serializes ~250 HTTPS POSTs
    # per request, and per-trace throughput drops far enough that most
    # spans never flush before the request returns and CPU throttling
    # kicks in. Diagnosed 2026-06-11 (IF-19): live audits produced 0
    # target spans for 11 of 13 traces; direct single curls produced
    # 48-50 spans cleanly. BatchSpanProcessor's queue absorbs the burst
    # and force_flush() at the end of each request guarantees pre-
    # response export. tools.py's module-level `trace.get_tracer()` will
    # automatically pick up the global Phoenix-wired provider.
    tracer_provider = register(
        project_name=project_name,
        auto_instrument=False,
        batch=True,
    )

    # Defensive runtime check: if some upstream code already installed a
    # global TracerProvider (e.g. a test-side conftest), register() may
    # have silently no-op'd the global install (OTel emits a logger.warning
    # then keeps the existing global). Surface this for production
    # diagnostics — a no-op global means tools.py spans go nowhere.
    from opentelemetry import trace as _otel_trace

    current_global = _otel_trace.get_tracer_provider()
    if current_global is not tracer_provider:
        # On Cloud Run, this is a production-fatal misconfiguration:
        # tools.py manual spans will silently disappear while ADK-
        # instrumented spans land, producing a half-empty Attack Matrix
        # at demo time. Fail loud — same fail-loud-on-Cloud-Run pattern
        # as the credential-missing branch above (see _resolve_api_key
        # call site + audit-notes D4-8 "Cloud Run safety hardening").
        # In local dev or with the explicit opt-in, log + degrade.
        if _should_fail_loud():
            _logger.error(
                "phoenix_global_tracer_provider_not_installed_cloud_run",
                current_global_type=type(current_global).__name__,
                returned_provider_type=type(tracer_provider).__name__,
                env="cloud_run",
            )
            msg = (
                "Phoenix-wired tracer provider was NOT installed as the OTel "
                "global on Cloud Run — some earlier code (likely an import-"
                "order regression) installed one first. Fix server.py so "
                "setup_observability() runs BEFORE any module that calls "
                "trace.get_tracer() at import time."
            )
            raise ConfigurationError(msg)
        _logger.warning(
            "phoenix_global_tracer_provider_not_installed",
            current_global_type=type(current_global).__name__,
            returned_provider_type=type(tracer_provider).__name__,
            note=(
                "OTel's set-once guard fired — some earlier code installed "
                "a global TracerProvider before setup_observability ran. "
                "Module-level trace.get_tracer() calls will route to the "
                "earlier global, not Phoenix. Likely test-context only; "
                "if this fires in production, fix import order in server.py."
            ),
        )

    # ADK auto-instrumentor. Must run AFTER register() (needs the provider).
    # Wrapped the same way as register() so partial installs surface clearly.
    try:
        from openinference.instrumentation.google_adk import (
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
