"""
Thin wrapper around the Google Gemini API (gemini-1.5-flash).

Free tier: 15 requests/minute, no billing required.
Get a key at: https://aistudio.google.com → Get API key

Gracefully degrades when no API key is configured — the rest of the system
continues to function; only AI insights become unavailable.
"""
from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger("insights.llm_client")

_DEGRADED_NO_KEY = "AI insights unavailable. Set GEMINI_API_KEY in .env to enable."
_DEGRADED_API_ERROR = "AI insights temporarily unavailable."
_DEFAULT_SYSTEM_PROMPT = "You are a helpful data analyst."


def chat_completion(
    prompt: str,
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
) -> str:
    """
    Call Gemini and return the model reply as a plain string.

    Returns a safe degradation message instead of raising if:
    - GEMINI_API_KEY is not set
    - The API returns an error
    """
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — returning degraded message.")
        return _DEGRADED_NO_KEY

    try:
        import google.generativeai as genai  # type: ignore[import]

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt,
        )
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return _DEGRADED_API_ERROR
