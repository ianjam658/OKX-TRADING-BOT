"""
The bot's heartbeat: fetch data -> decide -> size position -> trade ->
journal -> persist state -> sleep -> repeat. Designed to run forever
in a background thread inside app.py.
"""

import logging
import time

from bot.config import config
from bot.exchange_client import ExchangeClient
from bot.journal import narrate, setup_logging
from bot.risk_manager import RiskManager
from bot.sentiment import get_market_sentiment
from bot.state import load_state, save_state
from bot.strategy import combine_with_sentiment, generate_signal

logger = logging.getLogger("main_loop")

_running = True  # flips to False for graceful shutdown


def stop():
    global _running
    _running = False


def run_forever():
    setup_logging()
    config.validate()

    client = ExchangeClient()
    risk = RiskManager(starting_balance=config.starting_balance_usd)
    state = load_state()

    logger.info(
        "Bot starting. dry_run=%s sandbox=%s symbol=%s starting_balance=$%.2f",
        config.dry_run, config.sandbox_mode, config.symbol, state["balance_usd"],
    )

    while _running:
        try:
            _tick(client, risk, state)
        except Exception:
            logger.exception("Unhandled error in main loop tick -- continuing")
        time.sleep(config.poll_interval_seconds)


def _tick(client: ExchangeClient, risk: RiskManager, state: dict):
    if state.get("is_dead"):
        # Already dead -- stay dead. No trading, no exceptions.
        return

    # Balance: use real exchange balance in live mode, simulated in dry run.
    live_balance = client.fetch_balance_usd()
    balance = live_balance if live_balance is not None else state["balance_usd"]

    danger = risk.danger_level(balance)
    narrate(danger, balance, state.get("trade_count", 0))

    if risk.is_dead(balance):
        state["balance_usd"] = balance
        state["is_dead"] = True
        save_state(state)
        logger.warning("Balance depleted below death threshold. Bot has died.")
        return

    ohlcv = client.fetch_ohlcv()
    last_price = ohlcv[-1][4]
    signal = generate_signal(ohlcv)

    sentiment = get_market_sentiment()  # 'neutral' if disabled/unavailable
    signal = combine_with_sentiment(signal, sentiment)
    if sentiment != "neutral":
        logger.info("Sentiment read: %s (signal after filter: %s)", sentiment, signal)

    if signal in ("buy", "sell"):
        # Second safety net: even a real crossover should only be acted
        # on once. If the last tick already traded this exact signal
        # and nothing has changed since, skip it -- this catches any
        # edge case beyond the closed-candle fix in strategy.py.
        if signal == state.get("last_acted_signal"):
            logger.info("Signal %s unchanged since last trade -- skipping duplicate.", signal)
        else:
            size_usd = risk.position_size_usd(balance)
            if size_usd > 0:
                result = client.create_market_order(signal, size_usd, last_price)
                if result is not None:
                    state["trade_count"] = state.get("trade_count", 0) + 1
                    state["last_acted_signal"] = signal
                    logger.info("Trade #%d executed: %s $%.2f", state["trade_count"], signal, size_usd)
            else:
                logger.info("Signal was %s but position size too small to act on.", signal)
    elif signal == "hold":
        # A hold clears the guard so the NEXT real buy/sell (in either
        # direction) is always allowed through.
        state["last_acted_signal"] = None

    state["balance_usd"] = balance
    save_state(state)
