# story-9.7 — phoenix-sessions: group audit spans by run + tenant

**Epic:** 9 · **Depends on:** story-9.12 (user-profile — `owner_uid` is the authoritative tenant key)
**Source:** Wave B (Arize-track core) in the unified-finish plan (`~/.claude/plans/there-i-want-you-toasty-ember.md`, B1). Recovered from the original S9.7 entry in `jazzy-churning-koala.md`.

## Why

Phoenix's **Sessions** tab is the regulator's "show me this one audit, end-to-end" view. Today, a single audit run emits 8 probe spans + 1 judge span + 1 patcher span as ten disconnected events — the auditor and the target each show up under separate trace ids, with no `session.id` or `user.id` attribute to group them. The Arize judges and a real compliance officer want to land on the Phoenix UI and immediately see "this is run `run_ddf8b97511ca`, owned by `<uid>`, with these 8 probes and 1 verdict cluster." Phoenix's **Experiments** tab has the same disease: every judge experiment is unnamed, so the rubric runs all collapse into one anonymous experiment.

The fix is OpenInference's `using_attributes(session_id=…, user_id=…)` context — a contextvar-backed scope that injects the OpenInference session/user semantic-convention attributes onto every span created in its dynamic scope. The auditor wraps `drive_audit` in it (run_id + owner_uid). The target-agent extracts the A2A `contextId` from the inbound JSON-RPC message and enters the same scope so the target's spans join the same session in Phoenix. The `run_phoenix_experiment` tool gains an `experiment_name` parameter so Judge-mounted runs land in the Experiments tab with `phoenix-audit-{run_id}` and become deep-linkable.

## BDD acceptance criteria

- **Given** an authenticated audit launched as `run_<id>` by user uid `<uid>`, **when** `drive_audit` runs, **then** every span emitted under the injector + judge + patcher work is created inside a `using_attributes(session_id="run_<id>", user_id="<uid>")` scope. A sample-run audit (`owner_uid is None`) enters the scope with `user_id=""` (OpenInference's no-op default) so the Sessions tab still groups by run_id without inventing a tenant.
- **Given** an inbound A2A `message/send` JSON-RPC request with `params.message.contextId == "run_<id>"`, **when** the target-agent handles it, **then** every span emitted while handling that request is created inside a `using_attributes(session_id="run_<id>")` scope. A request whose body cannot be parsed as JSON, or where `contextId` is absent / empty / non-string, **then** the request still proceeds (no scope entered) and a structured warning is logged — the middleware never errors a real request because of attribute-injection failure.
- **Given** `run_phoenix_experiment(dataset_name, evaluators, *, experiment_name=…)` is called with a non-empty `experiment_name`, **then** the SDK's `client.experiments.run_experiment(...)` is invoked with that same `experiment_name` kwarg forwarded. **Given** `experiment_name` is omitted or `None`, **then** the kwarg is NOT passed (Phoenix's SDK auto-generates one — preserving current behavior for callers that haven't migrated).
- **Given** the auditor opens a new audit, **then** the chosen `experiment_name` convention is `f"phoenix-audit-{run_id}"` and is documented as the canonical name a Judge-mounted `phoenix_run_experiment_tool` call should pass.
- Trace-as-assertion: tests assert against the OpenInference contextvar that `using_attributes` sets (`session_id`, `user_id`), **not** against natural-language tracing output. The target-agent test exercises the real ASGI middleware against a real Starlette test client with a real A2A request body — no parser mocks.

## File map

- Backend (auditor): `apps/phoenix-audit-agent/src/phoenix_audit_agent/audit_runner.py` (drive_audit: accept `owner_uid: str | None`, wrap pipeline body in `using_attributes`), `apps/phoenix-audit-agent/src/phoenix_audit_agent/main.py` (thread `state.owner_uid` into the `drive_audit` call inside `_drive_orchestrator`), `apps/phoenix-audit-agent/src/phoenix_audit_agent/phoenix_tools/run_experiment.py` (optional `experiment_name: str | None` parameter on both `run_phoenix_experiment` and `_invoke_sdk`).
- Backend (target): `apps/target-agent/src/target_agent/session_attrs.py` (NEW — ASGI middleware that parses the A2A body, extracts `contextId`, enters `using_attributes`), `apps/target-agent/src/target_agent/server.py` (mount the middleware in `_assemble_app` outside `TraceContextMiddleware` so OpenInference attributes attach for the whole request).
- Tests (auditor): `apps/phoenix-audit-agent/tests/unit/test_audit_runner_sessions.py` (NEW — drive_audit wraps work in using_attributes with correct session_id+user_id), `apps/phoenix-audit-agent/tests/unit/test_run_experiment_name.py` (NEW — `experiment_name` plumbing).
- Tests (target): `apps/target-agent/tests/unit/test_session_attrs_middleware.py` (NEW — extracts contextId from a real A2A body, no-ops on missing/malformed, never raises on bad JSON).

## Notes

- `using_attributes` returns a `ContextDecorator` subclass — usable as both context manager and decorator. We use the `with` form so the scope is exited deterministically on exception (the wrapping persists even if `drive_audit` raises mid-pipeline; the failure-timeline persistence in the exception arm still gets the session_id attribute).
- The target-agent ASGI middleware MUST buffer the request body, parse it, then replay it via a wrapping `receive` callable. The A2A body is JSON-RPC + always small (< few KB) so full buffering is acceptable; the alternative (read-on-demand) would break the downstream `to_a2a()` Starlette app's body access. JSON-RPC field name is camelCase: `params.message.contextId`. Snake-case (`context_id`) is not in the wire spec — never accept it.
- The Judge-mounted `phoenix_run_experiment_tool` callsite that passes `experiment_name=f"phoenix-audit-{run_id}"` is conceptually a Judge-prompt concern; story-9.7 lands the wire (the kwarg) and documents the convention. The Judge sub-agent prompt update can land later without breaking this story's contract.
- No file >400 lines after changes; if `audit_runner.py` brushes the cap, extract `_emit_signed_report` / `_finalize_run` to a sibling module before adding wraps (significant-line count, not raw).
- `owner_uid` default `None` on `drive_audit` keeps existing test fixtures (which call `drive_audit(...)` directly without owner_uid) green; the orchestrator always passes it.
