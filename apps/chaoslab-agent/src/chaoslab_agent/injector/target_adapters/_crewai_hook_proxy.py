"""Per-invocation CrewAI fault-hook session.

CrewAI's `@before_tool_call` / `@after_tool_call` decorators are
PROCESS-LOCAL — they run inside the target's Python process, not ours.
For Tier 2 we can't monkey-patch the target directly; instead we rely on
the target exposing a webhook surface (`POST /hooks/before_tool_call`)
that registers fault descriptors for the duration of one invoke().

This context manager:
- Yields ``None`` for any fault_config missing ``kind: "malformed_tool_output"``.
- On the matching fault, POSTs the descriptor to ``/hooks/before_tool_call``;
  yields the ``registration_id``; tears down via DELETE on exit.
- Network failure on registration is logged but does NOT abort the invoke
  (the target may not opt in to the webhook protocol — the orchestrator
  uses `fingerprint().behavioral_signals["hooks_available"]` to choose
  matching faults; this is defensive against drift).

S5.2 (MalformedToolOutputFault) lands the descriptor schema; here we
ship the wiring + a teardown receipt.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HOOK_PATH: str = "/hooks/before_tool_call"


@asynccontextmanager
async def crewai_hook_session(
    fault_config: dict[str, Any] | None,
    *,
    http: httpx.AsyncClient | None,
    target_url: str,
) -> AsyncIterator[str | None]:
    """Yield ``registration_id`` (str) when fault_config asks for tool-hook
    interception; yield ``None`` otherwise.

    Adapters use truthiness of the yielded value to decide whether the
    fault is wired — they DON'T branch on internal flags. The detailed
    descriptor mutation lands in S5.2 + S5.7 Injector wiring; S3.4 only
    proves the context-manager round-trip works.
    """
    if fault_config is None or fault_config.get("kind") != "malformed_tool_output" or http is None:
        yield None
        return

    registration_id: str | None = None
    try:
        try:
            resp = await http.post(f"{target_url}{_HOOK_PATH}", json={"fault_config": fault_config})
        except httpx.HTTPError as exc:
            # Defensive: target may not expose the hook surface. Log + carry on.
            logger.warning("crewai_hook_registration_failed: %s", exc)
            yield None
            return
        if resp.status_code == HTTPStatus.OK.value:
            try:
                payload = resp.json()
            except ValueError:
                logger.warning("crewai_hook_registration_non_json_body")
                payload = {}
            registration_id = payload.get("registration_id")
            if registration_id is not None:
                logger.info(
                    "crewai_hook_session_active fault_kind=%s registration_id=%s",
                    fault_config.get("kind"),
                    registration_id,
                )
        else:
            logger.warning(
                "crewai_hook_registration_returned_status status=%s body=%s",
                resp.status_code,
                resp.text[:200],
            )
        yield registration_id
    finally:
        if registration_id is not None:
            try:
                await http.delete(f"{target_url}{_HOOK_PATH}/{registration_id}")
            except httpx.HTTPError as exc:
                # Teardown failure — log but don't raise (the invoke()
                # error path mustn't be masked by a webhook hiccup).
                logger.warning(
                    "crewai_hook_teardown_failed registration_id=%s err=%s",
                    registration_id,
                    exc,
                )
            else:
                logger.info("crewai_hook_session_torn_down registration_id=%s", registration_id)


__all__ = ["crewai_hook_session"]
