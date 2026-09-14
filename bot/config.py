"""
Central configuration for the survival trading bot.
All values are pulled from environment variables so no secrets ever
live in the code or the git repo.
"""

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    return float(val) if val not in (None, "") else default


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val not in (None, "") else default


@dataclass
class Config:
    # Exchange credentials
    exchange_id: str = os.getenv("EXCHANGE_ID", "okx")
    api_key: str = os.getenv("API_KEY", "")
    api_secret: str = os.getenv("API_SECRET", "")
    api_passphrase: str = os.getenv("API_PASSPHRASE", "")  # required by OKX
    sandbox_mode: bool = _get_bool("SANDBOX_MODE", True)

    # Market / strategy
    symbol: str = os.getenv("SYMBOL", "BTC/USDT")
    timeframe: str = os.getenv("TIMEFRAME", "15m")
    fast_ma: int = _get_int("FAST_MA", 9)
    slow_ma: int = _get_int("SLOW_MA", 21)
    poll_interval_seconds: int = _get_int("POLL_INTERVAL_SECONDS", 60)

    # "Survival" economics
    starting_balance_usd: float = _get_float("STARTING_BALANCE_USD", 20.0)
    min_trade_usd: float = _get_float("MIN_TRADE_USD", 5.0)
    max_risk_per_trade_pct: float = _get_float("MAX_RISK_PER_TRADE_PCT", 0.25)
    critical_balance_pct: float = _get_float("CRITICAL_BALANCE_PCT", 0.25)
    death_balance_usd: float = _get_float("DEATH_BALANCE_USD", 1.0)

    # Ops
    dry_run: bool = _get_bool("DRY_RUN", True)  # simulate orders, no real trades
    state_file: str = os.getenv("STATE_FILE", "data/state.json")
    log_file: str = os.getenv("LOG_FILE", "data/journal.log")

    # Optional LLM layer (Groq). Off by default. Sentiment can only
    # veto a trade, never invent one -- see strategy.combine_with_sentiment.
    # Narration is pure flavor text and never affects trading decisions.
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    use_llm_sentiment: bool = _get_bool("USE_LLM_SENTIMENT", False)
    use_llm_narration: bool = _get_bool("USE_LLM_NARRATION", False)
    groq_min_interval_seconds: int = _get_int("GROQ_MIN_INTERVAL_SECONDS", 300)

    def validate(self) -> None:
        missing = []
        if not self.dry_run:
            if not self.api_key:
                missing.append("API_KEY")
            if not self.api_secret:
                missing.append("API_SECRET")
            if self.exchange_id == "okx" and not self.api_passphrase:
                missing.append("API_PASSPHRASE")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


config = Config()
