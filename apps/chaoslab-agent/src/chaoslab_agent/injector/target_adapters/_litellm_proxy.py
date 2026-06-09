"""Per-invocation LiteLLM proxy session — shared by Tier-2 adapters.

S3.3 (LangChain) wires the context-manager skeleton; S5.3
(PromptInjectionFault) fills in the actual `litellm.callbacks` mutation
logic. Tier-2 adapters (LangChain, CrewAI, OpenAI Agents SDK) call
``async with litellm_proxy_session(fault_config) as proxy:`` and pass
``proxy.base_url`` via an `X-LiteLLM-Base-Url` header so the target's
LiteLLM-routed model call goes through our interception point.

Round-2 review changes (SFH-I4 + SFH-I5 + CR-#2):
- `ProxyContext` is now base_url-only — the speculative `custom_logger_active`
  field was YAGNI until S5.3 actually wires registration. Truthiness of the
  context (None vs ProxyContext) is the only signal Tier-2 adapters need.
- `fault_config is None or .get("kind") != "prompt_injection"` is the explicit
  short-circuit — the previous `if not fault_config:` silently collapsed
  three different runtime states (None / {} / {"kind": None}).
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


@dataclass(frozen=True)
class ProxyContext:
    """Active LiteLLM proxy session — the adapter forwards `base_url` as
    the `X-LiteLLM-Base-Url` header. ``frozen=True`` so a caller can't mutate
    the URL mid-flight (round-2 review: any state needed beyond `base_url`
    lives in S5.3's real callback registration, not here)."""

    base_url: str


@asynccontextmanager
async def litellm_proxy_session(
    fault_config: dict[str, Any] | None,
) -> AsyncIterator[ProxyContext | None]:
    """Yield a `ProxyContext` when fault_config asks for LLM-layer interception.

    Yields ``None`` for fault_config that is missing OR whose ``kind`` is not
    ``"prompt_injection"`` — adapters use that as the signal to skip the
    `X-LiteLLM-Base-Url` header. The detailed payload-mutation logic
    (e.g., LiteLLM CustomLogger registration in `litellm.callbacks`) lands
    in S5.3 PromptInjectionFault; S3.3 only proves the context-manager
    wiring round-trips through Tier-2 adapters.

    Exception propagation contract: an exception raised INSIDE the
    ``async with litellm_proxy_session(...) as proxy:`` block propagates
    cleanly (the generator's ``finally`` runs first, then re-raises). The
    test in ``test__litellm_proxy.py`` locks this so a future refactor
    can't accidentally swallow the caller's exception.
    """
    if fault_config is None or fault_config.get("kind") != "prompt_injection":
        yield None
        return
    proxy = ProxyContext(base_url=_DEFAULT_PROXY_BASE_URL)
    logger.info(
        "litellm_proxy_session_active fault_kind=%s base_url=%s",
        fault_config.get("kind"),
        proxy.base_url,
    )
    try:
        yield proxy
    finally:
        # S5.3 will register a `litellm.callbacks.remove(...)` here. For
        # round-1+2 we just log the teardown — proves the `finally` runs
        # even when the caller's `async with` block raises.
        logger.info("litellm_proxy_session_torn_down base_url=%s", proxy.base_url)


__all__ = ["ProxyContext", "litellm_proxy_session"]
