# Python Project Layout & Library Best Practices (2026)

> **Scope.** This document captures *what's true in 2026* about Python project structure and library selection for production agent projects. It is purely descriptive — no decisions or opinions about any specific project. Downstream agents read this and make their own choices.
>
> **Date of research.** 2026-06-02. Versions valid as of this date and may drift.
>
> **Marking convention.** Inline `[VERIFIED]` for facts cross-checked against PyPI / official docs in this research pass. `[UNVERIFIED]` for claims that are widely-stated but I did not independently verify in this pass.

---

## 1. Python project layout conventions (2026)

### 1.1 `src/` layout vs flat layout

The two canonical Python project layouts in 2026:

```
# src/ layout                          # flat layout
myproj/                                myproj/
├── pyproject.toml                     ├── pyproject.toml
├── src/                               ├── mypkg/
│   └── mypkg/                         │   ├── __init__.py
│       ├── __init__.py                │   └── ...
│       └── ...                        └── tests/
└── tests/
```

**PyPA guidance (https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/):** PyPA presents both as viable, but enumerates three concrete benefits of `src/`:

1. **Prevents accidental imports of the in-tree copy.** Because Python prepends CWD to `sys.path`, a flat layout can silently import the working-copy package instead of the *installed* one — masking packaging bugs. `src/` removes that ambiguity. `[VERIFIED — PyPA guide]`
2. **Forces editable install during development.** You can't `python -c "import mypkg"` from the project root without `pip install -e .` first. This catches packaging-config bugs early.
3. **Catches packaging errors.** Files not properly listed in the build config simply aren't importable, surfacing configuration drift before publish.

**Application code (non-library) projects:** Many internal applications use flat layout because they're not published to PyPI — no risk of "uninstalled but accidentally importable." The Google Cloud `agent-starter-pack` template uses flat layout for the agent module (`app/` at the repo root, not `src/app/`). `[VERIFIED — agent-starter-pack base template]`

### 1.2 Package vs application distinction

| | Library (publishable) | Application (deployable) |
|---|---|---|
| Distributed via | PyPI wheel | Container image / source bundle |
| Layout favoured | `src/` (PyPA-recommended) | Flat is common and accepted |
| `pyproject.toml [project] name` | The PyPI dist name | Just a project name (e.g., `my-agent`) |
| Entry points | `[project.scripts]` for CLI tools | Often via uvicorn/adk/gunicorn invocation |
| Dependency style | Loose lower-bounds (`>=`) | Pinned with lockfile (`uv.lock`) |
| Build backend | Required (hatchling, setuptools, poetry-core) | Required only if containerised wheel build |

The `agent-starter-pack` template is interesting because the generated project is shaped like an application (deployed to Cloud Run / Agent Engine) but still ships with `[build-system] requires = ["hatchling"]` so the agent module can be wheel-built for deployment. `[VERIFIED — agent-starter-pack base template pyproject.toml]`

### 1.3 Test directory placement

Two patterns dominate:

```
# pattern A: tests/ alongside src/        # pattern B: nested under package
myproj/                                   myproj/
├── src/                                  ├── src/mypkg/
│   └── mypkg/                            │   ├── __init__.py
│       └── ...                           │   └── tests/
└── tests/                                │       └── test_*.py
    ├── unit/                             └── ...
    ├── integration/
    └── e2e/
```

**Pattern A** (`tests/` as sibling) is dominant in 2026. It allows pytest to discover tests without importing the source tree, and keeps tests out of the published wheel. `[VERIFIED — agent-starter-pack uses pattern A with `tests/unit`, `tests/integration`, `tests/eval` subdirs]`

**Pattern B** (`mypkg/tests/`) is rare in modern code; mostly seen in legacy `setup.py` projects.

The `agent-starter-pack` ADK template's specific layout:

```
tests/
├── unit/                     # pytest unit tests
├── integration/
│   └── test_agent.py         # spins up Runner + InMemorySessionService
└── eval/
    ├── eval_config.json      # ADK eval config
    └── evalsets/
        └── basic.evalset.json
```
`[VERIFIED — gh api inspection]`

### 1.4 Config file conventions

A 2026 production Python project typically ships:

| File | Role | Required? |
|---|---|---|
| `pyproject.toml` | PEP 517/518 build config + tool config | Yes |
| `uv.lock` (or `poetry.lock`) | Pinned dependency graph | Yes for apps |
| `.python-version` | pyenv / uv reads to pin interpreter | Yes |
| `.env.example` | Documented env var template (no secrets) | Yes |
| `.env` | Local-only secrets, gitignored | Yes (gitignored) |
| `.gitignore` | Standard Python + tool exclusions | Yes |
| `.dockerignore` | Slim container builds | If containerized |
| `Makefile` | Common dev commands (install / test / lint / deploy) | Common, not required |
| `README.md` | Project overview, quickstart, links | Yes |
| `CLAUDE.md` / `GEMINI.md` / `AGENTS.md` | Agent-driven dev guidance | Optional, increasingly common |
| `LICENSE` | OSS license file | If open source |

**`pyproject.toml` as the single source of truth.** PEP 621 (`[project]` table) + PEP 518 (`[build-system]`) + tool-specific tables (`[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.mypy]`, `[tool.uv]`, `[tool.hatch.build.targets.wheel]`) all live in one file. Standalone `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `tox.ini` are legacy in 2026 — most new projects skip them.

### 1.5 Multi-package monorepo patterns

**uv workspaces** (https://docs.astral.sh/uv/concepts/projects/workspaces/) — Cargo-style:

```toml
# Root pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/seeds"]

