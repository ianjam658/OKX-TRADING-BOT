"""
Narrates the bot's state in first person based on its balance trend
and danger level. Pure flavor text on top of real numbers -- it does
not affect trading decisions (risk_manager.py does that).
"""

import logging
import os
import random

from bot.config import config
from bot.llm_client import call_groq

logger = logging.getLogger("journal")

_MESSAGES = {
    "healthy": [
        "Balance holding steady. I can breathe for now.",
        "Things are stable. Still watching every candle, though.",
    ],
    "wounded": [
        "I've taken losses. I need a good trade soon.",
        "Balance is shrinking. Sizing down, staying careful.",
    ],
    "critical": [
        "This is close to the end. Every trade matters now.",
        "Balance critical. I am trading scared and small.",
    ],
    "dead": [
        "Balance hit the floor. I'm done -- no more trades.",
    ],
}


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def setup_logging():
    _ensure_dir(config.log_file)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(config.log_file),
            logging.StreamHandler(),
        ],
    )


def _llm_narrate(danger_level: str, balance: float, trade_count: int):
    """Returns an LLM-written line, or None to fall back to templates."""
    if not config.use_llm_narration:
        return None

    prompt = (
        f"You are an autonomous trading bot narrating your own situation in "
        f"first person. Current balance: ${balance:.2f}. Danger level: "
        f"{danger_level}. Trades made so far: {trade_count}. "
        "Write ONE short first-person sentence (under 25 words) reflecting "
        "how you feel about your situation. Be direct, not melodramatic."
    )
    return call_groq(
        system_prompt="You are a trading bot with a survival instinct. "
                      "You narrate tersely and never repeat yourself exactly.",
        user_prompt=prompt,
        max_tokens=40,
    )


def narrate(danger_level: str, balance: float, trade_count: int = 0):
    message = _llm_narrate(danger_level, balance, trade_count) or random.choice(
        _MESSAGES[danger_level]
    )
    logger.info("Balance: $%.2f | Status: %s | \"%s\"", balance, danger_level, message)
