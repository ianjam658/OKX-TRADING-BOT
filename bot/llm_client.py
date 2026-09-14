"""
Thin wrapper around Groq's OpenAI-compatible chat completions API.
Used optionally for (1) reading crypto news sentiment as a secondary
signal, and (2) writing more varied 'survival' journal narration.

Every call is wrapped so a missing key, network error, or bad
response NEVER crashes the bot -- it just returns None and callers
fall back to their non-LLM behavior. The LLM is decoration/advice
here, never a single point of failure for trading.

A simple cooldown throttles how often Groq is actually called. With
sentiment + narration both wired in, calling every single poll tick
(as often as once a minute) can exceed Groq's free-tier rate limits,
which just produces noisy 429 log spam for no benefit -- narration
text doesn't need to change every 60 seconds anyway.
"""

import logging
import time

import requests

from bot.config import config

logger = logging.getLogger("llm_client")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_last_call_at = 0.0


def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 60):
    global _last_call_at

    if not config.groq_api_key:
        return None

    elapsed = time.monotonic() - _last_call_at
    if elapsed < config.groq_min_interval_seconds:
        return None  # cooldown active -- skip silently, caller falls back

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {config.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.groq_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=10,
        )
        _last_call_at = time.monotonic()  # counts even toward failed calls, avoids hammering during an outage
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("Groq call failed, falling back to non-LLM behavior: %s", e)
        return None
