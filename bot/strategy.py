"""
Simple, transparent trend-following strategy: moving-average crossover.
Deliberately kept simple and readable -- swap this module out once you
want something more sophisticated. The rest of the bot doesn't care
how the signal is generated, only that it gets 'buy' / 'sell' / 'hold'.
"""

from bot.config import config


def _sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def generate_signal(ohlcv) -> str:
    """
    ohlcv: list of [timestamp, open, high, low, close, volume], oldest first.
    Returns 'buy', 'sell', or 'hold'.
    """
    closes = [candle[4] for candle in ohlcv]

    fast = _sma(closes, config.fast_ma)
    slow = _sma(closes, config.slow_ma)
    prev_fast = _sma(closes[:-1], config.fast_ma)
    prev_slow = _sma(closes[:-1], config.slow_ma)

    if None in (fast, slow, prev_fast, prev_slow):
        return "hold"  # not enough data yet

    crossed_up = prev_fast <= prev_slow and fast > slow
    crossed_down = prev_fast >= prev_slow and fast < slow

    if crossed_up:
        return "buy"
    if crossed_down:
        return "sell"
    return "hold"


def combine_with_sentiment(signal: str, sentiment: str) -> str:
    """
    Sentiment is an advisor, never the decision-maker: it can only
    VETO a signal that directly conflicts with it (downgrade to
    'hold'). It can never turn a 'hold' into a trade, and it never
    strengthens a signal that already agrees with it. This keeps the
    core MA-crossover strategy in charge and the LLM as a filter.
    """
    if signal == "buy" and sentiment == "bearish":
        return "hold"
    if signal == "sell" and sentiment == "bullish":
        return "hold"
    return signal
