"""
This is where the 'survival' concept becomes an actual mechanic rather
than just narration: as the bot's balance falls, it takes smaller,
more cautious positions. If it hits the death threshold, it stops
trading entirely -- game over.
"""

from bot.config import config


class RiskManager:
    def __init__(self, starting_balance: float):
        self.starting_balance = starting_balance

    def danger_level(self, balance: float) -> str:
        """Returns a coarse danger bucket used for sizing and narration."""
        if balance <= config.death_balance_usd:
            return "dead"
        pct_of_start = balance / self.starting_balance
        if pct_of_start <= config.critical_balance_pct:
            return "critical"
        if pct_of_start <= 0.5:
            return "wounded"
        return "healthy"

    def is_dead(self, balance: float) -> bool:
        return balance <= config.death_balance_usd

    def position_size_usd(self, balance: float) -> float:
        """
        Position size shrinks as balance shrinks, so the bot naturally
        becomes more conservative the closer it gets to zero. Never
        risks more than max_risk_per_trade_pct of current balance,
        and never below the exchange's minimum tradeable amount.
        """
        danger = self.danger_level(balance)

        risk_pct = {
            "healthy": config.max_risk_per_trade_pct,
            "wounded": config.max_risk_per_trade_pct * 0.5,
            "critical": config.max_risk_per_trade_pct * 0.25,
            "dead": 0.0,
        }[danger]

        size = balance * risk_pct
        if size < config.min_trade_usd:
            return 0.0  # too small to trade -- sit this one out
        return min(size, balance)
