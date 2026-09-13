"""
Thin wrapper around Groq's OpenAI-compatible chat completions API.
Used optionally for (1) reading crypto news sentiment as a secondary
signal, and (2) writing more varied 'survival' journal narration.

Every call is wrapped so a missing key, network error, or bad
response NEVER crashes the bot -- it just returns None and callers
fall back to their non-LLM behavior. The LLM is decoration/advice
here, never a single point of failure for trading.
"""

import logging

import requests

from bot.config import config

logger = logging.getLogger("llm_client")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 60):
    if not config.groq_api_key:
        return None
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
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("Groq call failed, falling back to non-LLM behavior: %s", e)
        return None
