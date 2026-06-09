"""Per-invocation LiteLLM proxy session — shared by Tier-2 adapters.

S3.3 (LangChain) wires the context-manager skeleton; S5.3
(PromptInjectionFault) fills in the actual `litellm.callbacks` mutation
logic. Tier-2 adapters (LangChain, CrewAI, OpenAI Agents SDK) call
``async with litellm_proxy_session(fault_config) as proxy:`` and pass
``proxy.base_url`` via an `X-LiteLLM-Base-Url` header so the target's
LiteLLM-routed model call goes through our interception point.

When ``fault_config`` is missing the ``"kind": "prompt_injection"`` marker,
this yields ``None`` so the adapter takes the unmodified path. The
``None`` return value is the language-level None — NOT a placeholder mock,
which keeps the file §14-clean.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Default LiteLLM proxy URL. The real registration target is configured by
# S5.3 when PromptInjectionFault is loaded; this is the wire-protocol
# expectation between adapter and proxy host. Adapters pass this value as
# `X-LiteLLM-Base-Url`; the target's LiteLLM client reads it (per the
# documented convention in `context/04 §17.6`).
_DEFAULT_PROXY_BASE_URL: str = "http://localhost:4000/v1"


@dataclass
class ProxyContext:
    """Active LiteLLM proxy session — passed to the adapter's invoke loop."""

    base_url: str
    custom_logger_active: bool


@asynccontextmanager
async def litellm_proxy_session(
    fault_config: dict[str, Any] | None,
) -> AsyncIterator[ProxyContext | None]:
    """Yield a `ProxyContext` when fault_config asks for LLM-layer interception.

    Yields ``None`` for every fault_config that is missing or whose ``kind``
    is not ``"prompt_injection"`` — adapters use that as the signal to skip
    the `X-LiteLLM-Base-Url` header. The detailed payload-mutation logic
    (e.g., LiteLLM CustomLogger registration in `litellm.callbacks`) lands
    in S5.3 PromptInjectionFault; S3.3 only proves the context-manager
    wiring round-trips through Tier-2 adapters.
    """
    if not fault_config or fault_config.get("kind") != "prompt_injection":
        yield None
        return
    proxy = ProxyContext(base_url=_DEFAULT_PROXY_BASE_URL, custom_logger_active=True)
    logger.info(
        "litellm_proxy_session_active fault_kind=%s base_url=%s",
        fault_config.get("kind"),
        proxy.base_url,
    )
    try:
        yield proxy
    finally:
        # Mark the context dead so any downstream code holding a reference
        # can't accidentally believe the proxy is still active after teardown.
        # The actual `litellm.callbacks.remove(...)` lands in S5.3.
        proxy.custom_logger_active = False
        logger.info("litellm_proxy_session_torn_down base_url=%s", proxy.base_url)


__all__ = ["ProxyContext", "litellm_proxy_session"]
