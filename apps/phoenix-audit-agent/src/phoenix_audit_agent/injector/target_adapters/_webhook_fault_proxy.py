"""Per-invocation webhook fault-hook session — shared by Tier-2 adapters.

CrewAI uses `POST /hooks/before_tool_call`; OpenAI Agents SDK uses
`POST /hooks/function_tool`. Both follow the same shape:

1. POST `<hook_path>` with `{"fault_config": {...}}` returns `{"registration_id": ...}`
2. Adapter invokes the target's normal run path while the hook is live.
3. On exit, DELETE `<hook_path>/<registration_id>` tears the hook down.

This module ships the shared lifecycle so each Tier-2 adapter only needs
to pass its path. S5.2 (MalformedToolOutputFault) fills in the descriptor
schema; here we only ship the wiring + a teardown receipt.

Defensive contract:
- A target that doesn't expose the hook surface is normal — the fingerprint
  signals `hooks_available=False` and S5.7 Injector skips this fault. If
  registration fails at the transport layer here, we LOG and yield None so
  the caller can fall back to the no-fault path.
- A teardown failure is LOGGED but swallowed so the invoke()'s own error
  path can propagate as the root cause.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@asynccontextmanager
async def webhook_fault_session(
    fault_config: dict[str, Any] | None,
    *,
    http: httpx.AsyncClient | None,
    target_url: str,
    hook_path: str,
    fault_kind: str,
) -> AsyncIterator[str | None]:
    """Yield `registration_id` for a matching fault, else yield None.

    Parameters:
      fault_config:  per-invocation fault descriptor from AdapterInvocation.
      http:          adapter's active httpx client (None → defensive skip).
      target_url:    base URL — `hook_path` and `/{id}` concatenate after it.
      hook_path:     framework-specific webhook path, e.g. ``/hooks/function_tool``.
      fault_kind:    only fault_config whose ``kind`` matches this str
                     triggers registration; everything else yields None.
    """
    if fault_config is None or fault_config.get("kind") != fault_kind or http is None:
        yield None
        return

    registration_id: str | None = None
    try:
        try:
            resp = await http.post(
                f"{target_url}{hook_path}",
                json={"fault_config": fault_config},
            )
        except httpx.HTTPError as exc:
            # Target may not opt in — log + carry on with the no-fault path
            # rather than aborting the audit.
            logger.warning("webhook_fault_registration_failed hook_path=%s err=%s", hook_path, exc)
            yield None
            return
        if resp.status_code == HTTPStatus.OK.value:
            try:
                payload = resp.json()
            except ValueError:
                logger.warning("webhook_fault_registration_non_json_body hook_path=%s", hook_path)
                payload = {}
            raw_id = payload.get("registration_id")
            # Shape check, not just None check: an empty/typed-wrong id would
            # mark the fault "delivered" while teardown DELETEs a bogus path.
            registration_id = raw_id if isinstance(raw_id, str) and raw_id else None
            if registration_id is None and raw_id is not None:
                logger.warning(
                    "webhook_fault_registration_malformed_id hook_path=%s raw=%r",
                    hook_path,
                    raw_id,
                )
            if registration_id is not None:
                logger.info(
                    "webhook_fault_session_active hook_path=%s fault_kind=%s registration_id=%s",
                    hook_path,
                    fault_kind,
                    registration_id,
                )
        else:
            logger.warning(
                "webhook_fault_registration_returned_status hook_path=%s status=%s body=%s",
                hook_path,
                resp.status_code,
                resp.text[:200],
            )
        yield registration_id
    finally:
        if registration_id is not None:
            try:
                await http.delete(f"{target_url}{hook_path}/{registration_id}")
            except httpx.HTTPError as exc:
                # Teardown failure — log but don't raise. The invoke()'s
                # own error path mustn't be masked by a webhook hiccup.
                logger.warning(
                    "webhook_fault_teardown_failed hook_path=%s registration_id=%s err=%s",
                    hook_path,
                    registration_id,
                    exc,
                )
            else:
                logger.info(
                    "webhook_fault_session_torn_down hook_path=%s registration_id=%s",
                    hook_path,
                    registration_id,
                )


__all__ = ["webhook_fault_session"]
