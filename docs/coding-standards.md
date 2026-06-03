# Coding Standards — ChaosLab

**Status:** DRAFT — pending Abu approval (LOCKS upon approval)
**Last updated:** 2026-06-02

Standards apply to both Python (`apps/chaoslab-agent`, `apps/target-agent`) and TypeScript (`apps/chaoslab-web`). Enforced by pre-commit + CI gates.

---

## The 400-line file rule (HARD CONSTRAINT)

**Rule:** No tracked source file may exceed 400 significant lines (blank lines + single-line comments excluded). Applies to `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.md` under `apps/`, `packages/`, `scripts/`.

**Enforcement:**

- Pre-commit hook (`scripts/check_max_lines.py` via `pre-commit-config.yaml`)
- CI gate (`pr-checks.yaml/max-lines-check` job)
- Both must pass — belt-and-suspenders per ADR-010

**Excluded:**

- `__init__.py` (Python re-export shims)
- `.d.ts` (TypeScript type-only)
- `_vendored/` (third-party copied code with NOTICE attribution)
- Generated dirs: `node_modules/`, `.next/`, `dist/`, `build/`

**If a file approaches 400 lines: split it.** Not "remove blank lines." Split by:

- Responsibility (extract a class/function to its own module)
- Layer (UI / business / data — each its own file)
- Feature flag (gate optional behavior in a separate file)

Splitting EARLY is cheaper than splitting at 399 lines.

---

## Python standards

### Toolchain (per ADR-001 and `best-practices/01 §11`)

| Tool                                       | Purpose                                                       | Required    |
| ------------------------------------------ | ------------------------------------------------------------- | ----------- |
| `uv`                                       | Package management + venv                                     | yes         |
| `ruff`                                     | Lint + format (replaces flake8/black/isort/pylint)            | yes         |
| `ty`                                       | Type checker (Astral, primary)                                | yes         |
| `mypy strict`                              | Type checker (FALLBACK only if `ty` blocks build per ADR-001) | conditional |
| `pytest` + `pytest-asyncio` + `pytest-cov` | Tests + coverage                                              | yes         |
| `hypothesis`                               | Property-based tests                                          | encouraged  |
| `pre-commit`                               | Git hooks                                                     | yes         |

### `pyproject.toml` ruff config (workspace-level)

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["apps/chaoslab-agent/src", "apps/target-agent/src"]

