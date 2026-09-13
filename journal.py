"""
Narrates the bot's state in first person based on its balance trend
and danger level. Pure flavor text on top of real numbers -- it does
not affect trading decisions (risk_manager.py does that).
"""

import logging
import os
import random

from bot.config import config

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


def narrate(danger_level: str, balance: float):
    message = random.choice(_MESSAGES[danger_level])
    logger.info("Balance: $%.2f | Status: %s | \"%s\"", balance, danger_level, message)
