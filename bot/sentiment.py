"""
Optional secondary signal: reads recent crypto headlines from a public
RSS feed and asks the LLM for a rough bullish/bearish/neutral read.

This is NOT a prediction engine. It is one noisy extra input that can
VETO a trade the MA-crossover strategy already wants to make -- it
never invents a trade on its own. If disabled, or if anything fails
(network error, bad response, missing key), it returns 'neutral',
which has zero effect on the underlying strategy.
"""

import logging
import re

import requests

from bot.config import config
from bot.llm_client import call_groq

logger = logging.getLogger("sentiment")

RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"


def _fetch_headlines(limit: int = 8):
    try:
        resp = requests.get(RSS_URL, timeout=10)
        resp.raise_for_status()
        titles = re.findall(r"<title>(.*?)</title>", resp.text)
        # The first <title> match is usually the feed's own title, not a headline.
        return titles[1:limit + 1]
    except Exception as e:
        logger.warning("Failed to fetch headlines: %s", e)
        return []


def get_market_sentiment() -> str:
    """
    Returns 'bullish', 'bearish', or 'neutral'.
    Defaults to 'neutral' whenever the feature is off or anything
    fails -- 'neutral' never blocks or forces a trade on its own.
    """
    if not config.use_llm_sentiment:
        return "neutral"

    headlines = _fetch_headlines()
    if not headlines:
        return "neutral"

    prompt = (
        "Here are recent crypto news headlines:\n"
        + "\n".join(f"- {h}" for h in headlines)
        + "\n\nBased ONLY on these headlines, is near-term Bitcoin sentiment "
          "bullish, bearish, or neutral? Reply with exactly one word: "
          "bullish, bearish, or neutral."
    )
    result = call_groq(
        system_prompt="You are a terse crypto market sentiment classifier. "
                       "You are cautious and often say neutral when headlines are mixed.",
        user_prompt=prompt,
        max_tokens=5,
    )
    if not result:
        return "neutral"

    result = result.lower()
    if "bullish" in result:
        return "bullish"
    if "bearish" in result:
        return "bearish"
    return "neutral"
