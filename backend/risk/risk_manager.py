import logging
from typing import Optional, Tuple
from config.settings import settings

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, market_data=None):
        self.market_data = market_data
        self.risk_per_trade = settings.RISK_PER_TRADE / 100
        self.max_daily_loss = settings.MAX_DAILY_LOSS / 100
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_trades = 10
        self._capital = 100000.0

    def get_capital(self) -> float:
        if self.market_data:
            try:
                margins = self.market_data.get_margins()
                return margins["equity"]["available"]["live_balance"]
            except Exception as e:
                logger.warning(f"Could not fetch capital: {e}")
        return self._capital

    def set_mock_capital(self, capital: float):
        self._capital = capital

    def calculate_position_size(self, capital: float, entry: float, stop_loss: float, multiplier: float = 1.0) -> int:
        risk_amount = capital * self.risk_per_trade * multiplier
        risk_per_share = abs(entry - stop_loss)
        if risk_per_share == 0:
            return 0
        qty = int(risk_amount / risk_per_share)
        return max(1, qty)

    def is_trade_allowed(self) -> Tuple[bool, str]:
        capital = self.get_capital()
        if self.daily_pnl <= -(capital * self.max_daily_loss):
            msg = f"Daily loss limit hit (PnL: ₹{self.daily_pnl:.2f}). No more trades today."
            logger.warning(msg)
            return False, msg
        if self.daily_trades >= self.max_daily_trades:
            msg = f"Max daily trades ({self.max_daily_trades}) reached."
            logger.warning(msg)
            return False, msg
        return True, "Trade allowed"

    def validate_signal(self, signal: dict) -> Tuple[bool, str]:
        if signal.get("risk_reward_ratio", 0) < 1.5:
            return False, f"R:R too low ({signal.get('risk_reward_ratio')}). Minimum 1.5 required."
        if signal.get("confidence", 0) < settings.CONFIDENCE_THRESHOLD:
            return False, f"Confidence too low ({signal.get('confidence')}%). Minimum {settings.CONFIDENCE_THRESHOLD}% required."
        if signal.get("action") == "HOLD":
            return False, "Signal is HOLD - no trade."
        return True, "Signal validated"

    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl
        self.daily_trades += 1
        logger.info(f"PnL updated: ₹{pnl:.2f} | Daily PnL: ₹{self.daily_pnl:.2f} | Trades: {self.daily_trades}")

    def reset_daily(self):
        self.daily_pnl = 0.0
        self.daily_trades = 0
        logger.info("Daily PnL and trade count reset.")

    def get_stats(self) -> dict:
        return {
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_trades": self.daily_trades,
            "capital": round(self.get_capital(), 2),
            "max_daily_loss_amount": round(self.get_capital() * self.max_daily_loss, 2),
            "remaining_risk": round(self.get_capital() * self.max_daily_loss + self.daily_pnl, 2),
        }
