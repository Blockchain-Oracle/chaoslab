"""Shared lazy `phoenix.evals.LLM` singleton for all rubrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from phoenix_audit_agent.config import get_settings

if TYPE_CHECKING:
    from phoenix.evals import LLM

_JUDGE: Any = None


def get_judge_llm() -> LLM:
    # Lazy because `LLM(provider="google", ...)` constructs a google-genai
    # client that performs ADC / credential discovery at instantiation. In
    # tests we never hit this path.
    #
    # Vertex AI backend selection happens via the three env vars
    # `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and
    # `GOOGLE_CLOUD_LOCATION` set on the Cloud Run revision. When unset
    # (e.g. self-hosters who BYO an AI Studio key) the SDK falls back to
    # `GEMINI_API_KEY` / `GOOGLE_API_KEY` env vars.
    global _JUDGE  # noqa: PLW0603
    if _JUDGE is None:
        from phoenix.evals import LLM

        _JUDGE = LLM(provider="google", model=get_settings().JUDGE_LLM)
    return _JUDGE


__all__ = ["get_judge_llm"]
