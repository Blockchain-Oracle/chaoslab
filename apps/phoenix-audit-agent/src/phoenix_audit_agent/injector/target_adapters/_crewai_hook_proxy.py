"""CrewAI-specific binding of the shared `webhook_fault_session` proxy.

Round-2 follow-up (S3.5): the actual session lifecycle moved to
`_webhook_fault_proxy.py` so OpenAI Agents SDK (S3.5) and future Tier-2
adapters inherit the same defensive shape. This module is a thin
adapter-specific binding — fixes the hook path and fault kind so the
adapter call site stays readable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from phoenix_audit_agent.injector.target_adapters._webhook_fault_proxy import (
    webhook_fault_session,
)

_HOOK_PATH: str = "/hooks/before_tool_call"
_FAULT_KIND: str = "malformed_tool_output"


@asynccontextmanager
async def crewai_hook_session(
    fault_config: dict[str, Any] | None,
    *,
    http: httpx.AsyncClient | None,
    target_url: str,
) -> AsyncIterator[str | None]:
    """Yield `registration_id` for `malformed_tool_output` fault, else None.

    Delegates to `webhook_fault_session` with CrewAI's path + fault kind
    baked in — adapter call sites don't need to know the constants.
    """
    async with webhook_fault_session(
        fault_config,
        http=http,
        target_url=target_url,
        hook_path=_HOOK_PATH,
        fault_kind=_FAULT_KIND,
    ) as registration_id:
        yield registration_id


__all__ = ["crewai_hook_session"]
