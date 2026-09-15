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
        config.dry_run, config.sandbox_mode, config.symbol, state.get("balance_usd", config.starting_balance_usd),
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

    # Price is needed to value the simulated portfolio in dry-run mode,
    # so fetch it before computing balance (unlike before, when balance
    # was computed first using a flat number that never actually moved).
    ohlcv = client.fetch_ohlcv()
    last_price = ohlcv[-1][4]

    live_balance = client.fetch_balance_usd()
    if live_balance is not None:
        # Live mode: the exchange's own balance is the source of truth.
        balance = live_balance
    else:
        # Dry-run mode: value the simulated portfolio (USD + BTC held)
        # at the current price. This is what makes balance actually
        # move with wins/losses instead of staying flat forever.
        balance = state["usd_held"] + state["btc_held"] * last_price

    danger = risk.danger_level(balance)
    narrate(danger, balance, state.get("trade_count", 0))

    if risk.is_dead(balance):
        state["balance_usd"] = balance
        state["is_dead"] = True
        save_state(state)
        logger.warning("Balance depleted below death threshold. Bot has died.")
        return

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
            executed_usd = 0.0

            if live_balance is not None:
                # Live: let the real order determine what actually happened.
                if size_usd > 0:
                    result = client.create_market_order(signal, size_usd, last_price)
                    if result is not None:
                        executed_usd = size_usd
            else:
                # Dry run: actually move simulated USD <-> BTC so the
                # portfolio's value can genuinely go up or down.
                if signal == "buy":
                    spend = min(size_usd, state["usd_held"])
                    if spend >= config.min_trade_usd:
                        state["usd_held"] -= spend
                        state["btc_held"] += spend / last_price
                        executed_usd = spend
                else:  # sell
                    btc_value_held = state["btc_held"] * last_price
                    sell_value = min(size_usd, btc_value_held)
                    if sell_value >= config.min_trade_usd:
                        btc_to_sell = sell_value / last_price
                        state["btc_held"] -= btc_to_sell
                        state["usd_held"] += sell_value
                        executed_usd = sell_value
                if executed_usd > 0:
                    client.create_market_order(signal, executed_usd, last_price)  # just logs in dry run

            if executed_usd > 0:
                state["trade_count"] = state.get("trade_count", 0) + 1
                state["last_acted_signal"] = signal
                logger.info("Trade #%d executed: %s $%.2f", state["trade_count"], signal, executed_usd)
            else:
                logger.info("Signal was %s but not enough held asset / size too small to act on.", signal)
    elif signal == "hold":
        # A hold clears the guard so the NEXT real buy/sell (in either
        # direction) is always allowed through.
        state["last_acted_signal"] = None

    # Recompute balance after any trade so it reflects the post-trade
    # portfolio, not the pre-trade snapshot from the top of this tick.
    if live_balance is None:
        balance = state["usd_held"] + state["btc_held"] * last_price
    state["balance_usd"] = balance
    save_state(state)