[tool.ruff.lint]
select = [
  "E", "F", "W",       # pyflakes + pycodestyle
  "I",                 # isort
  "N",                 # pep8-naming
  "B",                 # bugbear
  "A",                 # builtins shadowing
  "C4",                # comprehensions
  "T20",               # print statements (banned in src/)
  "UP",                # pyupgrade
  "S",                 # bandit (security)
  "PT",                # pytest-style
  "RET",               # return statements
  "SIM",               # simplify
  "PL",                # pylint family (we skip module-line-count per ADR-010)
  "RUF",               # ruff-specific
]
ignore = [
  "S101",              # assert (allowed in tests)
  "PLR0913",           # too-many-arguments (sometimes needed for ADK signatures)
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106", "PLR2004"]
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
```

### `pyproject.toml` `ty` config

```toml
[tool.ty]
src = ["apps/chaoslab-agent/src", "apps/target-agent/src"]
python-version = "3.12"

[tool.ty.terminal]
output-format = "concise"
```

### `pyproject.toml` mypy fallback config (only used if `ty` blocks)

```toml
[tool.mypy]
python_version = "3.12"
strict = true
disallow_untyped_defs = true
warn_return_any = true
warn_unreachable = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "google.adk.*"
ignore_missing_imports = true
# Per `best-practices/03 §3`: google.adk ships partial stubs; quarantine in chaoslab_agent.adk_types module
```

### `pyproject.toml` pytest config

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["apps/*/tests"]
markers = [
  "slow: tests that take >5s",
  "online: tests that hit real Gemini/Phoenix (cost-impacting)",
  "integration: tests that span multiple components",
  "e2e: end-to-end against deployed Cloud Run",
]
addopts = "-ra --strict-markers --strict-config"
filterwarnings = [
  "error",
  "ignore::DeprecationWarning:google.*",
]

[tool.coverage.run]
source = ["apps/chaoslab-agent/src", "apps/target-agent/src"]
branch = true
omit = ["*/_vendored/*", "*/tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false
exclude_lines = ["pragma: no cover", "raise NotImplementedError", "if TYPE_CHECKING:"]
```

### Python conventions

- **Naming:** PEP 8. `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants
- **Imports:** ruff `I` sorts. Standard lib → third-party → first-party (chaoslab_agent.\*) → relative. Absolute imports only inside `chaoslab_agent`.
- **Type annotations:** REQUIRED on every function (enforced by `ty` / `mypy strict`). Return type explicit, even `-> None`.
- **Async:** prefer async-by-default for I/O. Use `asyncio.gather` for parallel waits. Never `time.sleep()` in async code — use `asyncio.sleep()`.
- **Logging:** structlog only (per `best-practices/03 §11`). NEVER `print()` (banned by `T20`). Use module-level loggers: `log = structlog.get_logger(__name__)`.
- **Docstrings:** Google style. One-line for trivial functions, full docstrings for public API (`Args:`, `Returns:`, `Raises:`).
- **Error handling:** specific exceptions only. Never bare `except:`. Re-raise with `from e` to preserve traceback. Custom exceptions in `chaoslab_agent.errors`.
- **No mutable default arguments:** ruff `B006` catches this. Use `None` + assign.
- **No global state:** all dependencies passed explicitly. Module-level constants OK, mutable globals banned.

### ADK-specific Python patterns

- **Quarantine ADK types:** import from `chaoslab_agent.adk_types` instead of `google.adk.*` directly in business logic. This module wraps ADK primitives in Pydantic models with explicit types. (Per ADR-001 + `best-practices/03 §3`.)
- **Callback registration:** use `before_tool_callback`, `after_tool_callback`, `before_model_callback`, `after_model_callback` as the injection surface for faults. Each callback module ≤400 lines.
- **Sub-agent vs A2A peer:** use `SequentialAgent`/`ParallelAgent`/`LoopAgent` for in-process. Use `RemoteA2aAgent` for out-of-process. Document the choice per architecture/03 patterns.
- **Phoenix instrumentation MUST run at module load:** `chaoslab_agent.observability.setup()` called from `main.py` BEFORE any ADK import. Per ADR-005.
- **Custom FunctionTools:** wrap Phoenix Python SDK calls. Each ≤30 LOC. Type-safe via Pydantic. Live in `chaoslab_agent.phoenix_tools/`.

### structlog setup (per `best-practices/03 §11`)

```python
# apps/chaoslab-agent/src/chaoslab_agent/observability.py
import structlog
import logging
from opentelemetry import trace

def _add_phoenix_trace_id(_logger, _method_name, event_dict):
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

def setup_logging(env: str = "production") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_phoenix_trace_id,
            structlog.processors.JSONRenderer() if env == "production" else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
```

---

## TypeScript standards

### Toolchain (per `best-practices/04`)

| Tool                                       | Purpose                 | Required |
| ------------------------------------------ | ----------------------- | -------- |
| `pnpm`                                     | Package management      | yes      |
| ESLint 9 (flat config)                     | Lint                    | yes      |
| Prettier 3 + `prettier-plugin-tailwindcss` | Format                  | yes      |
| `tsc --noEmit`                             | Type check              | yes      |
| `vitest`                                   | Unit tests              | yes      |
| `@playwright/test`                         | E2E + visual regression | yes      |

### `eslint.config.mjs`

```js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import next from "eslint-config-next";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...next,
  {
    rules: {
      "max-lines": [
        "error",
        { max: 400, skipBlankLines: true, skipComments: true },
      ],
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/strict-boolean-expressions": "error",
      "no-console": ["error", { allow: ["warn", "error"] }],
    },
  },
);
```

### `prettier.config.mjs`

```js
export default {
  semi: false,
  singleQuote: true,
  trailingComma: "all",
  printWidth: 100,
  plugins: ["prettier-plugin-tailwindcss"],
  tailwindConfig: "./tailwind.config.ts",
};
```

### `tsconfig.json` strict mode

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "verbatimModuleSyntax": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": { "@/*": ["./*"] }
  }
}
```

### TypeScript conventions

