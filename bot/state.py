"""
Very small JSON-file state store. Good enough for a single-instance
bot. Note: on Render's free tier, disk is NOT guaranteed to persist
across deploys/restarts -- see README for options if you need durable
state (a free Postgres instance, or an external key-value store).
"""

import json
import os

from bot.config import config


def load_state() -> dict:
    if not os.path.exists(config.state_file):
        return {
            "balance_usd": config.starting_balance_usd,
            "is_dead": False,
            "trade_count": 0,
            "last_acted_signal": None,
        }
    with open(config.state_file, "r") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    d = os.path.dirname(config.state_file)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(config.state_file, "w") as f:
        json.dump(state, f, indent=2)
