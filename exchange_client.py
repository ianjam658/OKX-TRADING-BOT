"""
Thin wrapper around ccxt so the rest of the bot never talks to the
exchange API directly. Makes it easy to swap exchanges or switch
sandbox/live mode from config alone.
"""

import logging
import time

import ccxt

from bot.config import config

logger = logging.getLogger("exchange")


class ExchangeClient:
    def __init__(self):
        exchange_class = getattr(ccxt, config.exchange_id)

        params = {
            "apiKey": config.api_key,
            "secret": config.api_secret,
            "enableRateLimit": True,
        }
        if config.exchange_id == "okx" and config.api_passphrase:
            params["password"] = config.api_passphrase

        self.exchange = exchange_class(params)

        if config.sandbox_mode:
            try:
                self.exchange.set_sandbox_mode(True)
                logger.info("Exchange sandbox mode ENABLED (%s)", config.exchange_id)
            except ccxt.NotSupported:
                logger.warning(
                    "%s ccxt integration has no sandbox mode; "
                    "falling back to DRY_RUN simulation only.",
                    config.exchange_id,
                )

    def fetch_balance_usd(self) -> float:
        """Returns available quote-currency (e.g. USDT) balance."""
        if config.dry_run:
            return None  # caller falls back to simulated balance
        balance = self.exchange.fetch_balance()
        quote = config.symbol.split("/")[1]
        return float(balance.get(quote, {}).get("free", 0.0))

    def fetch_ohlcv(self, limit: int = 100):
        """Returns OHLCV candles: [timestamp, open, high, low, close, volume]."""
        for attempt in range(3):
            try:
                return self.exchange.fetch_ohlcv(
                    config.symbol, timeframe=config.timeframe, limit=limit
                )
            except ccxt.NetworkError as e:
                logger.warning("Network error fetching OHLCV (attempt %d): %s", attempt + 1, e)
                time.sleep(2 ** attempt)
        raise RuntimeError("Failed to fetch OHLCV after retries")

    def create_market_order(self, side: str, amount_quote_usd: float, last_price: float):
        """
        Places a market order sized in quote currency (USD-ish), converting
        to base-asset amount using the last known price.
        """
        amount_base = amount_quote_usd / last_price

        if config.dry_run:
            logger.info(
                "[DRY RUN] Would place %s order: ~%.6f %s (~$%.2f)",
                side, amount_base, config.symbol.split("/")[0], amount_quote_usd,
            )
            return {"simulated": True, "side": side, "amount": amount_base, "price": last_price}

        try:
            order = self.exchange.create_order(
                symbol=config.symbol, type="market", side=side, amount=amount_base
            )
            logger.info("Order placed: %s", order)
            return order
        except ccxt.InsufficientFunds as e:
            logger.error("Insufficient funds for order: %s", e)
            return None
        except ccxt.BaseError as e:
            logger.error("Exchange error placing order: %s", e)
            return None
