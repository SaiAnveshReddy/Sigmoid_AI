"""
Thin wrapper around the Anthropic Claude API.

Gracefully degrades when no API key is configured — the rest of the system
continues to function; only AI insights become unavailable.

Get a free API key at: https://console.anthropic.com
"""
from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger("insights.llm_client")

_DEGRADED_NO_KEY = "AI insights unavailable. Set ANTHROPIC_API_KEY in .env to enable."
_DEGRADED_API_ERROR = "AI insights temporarily unavailable."
_DEFAULT_SYSTEM_PROMPT = "You are a helpful data analyst."


def chat_completion(
    prompt: str,
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
) -> str:
    """
    Call Claude and return the assistant reply as a plain string.

    Returns a safe degradation message instead of raising if:
    - ANTHROPIC_API_KEY is not set
    - The API returns an error
    """
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning degraded message.")
        return _DEGRADED_NO_KEY

    try:
        import anthropic  # type: ignore[import]

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    except anthropic.APIError as exc:  # type: ignore[attr-defined]
        logger.error("Anthropic API error: %s", exc)
        return _DEGRADED_API_ERROR