- **Naming:** `camelCase` variables/functions, `PascalCase` types/components, `SCREAMING_SNAKE` constants
- **Imports:** ESLint `import/order` sorts. `import type` for type-only imports (forced by `consistent-type-imports`)
- **Exports:** named only (NO default exports) except for Next.js pages/layouts/components where the framework requires default
- **React components:** function components only (no class). Server components by default; `'use client'` only when needed. PUSH `'use client'` boundary as LOW as possible (per `best-practices/04 §1`)
- **Hooks:** custom hooks in `app/_hooks/` or `lib/hooks/`. Naming: `useX`
- **Type assertions:** banned (`as Foo`). Use type guards or schema validation (Zod)
- **`any`:** banned (eslint `no-explicit-any`). Use `unknown` + narrow
- **`console.log`:** banned in src/ (eslint rule). Use `console.warn`/`console.error` only when justified
- **CSS:** Tailwind utility classes only. Custom CSS only in `globals.css` with `@theme` or `@layer base/components`. NEVER inline `style={{}}` except for dynamic computed values

### Next.js-specific patterns

- **Default to server components.** Mark `'use client'` only for components needing `useState`, `useEffect`, event handlers, browser APIs, or third-party client libs (Framer Motion, visx)
- **Server actions for mutations**, NOT API routes when both work
- **SSE for trace streaming** — `app/api/stream/route.ts` proxies `chaoslab-agent`'s `/stream` endpoint (per `best-practices/04 §7`)
- **Zod-validated env vars** — never read `process.env.X` directly; import from `lib/env.ts`
- **Dynamic Tailwind classes:** use a static lookup map, NEVER template-string class names (`\`bg-${color}\`` won't ship)

---

## File header conventions

### Python

```python
"""<one-line module purpose>.

Longer description if non-obvious.
Cross-references corpus or other modules if relevant.
"""
from __future__ import annotations  # required at top of every module
```

### TypeScript

```ts
// app/_components/attack-matrix.tsx
"use client";
// one-line comment explaining the component if non-obvious
```

No license headers per file — `LICENSE` + `NOTICE` at repo root cover attribution.

---

## Conventional commits

Format: `<type>(<scope>): <subject>` (lower-case, no period).

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

Scopes: `injector`, `judge`, `patcher`, `target`, `phoenix-tools`, `frontend`, `infra`, `cicd`, `docs`, `deps`

Examples:

- `feat(injector): add malformed_tool_output fault decorator`
- `fix(phoenix-tools): handle 429 retries in run_experiment wrapper`
- `refactor(judge): extract clustering to its own module`
- `test(injector): add property-based tests for malformed JSON output`

Breaking change: footer `BREAKING CHANGE: <description>` or `!` after type (`feat!:`).

Enforced via PR title check in `pr-checks.yaml`.

---

## Pre-commit hooks (full `.pre-commit-config.yaml`)

```yaml
default_language_version:
  python: python3.12

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0 # pin to latest verified
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: ty-check
        name: ty type check
        entry: uv run ty check apps/chaoslab-agent apps/target-agent
        language: system
        pass_filenames: false
        types: [python]

      - id: check-max-lines
        name: Enforce 400-line limit
        entry: python3 scripts/check_max_lines.py --strict
        language: system
        pass_filenames: false
        always_run: true

      - id: eslint
        name: ESLint (changed TS files)
        entry: pnpm --filter chaoslab-web exec eslint --fix
        language: system
        files: \.(ts|tsx|js|jsx)$
        pass_filenames: true

      - id: prettier
        name: Prettier (changed files)
        entry: pnpm --filter chaoslab-web exec prettier --write
        language: system
        files: \.(ts|tsx|js|jsx|json|css|md)$
        pass_filenames: true

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-added-large-files
        args: [--maxkb=500]

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.0
    hooks:
      - id: gitleaks

  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.43.0
    hooks:
      - id: markdownlint
        args: [--config, .markdownlint.json]

  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.6.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

---

## Definition of Done (every story)

Per `best-practices/05 §11`. Every PR must satisfy:

- [ ] All BDD acceptance criteria in the story file pass (machine-verifiable)
- [ ] CI green: lint, type-check, tests, 400-line, gitleaks, conventional-commits
- [ ] Coverage delta ≥0 on the changed module (no coverage regression)
- [ ] No new ruff / `ty` / ESLint errors
- [ ] All files ≤400 lines (`scripts/check_max_lines.py` exit 0)
- [ ] Story status flipped to `done` in YAML front-matter
- [ ] PR description: closes the issue, links to story file, summarizes change
- [ ] If UI changed: Playwright screenshot regression passes (per `best-practices/04 §15`)
- [ ] If infra changed: successful staging deploy referenced in PR description
- [ ] Docs touched: relevant `docs/*.md` updated (especially `architecture.md` if a new dep added)
- [ ] Vendored code: NOTICE updated with attribution
- [ ] `sahil-pr-audit` returns ✅ on all categories