# Then each packages/foo/pyproject.toml is its own project
# Inter-package deps:
[tool.uv.sources]
mypkg-core = { workspace = true }
```

Key facts (from uv workspaces docs):
- **Single shared `uv.lock`** at the workspace root. All members lock to the same dependency versions. `[VERIFIED]`
- **Per-package `pyproject.toml`** with its own dependencies + tool config.
- **Shared `requires-python`** — uv takes the intersection of all members' Python version requirements. `[VERIFIED]`
- **Editable workspace deps** via `workspace = true` under `[tool.uv.sources]`. `[VERIFIED]`
- **When NOT to use workspaces:** if members need conflicting deps or separate venvs, use path dependencies instead. `[VERIFIED]`

**Poetry workspaces:** Poetry 2.4 documentation (https://python-poetry.org/docs/, fetched 2026-06-02) does not surface a workspace concept on the landing page; the community uses `path` deps + monorepo plugins (e.g., `poetry-workspace-plugin`) to approximate it. `[UNVERIFIED for 2026 — Poetry may have added native workspaces; landing page didn't mention them in this fetch]`

**Pants / Bazel** remain the heavyweight option for very large Python monorepos with cross-language builds; uncommon for hackathon-scale work.

---

## 2. Package management: uv vs poetry vs pip-tools (2026 state)

### 2.1 uv (`https://docs.astral.sh/uv/`)

- **Latest version (2026-06-02):** `uv` 0.11.18, released 2026-06-01. `[VERIFIED — pypi.org/project/uv]`
- **Vendor:** Astral (same team as Ruff and ty).
- **Implementation:** Rust.
- **Self-described scope:** "An extremely fast Python package and project manager... consolidates functionality from pip, pip-tools, pipx, poetry, pyenv, twine, and virtualenv into a single tool." `[VERIFIED — docs.astral.sh/uv/]`
- **Speed claim:** "10-100x faster" than pip. `[VERIFIED — official docs]`
- **Lockfile:** `uv.lock`, universal cross-platform format. `[VERIFIED]`
- **Workspaces:** Native (Cargo-style), shared lockfile, see §1.5. `[VERIFIED]`
- **Python version management:** `uv python install 3.12`, `uv python pin 3.12`. Reads `.python-version`. `[VERIFIED]`
- **Drop-in compatibility:** `uv pip install …` is a faster pip clone. `[VERIFIED]`
- **PEP 723 inline-script deps:** `uv run script.py` reads inline metadata. `[VERIFIED]`
- **Tool installer:** `uv tool install ruff` (replaces pipx). `[VERIFIED]`
- **`uvx` for ephemeral execution:** `uvx <pkg> ...` runs in a throwaway venv. `[VERIFIED — used heavily in agent-starter-pack: `uvx agent-starter-pack create ...`]`

### 2.2 Poetry (`https://python-poetry.org/docs/`)

- **Latest version (2026-06-02):** Poetry 2.4 stable. `[VERIFIED — landing page]`
- **Implementation:** Python.
- **Lockfile:** `poetry.lock`, "ensure repeatable installs". `[VERIFIED]`
- **Workspaces:** Not surfaced as a first-class concept on the 2.4 docs landing page; path deps + community plugins approximate. `[UNVERIFIED for deep current state]`
- **Speed:** Significantly slower than uv. Specific benchmarks not re-verified in this pass.
- **Build backend:** `poetry-core`, PEP 517-compliant.

### 2.3 pip-tools (`https://github.com/jazzband/pip-tools`)

- Provides `pip-compile` (resolves `requirements.in` → pinned `requirements.txt`) and `pip-sync` (reconciles venv with lockfile).
- Still used in 2026 for projects that want plain `requirements.txt` semantics with proper pinning.
- Slower than uv (uv has a `uv pip compile` equivalent that's 10-100x faster). `[UNVERIFIED for 2026 specific benchmarks]`

### 2.4 hatch / pdm / rye

- **hatch** — modern build backend + project manager. The Google `agent-starter-pack` uses `hatchling` (hatch's build backend) for wheel builds. `[VERIFIED]`
- **pdm** — early PEP 621 implementation; smaller community share in 2026.
- **rye** — Armin Ronacher's project manager; **now folded into uv** (development of rye paused; uv absorbed its mindshare). `[UNVERIFIED for current rye status]`

### 2.5 Recommended default in 2026

Signal: every major template I inspected in this research pass uses uv:
- `agent-starter-pack` (Google Cloud) — `uvx agent-starter-pack create ...`, `uv sync`, `uv run`, `uv.lock` in repo. `[VERIFIED]`
- ADK template Makefile bootstraps uv if missing: `curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh`. `[VERIFIED]`
- Tooling installations: `uv tool install ruff`, `uvx ty check`. `[VERIFIED — official docs of each tool]`

Combined factual signal: **uv is the de facto default for new Python projects in 2026.** Poetry remains widely deployed in existing codebases. pip-tools is maintenance mode for projects that want only the resolver, not a full project manager.

---

## 3. Google Cloud `agent-starter-pack` canonical layout

### 3.1 Repository

- **GitHub:** https://github.com/GoogleCloudPlatform/agent-starter-pack
- **PyPI:** `agent-starter-pack` 0.41.3 (2026-06-02). `[VERIFIED — pyproject.toml inspection]`
- **License:** Apache-2.0.
- **Requires:** Python ≥3.10.

### 3.2 Top-level repo structure

```
agent-starter-pack/
├── .cloudbuild/                # Cloud Build pipelines (project's own CI)
├── .github/                    # GitHub Actions
├── agent_starter_pack/         # Source: the CLI + templates
│   ├── agents/                 # ← one subdir per template
│   │   ├── adk/                # Base ReAct agent (Python ADK)
│   │   ├── adk_a2a/            # ADK + Agent2Agent protocol
│   │   ├── adk_go/             # Go ADK
│   │   ├── adk_java/           # Java ADK
│   │   ├── adk_live/           # Multimodal RAG (audio/video/text)
│   │   ├── adk_ts/             # TypeScript ADK
│   │   ├── agentic_rag/        # RAG agent (document Q&A)
│   │   └── langgraph/          # LangChain LangGraph base agent
│   ├── base_templates/         # Shared scaffolding
│   │   ├── _shared/
│   │   ├── go/
│   │   ├── java/
│   │   ├── python/             # ← Python base template (see §3.3)
│   │   └── typescript/
│   ├── cli/                    # Click-based CLI
│   ├── deployment_targets/     # cloud_run/, gke/, agent_engine/
│   ├── frontends/              # Optional UI scaffolds (e.g., adk_live_react)
│   ├── resources/
│   ├── sample_data/
│   └── utils/
├── docs/                       # Documentation site
├── tests/                      # CLI tests
├── pyproject.toml
├── uv.lock
├── Makefile
├── GEMINI.md                   # Agent-driven dev guidance for the meta-repo
├── llm.txt                     # Machine-readable LLM-onboarding doc
└── README.md
```
`[VERIFIED — gh api repos/GoogleCloudPlatform/agent-starter-pack/contents inspection]`

### 3.3 The Python base template (`agent_starter_pack/base_templates/python/`)

This is what gets rendered when a user runs `uvx agent-starter-pack create my-agent -a adk -d cloud_run`:

```
{generated_project}/
├── .cloudbuild/                # Cloud Build CI (if cicd_runner=google_cloud_build)
├── .github/                    # GitHub Actions (if cicd_runner=github_actions)
├── .gitignore
├── Makefile                    # `install`, `playground`, `deploy`, `test`, `lint`, ...
├── README.md
├── pyproject.toml              # The fully-templated pyproject (see §3.5)
├── deployment/
│   └── terraform/              # IaC for the chosen deployment target
├── {{cookiecutter.agent_directory}}/   # ← default: `app/`
│   ├── __init__.py
│   ├── agent.py                # The agent definition
│   └── app_utils/              # Deploy + telemetry helpers
│       ├── converters/
│       ├── executor/
│       ├── gcs.py
│       ├── telemetry.py
│       └── typing.py
├── tests/
│   ├── unit/
│   ├── integration/
│   │   └── test_agent.py
│   └── eval/
│       ├── eval_config.json
│       └── evalsets/
│           └── basic.evalset.json
└── {{cookiecutter.agent_guidance_filename}}    # default: `GEMINI.md`
```
`[VERIFIED — base_templates/python directory listing + Makefile + pyproject.toml fetches]`

### 3.4 Canonical `agent.py` shape (ADK template)

```python
# app/agent.py  (templated for clarity)
import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Optional Vertex AI auto-bootstrap (only when not using AI Studio API key):
import os
import google.auth
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def get_weather(query: str) -> str:
    """Tool: simulated web search for weather. Args/Returns described
    in the docstring — ADK reads docstrings to populate tool schemas."""
    ...


def get_current_time(query: str) -> str:
    """Tool: simulated time lookup."""
    ...


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a helpful AI assistant...",
    tools=[get_weather, get_current_time],
)

app = App(
    root_agent=root_agent,
    name="app",
)
```
`[VERIFIED — agents/adk/app/agent.py in repo]`

Key observations:

- The module exposes a top-level `root_agent: Agent` and an `app: App`.
- `app/__init__.py` re-exports the App: `from .agent import app; __all__ = ["app"]`. `[VERIFIED]`
- **Tools are plain Python functions with docstrings.** ADK introspects the signature and docstring to build the tool schema. No decorators required.
- The starter template inlines tools in `agent.py`. A `prompts.py` + `tools.py` split is common in larger projects but not enforced by ADK.

### 3.5 Canonical `pyproject.toml` from the base template

Full template-rendered shape (Jinja stripped, ADK + Cloud Run target):

```toml
[project]
name = "my-agent"
version = "0.1.0"
description = ""
authors = [{name = "Your Name", email = "your@email.com"}]
dependencies = [
    "google-adk>=1.15.0,<2.0.0",                              # injected per-template
    "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",
    "gcsfs>=2024.11.0",
    "google-cloud-logging>=3.12.0,<4.0.0",
    "google-cloud-aiplatform[evaluation]>=1.130.0",
    "fastapi>=0.115.8,<1.0.0",
    "uvicorn~=0.34.0",
    "asyncpg>=0.30.0,<1.0.0",
]
requires-python = ">=3.10,<3.14"

[dependency-groups]
dev = [
    "pytest>=8.3.4,<9.0.0",
    "pytest-asyncio>=0.23.8,<1.0.0",
    "nest-asyncio>=1.6.0,<2.0.0",
]

[project.optional-dependencies]
jupyter = ["jupyter>=1.0.0,<2.0.0"]
eval = ["google-adk[eval]>=1.15.0,<2.0.0"]
lint = [
    "ruff>=0.4.6,<1.0.0",
    "ty>=0.0.1a0",
    "codespell>=2.2.0,<3.0.0",
]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E","F","W","I","C","B","UP","RUF"]
ignore = ["E501","C901","B006"]

[tool.ruff.lint.isort]
known-first-party = ["app", "frontend"]

[tool.ty]
[tool.ty.environment]
python-version = "3.10"
[tool.ty.src]
exclude = [".venv/**"]
[tool.ty.rules]
unresolved-import = "ignore"
unresolved-attribute = "ignore"
invalid-argument-type = "ignore"
invalid-assignment = "ignore"
invalid-return-type = "ignore"
possibly-missing-attribute = "ignore"
not-subscriptable = "ignore"
deprecated = "ignore"

[tool.codespell]
ignore-words-list = "rouge"
skip = "./locust_env/*,uv.lock,.venv,./frontend,**/*.ipynb,**/package-lock.json"

[tool.pytest.ini_options]
pythonpath = "."
asyncio_default_fixture_loop_scope = "function"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app", "frontend"]

# Generation metadata so the generated project remains a remote template
[tool.agent-starter-pack]
name = "my-agent"
base_template = "adk"
agent_directory = "app"
asp_version = "0.41.3"
[tool.agent-starter-pack.create_params]
deployment_target = "cloud_run"
session_type = "in_memory"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
```
`[VERIFIED — base_templates/python/pyproject.toml]`

### 3.6 How `adk web` discovers agents

From the generated Makefile:
```make
playground:
    uv run adk web . --port 8501 --reload_agents
```
`[VERIFIED — Makefile]`

The `adk web` CLI is invoked with a **directory argument**. It walks that directory looking for subdirectories that contain a module exposing an `App` (or `root_agent`). The base template's instructions reinforce this: "Select the 'app' folder to interact with your agent." `[VERIFIED — Makefile echo]`

So the discovery contract is:
1. A subdirectory matching the agent's name (e.g., `app/`).
2. An `app/__init__.py` re-exporting an `App` instance (e.g., `from .agent import app; __all__ = ["app"]`).
3. `adk web <parent-dir>` is launched from the project root.

`--reload_agents` enables file-watcher hot reload.

### 3.7 The `adk` CLI

Subcommands surfaced by the starter-pack Makefile and ADK docs:

| Command | Purpose |
|---|---|
| `adk web <dir>` | Launches local web playground that auto-discovers agents in `<dir>`. |
| `adk eval <agent_path> <evalset.json>` | Runs evaluation suite against a defined agent. The Makefile's `eval` target uses this. `[VERIFIED]` |
| `adk run <module>` | Local single-agent CLI run (per ADK docs). `[UNVERIFIED via direct fetch in this pass — adk.dev landing didn't expose CLI details]` |
| `adk deploy ...` | Some deployment-helper subcommands exist depending on ADK version. `[UNVERIFIED for current API]` |

### 3.8 Tests organization in the ADK template

```
tests/
├── unit/                        # Fast tests, no GCP calls
├── integration/
│   └── test_agent.py            # ADK Runner + InMemorySessionService end-to-end
└── eval/
    ├── eval_config.json         # ADK eval framework config
    └── evalsets/
        └── basic.evalset.json   # Conversation-level eval cases
```

The integration test pattern (`tests/integration/test_agent.py`, verbatim from the template):

```python
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_agent_stream() -> None:
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Why is the sky blue?")],
    )
    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0
    assert any(
        event.content and event.content.parts and any(p.text for p in event.content.parts)
        for event in events
    )
```
`[VERIFIED — tests/integration/test_agent.py in repo]`

Pytest config (from pyproject.toml):
```toml
[tool.pytest.ini_options]
pythonpath = "."                              # so `from app.agent import ...` works
asyncio_default_fixture_loop_scope = "function"
```

The Makefile's `test` target:
```make
test:
    uv sync --dev
    uv run pytest tests/unit && uv run pytest tests/integration
```
`[VERIFIED]`

### 3.9 Lint target conventions

The Makefile codifies a 3-tool lint chain:

```make
lint:
    uv sync --dev --extra lint
    uv run codespell                 # typo check
    uv run ruff check . --diff       # linter
    uv run ruff format . --check --diff   # formatter check
    uv run ty check .                # type checker
```
`[VERIFIED — base template Makefile]`

Note: the template uses **`ty`** (Astral's Rust type checker), not mypy or pyright. See §4 for tradeoffs.

---

## 4. Recommended Python libraries for ADK projects (with versions)

All versions verified against PyPI on 2026-06-02 unless noted.

### 4.1 Core ADK

| Library | Version | Notes |
|---|---|---|
| `google-adk` | **2.1.0** (2026-05-23) | `pip install google-adk`. Python ≥3.10. Optional extras: `a2a`, `eval`, `extensions`, `gcp`, `mcp`, `otel-gcp`, `slack`, `test`, `tools`, `toolbox`. `[VERIFIED — pypi.org/project/google-adk]`. Note: the agent-starter-pack template still pins `>=1.15.0,<2.0.0` because templates lag releases. |

Common extras-pin pattern in pyproject:
```toml
dependencies = ["google-adk>=2.1.0,<3.0.0"]
[project.optional-dependencies]
eval = ["google-adk[eval]>=2.1.0,<3.0.0"]
a2a = ["google-adk[a2a]>=2.1.0,<3.0.0"]
mcp = ["google-adk[mcp]>=2.1.0,<3.0.0"]
```

### 4.2 Phoenix observability

| Library | Version | Notes |
|---|---|---|
| `arize-phoenix` | **17.0.0** (2026-06-02) | The full Phoenix UI + server. Python `>=3.10,<3.15`. Elastic License 2.0. `[VERIFIED — pypi.org/project/arize-phoenix]` |
| `arize-phoenix-otel` | (latest) | Lightweight OTel SDK wrapper. Install when you only need to emit traces, not host the UI. `[UNVERIFIED for current pinned version]` |
| `arize-phoenix-client` | (latest) | Programmatic client for the Phoenix REST API (experiments, datasets, annotations). `[UNVERIFIED for current pinned version]` |
| `openinference-instrumentation-google-adk` | **0.1.15** (2026-05-22) | Auto-instruments ADK calls into OpenInference span format. Python `>=3.10,<3.15`. `[VERIFIED — pypi.org/project/openinference-instrumentation-google-adk]` |

Setup boilerplate (per openinference-instrumentation-google-adk docs):
```python
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

endpoint = "http://127.0.0.1:6006/v1/traces"
provider = trace_sdk.TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))

GoogleADKInstrumentor().instrument(tracer_provider=provider)
```

**For Vertex Agent Engine**, the corpus's `04-cross-framework-instrumentation.md` notes the trap: must call `register(batch=False, set_global_tracer_provider=False)` — see corpus §10 in that file.

### 4.3 HTTP client

| Library | Version | Notes |
|---|---|---|
| `httpx` | **0.28.1** (2024-12-06) | Sync + async API, HTTP/2, requests-compatible. `[VERIFIED — pypi.org/project/httpx]` |
| `requests` | 2.x | Sync only; legacy. Don't pick for new async code. |
| `aiohttp` | 3.x | Async-first, larger; httpx is preferred for new projects in 2026. |

Recommended pattern: `httpx.AsyncClient` for async, `httpx.Client` for sync. Single dependency covers both.

### 4.4 Schema validation

| Library | Version | Notes |
|---|---|---|
| `pydantic` | **2.13.4** (latest v2) | Rust core (`pydantic-core`), 5-50x faster than v1. `pip install pydantic`. `[VERIFIED — pydantic.dev landing]` |
| `pydantic-settings` | **2.14.1** (2026-05-08) | `BaseSettings` for env-driven config. Optional extras: `aws-secrets-manager`, `azure-key-vault`, `gcp-secret-manager`, `toml`, `yaml`. Python ≥3.10. `[VERIFIED — pypi.org/project/pydantic-settings]` |

The `gcp-secret-manager` extra is relevant for Cloud Run apps that load secrets from Secret Manager:
```bash
pip install "pydantic-settings[gcp-secret-manager]"
```

### 4.5 Async runtime

| Choice | Notes |
|---|---|
| **`anyio`** | Backend-agnostic async (works with asyncio or trio). The official MCP Python SDK depends on anyio. Good for libraries that want to be runtime-agnostic. `[VERIFIED — modelcontextprotocol/python-sdk uses anyio]` |
| **Raw `asyncio`** | Standard library; simpler if you're only ever running on asyncio. Used by FastAPI, Uvicorn, and the ADK Runner. |
| `trio` | Smaller community share in 2026; pick anyio if you want trio-compatibility. |

The ADK ecosystem itself is asyncio-native (`Runner.run` returns an async iterator). MCP clients are anyio-based but interoperate with asyncio cleanly.

### 4.6 Testing

| Library | Version | Notes |
|---|---|---|
| `pytest` | **9.0.3** (2026-04-07) | Python ≥3.10. `[VERIFIED — pypi.org/project/pytest]` |
| `pytest-asyncio` | 0.23+ | Required for `async def test_*` functions. Set `asyncio_default_fixture_loop_scope = "function"` (the starter pack does this). |
| `pytest-cov` | 5.x+ | Coverage reporter. Pin loosely. |
| `pytest-mock` | 3.x+ | `mocker` fixture wrapping `unittest.mock`. |
| `pytest-xdist` | 3.x+ | Parallel test execution. |
| `pytest-rerunfailures` | 15.x+ | Retry flaky tests. Used by agent-starter-pack itself. `[VERIFIED]` |

### 4.7 HTTP mocking

| Library | Version | Notes |
|---|---|---|
| `respx` | **0.23.1** (2026-04-08) | httpx-specific request mocking. Requires httpx ≥0.25. `[VERIFIED — pypi.org/project/respx]` |
| `pytest-httpx` | latest | Alternative pytest fixture style for httpx mocking. |
| `responses` | latest | For `requests` library only — pick respx if you're using httpx. |

### 4.8 Linting + formatting

| Library | Version | Notes |
|---|---|---|
| `ruff` | **0.15.15** (2026-05-28) | Replaces black + isort + flake8 + pyupgrade + autoflake + pydocstyle. 900+ rules. Rust. `[VERIFIED — pypi.org/project/ruff]` |

Recommended config baseline (matches agent-starter-pack):
```toml
[tool.ruff]
line-length = 88
target-version = "py310"   # bump as you bump requires-python

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort
    "C",   # flake8-comprehensions
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "RUF", # ruff-specific
]
ignore = ["E501", "C901", "B006"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

Ruff also has a separate formatter (`ruff format`) — black-compatible. The starter-pack lint target runs both:
```bash
ruff check . --diff && ruff format . --check --diff
```

### 4.9 Type checking

| Tool | Status | Notes |
|---|---|---|
| **`pyright`** | Mature; 98% typing-spec conformance. Microsoft. 2-5x faster than mypy. Best correctness/speed ratio in 2026 per multiple sources. `[VERIFIED via search — pydevtools handbook + Pyrefly conformance comparison]` |
| **`mypy`** | Mature; 57% conformance per recent benchmarks; well-supported plugin ecosystem; CI-installed everywhere. `[VERIFIED via search]` |
| **`ty`** | Astral. ~10-100x faster on large codebases (Rust). Newer; lower spec conformance than mypy (as of 2026-03). **Adopted by `agent-starter-pack`**. `[VERIFIED — docs.astral.sh/ty + agent-starter-pack pyproject]` |
| **`pyrefly`** | Meta's competitor; scores higher than ty + mypy on typing-spec; 10-50x faster on large codebases. `[VERIFIED via search — pyrefly.org/blog]` |

Current state (2026-06):
- For new ADK projects following the starter-pack template: `ty` (matches starter-pack default).
- For maximum correctness: `pyright`.
- For maximum compatibility with existing ecosystem (Django, SQLAlchemy plugins, FastAPI integration): `mypy`.

### 4.10 Logging

| Library | Version | Notes |
|---|---|---|
| `structlog` | **25.5.0** (2025-10-27) | Structured logging via processor chain. ~25-100% faster than loguru for JSON output. Free OpenTelemetry integration via stdlib bridge. `[VERIFIED — pypi.org/project/structlog]` |
| `loguru` | latest | Zero-config, single `from loguru import logger`. Easier DX. Production caveat: `diagnose=True` (default) leaks variable values in tracebacks — set `diagnose=False` in prod. `[VERIFIED via search — Dash0 + BSWEN guides]` |
| stdlib `logging` | always | Required as the underlying sink. Both structlog and loguru ultimately route through it (or replace it). |

Tradeoff in 2026 (per Dash0 + BSWEN 2026-04 guides):
- **structlog** wins for microservices, high-throughput, OTel-integrated apps.
- **loguru** wins for new projects, prototypes, scripts, when DX trumps.

### 4.11 Config management

| Library | Notes |
|---|---|
| `pydantic-settings` | The dominant pattern in 2026. Inherit from `BaseSettings`, fields auto-load from env, validation built-in. Optional GCP/AWS/Azure secret-manager extras. |
| `python-dotenv` | Loads `.env` into `os.environ`. Often used in combination with pydantic-settings (`env_file=".env"`). |
| stdlib `os.environ` | Always works; no validation. |
| `dynaconf` | Larger framework; multi-source config; smaller share in 2026. |

Recommended pattern:
```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    gcp_project: str
    gemini_model: str = "gemini-2.0-flash"
    phoenix_endpoint: str = "http://localhost:6006/v1/traces"
    debug: bool = False

settings = Settings()  # validates at import
```

### 4.12 CLI

| Library | Version | Notes |
|---|---|---|
| `click` | **8.4.1** (2026-05-22) | Decorator-based; mature; used by the agent-starter-pack itself. Pallets project. `[VERIFIED — pypi.org/project/click]` |
| `typer` | **0.26.6** (2026-06-02) | Built on click; uses type hints for arguments. By Sebastián Ramírez (FastAPI). `[VERIFIED — pypi.org/project/typer]` |
| stdlib `argparse` | always | Fine for tiny scripts; verbose for non-trivial CLIs. |

For 2026 new projects, the consensus signal (per devtoolbox + codecut 2026 comparisons): **typer** for new CLIs that lean into type hints; **click** for deep customization or maintaining click-based code. The Google `agent-starter-pack` CLI itself uses click. `[VERIFIED — agent-starter-pack pyproject.toml lists `click>=8.1.7`]`

### 4.13 MCP client

| Library | Version | Notes |
|---|---|---|
| `mcp` | **1.27.2** (2026-05-29) | Official Python MCP SDK. Provides `FastMCP` (decorator server framework) and `ClientSession` (client). Depends on anyio + httpx + pydantic. `[VERIFIED — pypi.org/project/mcp]` |

Install:
```bash
pip install "mcp[cli]"
```

Extras: `cli`, `rich`, `ws`.

Note: ADK also has its own MCP integration via `google-adk[mcp]`. For pure MCP work (no ADK), use the `mcp` package directly.

### 4.14 A2A peer

| Library | Version | Notes |
|---|---|---|
| `a2a-sdk` | **1.1.0** (2026-05-29) | Official Python SDK for A2A Protocol v1.0 (with v0.3 compat). Apache-2.0. Python ≥3.10. Async architecture. Multi-transport (JSON-RPC, HTTP+JSON/REST, gRPC). OTel built-in. `[VERIFIED — pypi.org/project/a2a-sdk]` |

Extras include http-server, gRPC, postgres/mysql/sqlite, OTel, encryption.

Alternative A2A implementations exist (`python-a2a`, `agentic-a2a`, `agent-framework-a2a`, `FastA2A`) but the official `a2a-sdk` from the a2aproject org is the canonical choice in 2026.

### 4.15 GitLab integration

Two options coexist:

**a) `python-gitlab` REST/GraphQL client** — `[VERIFIED — pypi.org/project/python-gitlab]`
- Current: **8.4.0** (2026-05-28).
- `pip install --upgrade python-gitlab`.
- Sync + async GraphQL clients + CLI tool.

**b) Official GitLab MCP server (not a Python lib — it's a server)** — `[VERIFIED via search]`
- Introduced as experiment in GitLab 18.3, Beta in 18.6, GA-quality in 18.11 (2026-04).
- Premium/Ultimate tier, 15 tools.
- Anthropic's reference server `@modelcontextprotocol/server-gitlab` has been **archived** in favour of GitLab's official server.
- Community alternative: `zereight/gitlab-mcp` (1.4k stars, 100+ tools).

Python projects that need to query GitLab in 2026 typically either talk to the MCP server (via the `mcp` Python SDK client) or use `python-gitlab` directly. The choice is workload-dependent.

### 4.16 Google Cloud SDKs

| Library | Version | Use |
|---|---|---|
| `google-cloud-secret-manager` | **2.28.0** (2026-05-07) | Reading Secret Manager values. `[VERIFIED]` |
| `google-cloud-aiplatform` | latest (template uses `>=1.130.0`) | Vertex AI, Agent Engine deploy. Extras: `[evaluation,agent-engines]`. `[VERIFIED — template pyproject]` |
| `google-cloud-logging` | latest (template uses `>=3.12.0,<4.0.0`) | Structured logging to Cloud Logging. |
| `google-cloud-run` | latest | Cloud Run admin operations (rarely needed in agent app code). |
| `google-cloud-storage` | latest | GCS reads/writes. Often replaced by `gcsfs` for filesystem-style access. |
| `google-cloud-trace` | latest | Cloud Trace exporter (vs Phoenix/OTLP). |
| `gcsfs` | latest (template uses `>=2024.11.0`) | fsspec-compatible GCS access. |

Common pattern: the deployed agent uses Application Default Credentials (`google.auth.default()`) so no key files are needed in container envs.

### 4.17 Other commonly-paired libraries

| Library | Purpose |
|---|---|
| `fastapi` | HTTP framework (template uses `>=0.115.8,<1.0.0`) for Cloud Run / GKE deployments. |
| `uvicorn` | ASGI server (template uses `~=0.34.0`). |
| `asyncpg` | Postgres driver for `session_type=cloud_sql`. |
| `nest-asyncio` | Used in notebooks + tests to allow re-entering asyncio loops. Template ships in dev group. |
| `opentelemetry-instrumentation-google-genai` | First-party Gemini call instrumentation (separate from openinference). |
| `opentelemetry-exporter-otlp-proto-http` | HTTP OTLP exporter (Phoenix expects this). |
| `protobuf` | Required pin (`>=6.31.1,<7.0.0`) for Agent Engine deploy target per the template. |

---

## 5. `pyproject.toml` template (fully-specified)

A `pyproject.toml` shaped for a production ADK agent project in 2026. Pinned major versions, all the tools from §4 included. Not specific to any project.

```toml
# ============================================================================
# Project metadata (PEP 621)
# ============================================================================
[project]
name = "my-agent"
version = "0.1.0"
description = "An ADK agent for X"
readme = "README.md"
requires-python = ">=3.11,<3.14"
license = {text = "Apache-2.0"}
authors = [
    {name = "Author Name", email = "author@example.com"},
]
keywords = ["ai", "agent", "adk", "google-cloud"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    # Core ADK
    "google-adk>=2.1.0,<3.0.0",

    # HTTP + schema
    "httpx>=0.28.0,<1.0.0",
    "pydantic>=2.13.0,<3.0.0",
    "pydantic-settings>=2.14.0,<3.0.0",

    # Observability — Phoenix + OpenInference
    "arize-phoenix-otel>=0.6.0,<1.0.0",
    "arize-phoenix-client>=0.1.0,<1.0.0",
    "openinference-instrumentation-google-adk>=0.1.15,<1.0.0",
    "opentelemetry-sdk>=1.29.0,<2.0.0",
    "opentelemetry-exporter-otlp-proto-http>=1.29.0,<2.0.0",
    "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0",

    # Logging
    "structlog>=25.5.0,<26.0.0",

    # MCP + A2A
    "mcp[cli]>=1.27.0,<2.0.0",
    "a2a-sdk>=1.1.0,<2.0.0",

    # Google Cloud
    "google-cloud-logging>=3.12.0,<4.0.0",
    "google-cloud-secret-manager>=2.28.0,<3.0.0",
    "google-cloud-aiplatform[evaluation]>=1.130.0",
    "gcsfs>=2024.11.0",

    # HTTP framework (if deploying as Cloud Run / GKE service)
    "fastapi>=0.115.8,<1.0.0",
    "uvicorn[standard]>=0.34.0,<1.0.0",

    # CLI
    "typer>=0.26.0,<1.0.0",
]

# ============================================================================
# Dev dependencies (PEP 735 dependency-groups, uv-native)
# ============================================================================
[dependency-groups]
dev = [
    "pytest>=9.0.0,<10.0.0",
    "pytest-asyncio>=0.23.8,<1.0.0",
    "pytest-cov>=5.0.0,<7.0.0",
    "pytest-mock>=3.12.0,<4.0.0",
    "pytest-xdist>=3.6.0,<4.0.0",
    "pytest-rerunfailures>=15.0.0,<16.0.0",
    "respx>=0.23.0,<1.0.0",
    "nest-asyncio>=1.6.0,<2.0.0",
]

# ============================================================================
# Optional dependency groups (PEP 621)
# ============================================================================
[project.optional-dependencies]
eval = [
    "google-adk[eval]>=2.1.0,<3.0.0",
    "arize-phoenix>=17.0.0,<18.0.0",
]
lint = [
    "ruff>=0.15.0,<1.0.0",
    "ty>=0.0.1a0",          # Astral type checker (alpha but used by agent-starter-pack)
    "codespell>=2.2.0,<3.0.0",
]
jupyter = [
    "jupyter>=1.0.0,<2.0.0",
    "ipykernel>=6.29.0,<7.0.0",
]
a2a = [
    "google-adk[a2a]>=2.1.0,<3.0.0",
]
mcp-extra = [
    "google-adk[mcp]>=2.1.0,<3.0.0",
]
gitlab = [
    "python-gitlab>=8.4.0,<9.0.0",
]
secrets = [
    "pydantic-settings[gcp-secret-manager]>=2.14.0,<3.0.0",
]

# ============================================================================
# Scripts / entry points
# ============================================================================
[project.scripts]
my-agent = "app.cli:main"

# ============================================================================
# Build system
# ============================================================================
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

# ============================================================================
# uv config
# ============================================================================
[tool.uv]
default-groups = ["dev"]
# If using a workspace:
# [tool.uv.workspace]
# members = ["packages/*"]

# ============================================================================
# Ruff (linter + formatter)
# ============================================================================
[tool.ruff]
line-length = 88
target-version = "py311"
extend-exclude = [".venv", "build", "dist"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "RUF",  # ruff-specific
    "ASYNC",# flake8-async
    "SIM",  # flake8-simplify
    "PT",   # pytest-style
    "T20",  # flake8-print
    "TID",  # flake8-tidy-imports
    "PERF", # perflint
]
ignore = [
    "E501",  # line too long (formatter handles)
    "B008",  # function default arg call (FastAPI Depends, Typer)
]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# ============================================================================
# Pytest
# ============================================================================
[tool.pytest.ini_options]
minversion = "9.0"
pythonpath = ["."]
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=xml",
]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "unit: fast tests, no external services",
    "integration: tests that need GCP / Phoenix / network",
    "e2e: full-stack tests against a deployed agent",
    "slow: tests that take >5s",
]
log_cli = true
log_cli_level = "INFO"

# ============================================================================
# Coverage
# ============================================================================
[tool.coverage.run]
source = ["app"]
branch = true
omit = [
    "tests/*",
    "app/**/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
fail_under = 70
show_missing = true

# ============================================================================
# Type checking — pick one of mypy or ty
# ============================================================================
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = [
    "google.adk.*",
    "openinference.*",
    "phoenix.*",
]
ignore_missing_imports = true

# Alternative: ty (Astral)
[tool.ty]
[tool.ty.environment]
python-version = "3.11"
[tool.ty.src]
exclude = [".venv/**", "build/**", "dist/**"]
[tool.ty.rules]
unresolved-import = "ignore"
unresolved-attribute = "ignore"
deprecated = "ignore"

# ============================================================================
# Codespell
# ============================================================================
[tool.codespell]
ignore-words-list = "rouge"
skip = ".venv,uv.lock,**/*.ipynb,**/*.lock"
```

---

## 6. `.env` management

### 6.1 Tools

- **`python-dotenv`** — loads `.env` into `os.environ`. Used as the file reader.
- **`pydantic-settings`** — validated config objects backed by env vars. Wraps python-dotenv (`env_file=".env"`).

In 2026, the dominant pattern is: **pydantic-settings owns the model; python-dotenv only matters if you load envs outside that model.**

### 6.2 12-factor config principles (applied)

1. **Store config in the environment.** Not in code. Not in committed files.
2. **One env var per setting.** Avoid encoding multiple settings into one var.
3. **Strict separation: code vs config vs secrets.** Config is non-sensitive (URLs, region names); secrets are credentials.
4. **No `.env` in git.** Always `.gitignore` it. Commit `.env.example` with documented var names but no values.
5. **Treat env vars as strings.** Validate at boundary (pydantic-settings handles this).

### 6.3 Secret vs config separation

| Type | Where to store locally | Where to store in prod |
|---|---|---|
| Config (`GEMINI_MODEL`, `PROJECT_ID`, `REGION`) | `.env` (gitignored) | Env vars set on Cloud Run service |
| Secrets (`GEMINI_API_KEY`, DB passwords) | `.env` (gitignored) | **GCP Secret Manager**, mounted into Cloud Run via `--set-secrets` |

Cloud Run secret mount example:
```bash
gcloud run deploy my-agent \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  ...
```

The starter-pack `make deploy` for Agent Engine passes secrets via `--set-secrets="KEY=SECRET_ID,..."`. `[VERIFIED — base Makefile]`

### 6.4 `.env.example` pattern

```bash
# .env.example  — committed to repo, no real secrets

# Google Cloud
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-east1
GOOGLE_GENAI_USE_VERTEXAI=True

# Gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=   # only if NOT using Vertex AI

# Phoenix
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
PHOENIX_API_KEY=  # only when sending to cloud Phoenix

# Logging
LOG_LEVEL=INFO
ENV=local
```

The `.gitignore` should always have:
```
.env
.env.local
.env.*.local
```

### 6.5 Cloud Run env var injection

Three ways to inject env vars on Cloud Run:

1. **Inline in the deploy command** — `--set-env-vars KEY1=value1,KEY2=value2`.
2. **From a YAML file** — `--env-vars-file env.prod.yaml` (PyYAML format).
3. **From Secret Manager** — `--set-secrets KEY=SECRET_NAME:latest`.

The agent-starter-pack `make deploy` for Cloud Run uses `--update-env-vars` (preserves existing vars and adds/updates listed ones) — see the Makefile.

---

## 7. Module organization patterns

These are *factual descriptions* of common patterns. The right choice depends on project size, team, and target audience.

### 7.1 Layered (api / services / repositories / models)

```
app/
├── api/               # HTTP / agent-protocol surface (FastAPI routes, ADK App)
├── services/          # Business logic
├── repositories/      # Data access (DB, vector store, external APIs)
├── models/            # Pydantic schemas / domain types
├── tools/             # ADK tools
├── prompts/           # System prompts, prompt templates
└── config.py          # pydantic-settings Settings
```

Pros: clear separation, easy to test services in isolation.
Cons: can over-layer for small projects; can degenerate to "everything is a service".

### 7.2 Hexagonal / clean architecture

```
app/
├── domain/            # Pure business types + protocols (no I/O)
├── adapters/
│   ├── inbound/       # API handlers, agent App, CLI
│   └── outbound/      # DB, LLM client, vector store, external APIs
├── usecases/          # Orchestration
└── infra/             # Wire-up, config, DI
```

Inversion principle: domain depends on nothing; adapters depend on domain. Strict about boundaries; high test isolation.

Pros: maximum testability; clean swap of LLM providers / vector stores.
Cons: ceremony-heavy; overkill for small projects.

### 7.3 Domain-Driven Design (DDD) modules

```
app/
├── ingestion/         # Bounded context 1
├── retrieval/         # Bounded context 2
├── reasoning/         # Bounded context 3
├── shared/            # Cross-cutting kernel
└── main.py
```

One package per "bounded context"; each has its own models, services, repositories.

Pros: scales to large teams.
Cons: requires real domain modeling; rare at hackathon scale.

### 7.4 Pattern observed in ADK starter-pack

```
app/
├── __init__.py        # re-exports App
├── agent.py           # Agent + tools inline
└── app_utils/
    ├── converters/    # Format conversions
    ├── executor/      # Local + remote runners
    ├── gcs.py         # GCS helpers
    ├── telemetry.py   # OTel setup
    └── typing.py      # Shared TypedDicts / Protocols
```
`[VERIFIED — base_templates/python/{{agent_directory}}/app_utils inspection]`

Observations:
- `agent.py` is the *single* canonical location for the agent definition.
- `app_utils/` is the catch-all for non-agent infrastructure (telemetry, GCS, deployment helpers).
- Tools/prompts are inline in `agent.py` for small agents; can be split into `tools.py` and `prompts.py` as the project grows.
- No formal layering — flat and pragmatic.

### 7.5 Common ADK-specific sub-modules in practice

When projects grow beyond the starter template, the typical extraction is:

```
app/
├── __init__.py
├── agent.py              # Agent + App definition; root_agent assembled here
├── tools/                # One file per tool group
│   ├── __init__.py
│   ├── search.py
│   ├── gitlab.py
│   └── filesystem.py
├── prompts/              # Prompt templates
│   ├── __init__.py
│   ├── system.py
│   └── few_shot.py
├── schemas/              # Pydantic models for tool I/O
│   └── __init__.py
├── observability/        # Phoenix + OTel setup
│   ├── __init__.py
│   └── tracing.py
├── config.py             # pydantic-settings
└── app_utils/            # Deploy helpers (mirroring starter-pack)
```

---

## 8. Naming conventions

### 8.1 PEP 8 baselines

| Item | Convention |
|---|---|
| Modules | `lower_snake_case.py` |
| Packages | `lower_snake_case/` |
| Classes | `CapWords` |
| Functions, variables | `lower_snake_case` |
| Constants | `UPPER_SNAKE_CASE` |
| Type aliases | `CapWords` (PEP 613) |
| Type variables | Single uppercase letter or `CapWords` ending in `T` |

### 8.2 Test file naming

`pytest` discovers `test_*.py` OR `*_test.py` by default. The 2026 convention strongly favours **`test_*.py`** because it's the pytest default in all template ecosystems (including the ADK starter-pack: `test_agent.py`). `[VERIFIED]`

### 8.3 Private vs public APIs

- `_name` → module-private convention. Linters won't import it via wildcard imports.
- `__name` → name-mangled in classes (`_ClassName__name`). Rare outside classes.
- `__all__ = [...]` in `__init__.py` → defines the public surface for `from pkg import *` and signals intent. The ADK template uses this:
  ```python
  # app/__init__.py
  from .agent import app
  __all__ = ["app"]
  ```
  `[VERIFIED]`

### 8.4 ADK-specific naming patterns (from the starter pack)

- `root_agent: Agent` — the top-level agent variable.
- `app: App` — wraps `root_agent`, exported from the package.
- Tool functions: plain verbs, e.g., `get_weather`, `search_docs`. Docstring describes purpose + Args/Returns (used to build the tool schema).
- Prompt templates: usually `<role>_PROMPT` or `<role>_INSTRUCTION` constants in UPPER_SNAKE_CASE.

---

## 9. README + CLAUDE.md best practices

### 9.1 README structure (general)

A high-signal README in 2026 typically has:

1. **One-line tagline** under the title.
2. **30-second elevator pitch** (3-5 sentences).
3. **Screenshot or GIF** of the working product. For agent projects, this is often a Phoenix trace screenshot or a `adk web` UI shot.
4. **Architecture diagram** (Mermaid is favoured because GitHub renders it).
5. **Quickstart** — copy-paste install + first-run commands.
6. **Tech stack** with version pins.
7. **Repository structure** — annotated tree.
8. **Development** — install, test, lint, run-locally commands (mirror the Makefile targets).
9. **Deployment** — how to ship it.
10. **License + contributors**.

For Google AI hackathon submissions specifically (per `research/google-cloud-rapid-agent/05-prior-winners.md`), README structure that historically wins:
- Demo video link at the top.
- Architecture diagram (judges scan, not read).
- "Built with" section listing every Google Cloud product used (Tech Implementation score).
- "What's next" section showing post-hackathon roadmap (Potential Impact score).

### 9.2 `CLAUDE.md` / `GEMINI.md` / `AGENTS.md`

These files are agent-driven dev guidance — read by Claude Code / Gemini Code Assist / OpenAI Codex when an agent works in the repo.

The agent-starter-pack itself ships **two** such files at different levels:
- `GEMINI.md` at the repo root: guidance for contributors to the meta-project (the CLI itself).
- `{{cookiecutter.agent_guidance_filename}}` in generated projects: guidance for agents working in the generated project.

Convention (from agent-starter-pack `llm.txt`):
- Section 1: Project Overview (what, why, tagline).
- Section 2: Creating & Enhancing Projects (commands).
- Section 3: Key Features & Configuration Options.
- Section 4: CLI Reference.

Typical `CLAUDE.md` skeleton for an agent project:
```markdown
# CLAUDE.md
## Project Overview
[name, purpose, deployment target]

## Tech Stack & Versions
[uv version, Python version, ADK version, key libraries]

## Commands
- `make install` — install deps
- `make playground` — local dev (runs `adk web`)
- `make test` — pytest
- `make lint` — ruff + ty
- `make deploy` — push to Cloud Run / Agent Engine

## Architecture
[brief module map]

## Coding standards
[type hints required, ruff config inherited from pyproject, etc.]

## Testing rules
[mock Gemini calls via respx; integration tests in tests/integration/]

## What NOT to do
[no committing .env; no requirements.txt — uv.lock is source of truth]
```

The Anthropic-pushed **`AGENTS.md`** standard (`agents-md.org` / similar) is a converging proposal; it serves the same role and is increasingly cross-tool readable.

---

## 10. Documentation strategy

### 10.1 Docstring styles

| Style | Format | Used by |
|---|---|---|
| **Google** | `Args: / Returns: / Raises:` headers | Most Google projects, including ADK. Picked up by ADK to populate tool schemas. `[VERIFIED — get_weather example]` |
| **NumPy/SciPy** | `Parameters\n----------\nname : type\n    desc` | Scientific stack (numpy, pandas, scipy, sklearn). |
| **reStructuredText (`:param x:`)** | `:param name: desc\n:returns: desc` | Sphinx default, older Python convention. |

For ADK projects specifically: **Google style** is recommended because ADK reads docstrings to build tool schemas. Example from the starter pack:
```python
def get_weather(query: str) -> str:
    """Simulates a web search. Use it to get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
```
`[VERIFIED]`

### 10.2 Auto-generated API docs

| Tool | Notes |
|---|---|
| **Sphinx** | Industry standard for Python libraries. The agent-starter-pack itself uses Sphinx (`sphinx~=7.1.2`, `sphinx-autoapi~=3.0.0`, `sphinx-click~=5.1.0`, `sphinx-rtd-theme~=2.0.0`). `[VERIFIED]` |
| **mkdocs + mkdocstrings** | Markdown-first; lighter; better for application-style projects. |
| **pdoc** | Minimal, opinionated. |

### 10.3 ADR (Architecture Decision Records)

```
docs/
└── adr/
    ├── 0001-use-uv-not-poetry.md
    ├── 0002-pin-google-adk-major.md
    ├── 0003-pydantic-settings-for-config.md
    └── README.md         # index
```

Typical ADR template (Michael Nygard format):
```
# ADR-NNNN: <decision>
## Status
Accepted | Superseded by ADR-XXXX | Deprecated

## Context
<what's the problem, what are the forces>

## Decision
<what was decided>

## Consequences
<what changes, what tradeoffs>
```

ADRs are useful for hackathon projects specifically because the post-mortem write-up references them.

---

## 11. Pre-existing project templates worth cloning

| Repo | Stars (approx) | Notes |
|---|---|---|
| **`GoogleCloudPlatform/agent-starter-pack`** | (1k+) | Canonical for Google Cloud ADK projects. Multi-template (ADK Python/TS/Java/Go, langgraph, agentic_rag). uv-first. Cloud Build / GitHub Actions CI generated. `[VERIFIED — Apache-2.0, Python 3.10+]` |
| `google/adk-samples` | — | Per-feature ADK snippets; not full project scaffolds. `[UNVERIFIED — not inspected in this pass]` |
| `pydantic/FastUI` | — | If building agent UIs in Python. `[UNVERIFIED]` |
| `Arize-ai/phoenix` | — | Phoenix itself; examples directory has agent integration patterns. `[UNVERIFIED for current state]` |
| `fastapi/full-stack-fastapi-template` | (high) | Not agent-specific but the canonical "production FastAPI project" template with uv, Docker, GitHub Actions, postgres, alembic. Worth scanning for app-layout ideas. `[UNVERIFIED for current state]` |
| `pyscaffold/pyscaffold` | (1k+) | Generic Python project scaffold; src-layout-first. `[UNVERIFIED current state]` |
| `astral-sh/uv` | (high) | uv's own example projects in the docs are good references. |

For Cloud Run agents specifically, the agent-starter-pack `create` command followed by `extract` (for the minimal shareable form) is the path-of-least-resistance starting point.

---

## 12. Sources

### Official documentation

- [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [PyPA Sample Project](https://github.com/pypa/sampleproject)
- [PEP 621 — Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 735 — Dependency Groups in pyproject.toml](https://peps.python.org/pep-0735/)
- [PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/)
- [uv documentation](https://docs.astral.sh/uv/)
- [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [ty documentation](https://docs.astral.sh/ty/)
- [Poetry documentation](https://python-poetry.org/docs/)
- [pip-tools](https://github.com/jazzband/pip-tools)
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)
- [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [httpx documentation](https://www.python-httpx.org/)
- [respx](https://lundberg.github.io/respx/)
- [structlog](https://www.structlog.org/)
- [loguru](https://loguru.readthedocs.io/)
- [Click](https://click.palletsprojects.com/)
- [Typer](https://typer.tiangolo.com/)

### Agent / ADK ecosystem

- [Google ADK landing](https://adk.dev/)
- [Google Cloud agent-starter-pack repo](https://github.com/GoogleCloudPlatform/agent-starter-pack)
- [agent-starter-pack pyproject.toml](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/pyproject.toml)
- [agent-starter-pack base Python template](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agent_starter_pack/base_templates/python)
- [agent-starter-pack ADK agent template](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agent_starter_pack/agents/adk)
- [agent-starter-pack llm.txt](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/main/llm.txt)
- [Arize Phoenix repo](https://github.com/Arize-ai/phoenix)
- [OpenInference Google ADK instrumentation](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk)
- [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Official A2A SDK (a2aproject/a2a-python)](https://github.com/a2aproject/a2a-python)
- [python-gitlab](https://python-gitlab.readthedocs.io/)
- [Official GitLab MCP server reference](https://docs.gitlab.com/ee/user/gitlab_duo_chat/) (search for MCP)

### PyPI version pages (verified 2026-06-02)

- [`uv` 0.11.18](https://pypi.org/project/uv/)
- [`ruff` 0.15.15](https://pypi.org/project/ruff/)
- [`pytest` 9.0.3](https://pypi.org/project/pytest/)
- [`pydantic-settings` 2.14.1](https://pypi.org/project/pydantic-settings/)
- [`google-adk` 2.1.0](https://pypi.org/project/google-adk/)
- [`arize-phoenix` 17.0.0](https://pypi.org/project/arize-phoenix/)
- [`openinference-instrumentation-google-adk` 0.1.15](https://pypi.org/project/openinference-instrumentation-google-adk/)
- [`mcp` 1.27.2](https://pypi.org/project/mcp/)
- [`a2a-sdk` 1.1.0](https://pypi.org/project/a2a-sdk/)
- [`structlog` 25.5.0](https://pypi.org/project/structlog/)
- [`respx` 0.23.1](https://pypi.org/project/respx/)
- [`click` 8.4.1](https://pypi.org/project/click/)
- [`typer` 0.26.6](https://pypi.org/project/typer/)
- [`httpx` 0.28.1](https://pypi.org/project/httpx/)
- [`python-gitlab` 8.4.0](https://pypi.org/project/python-gitlab/)
- [`google-cloud-secret-manager` 2.28.0](https://pypi.org/project/google-cloud-secret-manager/)

### Comparative analyses (2026)

- [Dash0 — Choosing a Python Logging Library in 2026](https://www.dash0.com/guides/python-logging-libraries)
- [BSWEN — Which Python Logging Library Should I Use in 2026?](https://docs.bswen.com/blog/2026-04-29-python-logging-library-choice/)
- [Better Stack — Best Python logging libraries](https://betterstack.com/community/guides/logging/best-python-logging-libraries/)
- [pydevtools — How do Python type checkers compare?](https://pydevtools.com/handbook/explanation/how-do-mypy-pyright-and-ty-compare/)
- [danilchenko.dev — mypy vs Pyright vs ty (2026)](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/)
- [Pyrefly — Typing Spec Conformance comparison](https://pyrefly.org/blog/typing-conformance-comparison/)
- [Pyright vs mypy comparison](https://github.com/microsoft/pyright/blob/main/docs/mypy-comparison.md)
- [DevToolbox — Python CLI Tools with Click and Typer (2026)](https://devtoolbox.dedyn.io/blog/python-click-typer-cli-guide)
- [CodeCut — Comparing argparse, Click, and Typer](https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/)
- [TokenMix — GitLab MCP Server Setup (2026)](https://tokenmix.ai/blog/gitlab-mcp-server-complete-setup-use-cases-2026)

### Cross-references inside this corpus

- `research/google-cloud-rapid-agent/context/04-cross-framework-instrumentation.md` — Phoenix + OpenInference setup details, including the Vertex Agent Engine `register(batch=False, set_global_tracer_provider=False)` trap.
- `research/google-cloud-rapid-agent/context/06-open-standards.md` — MCP 2025-11-25, A2A v1.0, OpenInference spec versions.
- `research/google-cloud-rapid-agent/05-prior-winners.md` — README + demo patterns that have historically won.
- `research/google-cloud-rapid-agent/partner-arize.md` — Arize Phoenix partner deep-dive.
- `research/google-cloud-rapid-agent/partner-gitlab.md` — GitLab partner deep-dive.

---

*End of file. Last updated 2026-06-02.*
