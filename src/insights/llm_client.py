"""
Thin wrapper around the Groq chat completions API.

Gracefully degrades when no API key is configured.

Function: chat_completion(prompt, system_prompt) -> str
"""
from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger("insights.llm_client")

_DEGRADED_NO_KEY = (
    "AI insights unavailable. Set GROQ_API_KEY in .env to enable."
)
_DEGRADED_API_ERROR = "AI insights temporarily unavailable."

_DEFAULT_SYSTEM_PROMPT = "You are a helpful data analyst."


def chat_completion(
    prompt: str,
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
) -> str:
    """
    Call the Groq chat completions API and return the assistant reply.

    Parameters
    ----------
    prompt:
        User-facing message to send to the model.
    system_prompt:
        System-level instruction; defaults to a generic data-analyst persona.

    Returns
    -------
    str
        Model response text, or a degradation message if the key is missing
        or the API returns an error.
    """
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — returning degraded message.")
        return _DEGRADED_NO_KEY

    try:
        import groq  # type: ignore[import]

        client = groq.Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        content: str = response.choices[0].message.content.strip()
        return content

    except groq.APIError as exc:  # type: ignore[attr-defined]
        logger.error("Groq API error: %s", exc)
        return _DEGRADED_API_ERROR
