"""
Options Selector — Strategy Rule 5
For filtered stocks, select the best CE or PE option strike to trade.
Rules:
- BUY CE if sector trend is UP/STRONG_UP + 5-min low holding
- BUY PE if sector trend is DOWN/STRONG_DOWN
- Strike: ATM or 1 strike OTM for better R:R
- Expiry: nearest weekly expiry
- Target: 40-80% of premium, SL: 25-30% of premium
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

STOCK_LOT_SIZES = {
    "INFY": 400, "TCS": 150, "HCLTECH": 350, "WIPRO": 1500, "TECHM": 600,
    "LTIM": 75, "PERSISTENT": 125, "COFORGE": 100,
    "HDFCBANK": 550, "ICICIBANK": 700, "AXISBANK": 625, "KOTAKBANK": 200,
    "SBIN": 1500, "BANDHANBNK": 5000, "FEDERALBNK": 5000,
    "TATASTEEL": 5500, "JSWSTEEL": 600, "HINDALCO": 1075, "VEDL": 2000,
    "SAIL": 6000, "NMDC": 3500, "NATIONALUM": 8000,
    "MARUTI": 100, "TATAMOTORS": 2850, "M&M": 175,
    "RELIANCE": 250, "ONGC": 1975, "NTPC": 2625,
    "BAJFINANCE": 125, "BAJAJFINSV": 500,
    "SUNPHARMA": 700, "DRREDDY": 125, "CIPLA": 650,
    "DLF": 1650, "GODREJPROP": 425,
}

MOCK_OPTION_PRICES = {
    "COFORGE": {"price": 1850.0, "atm_ce": 45.0, "atm_pe": 38.0},
    "PERSISTENT": {"price": 2200.0, "atm_ce": 52.0, "atm_pe": 44.0},
    "LTIM": {"price": 3100.0, "atm_ce": 68.0, "atm_pe": 58.0},
    "TECHM": {"price": 1450.0, "atm_ce": 32.0, "atm_pe": 28.0},
    "FEDERALBNK": {"price": 195.0, "atm_ce": 4.5, "atm_pe": 3.8},
    "BANDHANBNK": {"price": 185.0, "atm_ce": 4.2, "atm_pe": 3.5},
    "AXISBANK": {"price": 1120.0, "atm_ce": 25.0, "atm_pe": 21.0},
    "NATIONALUM": {"price": 215.0, "atm_ce": 5.2, "atm_pe": 4.4},
    "NMDC": {"price": 240.0, "atm_ce": 5.8, "atm_pe": 4.9},
    "SAIL": {"price": 130.0, "atm_ce": 3.2, "atm_pe": 2.7},
}


class OptionsSelector:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade

    def get_nearest_expiry(self) -> str:
        today = datetime.now()
        days_to_thursday = (3 - today.weekday()) % 7
        if days_to_thursday == 0 and today.hour >= 15:
            days_to_thursday = 7
        expiry = today + timedelta(days=days_to_thursday)
        return expiry.strftime("%d%b%Y").upper()

    def get_atm_strike(self, price: float, step: int = 50) -> int:
        return round(price / step) * step

    def select_option(self, stock: Dict, kite=None) -> Optional[Dict]:
        symbol = stock.get("symbol", "")
        trend = stock.get("sector_trend", "UP")
        change_pct = stock.get("change_pct", 0)

        option_type = "CE" if "UP" in trend else "PE"

        price = self._get_price(symbol, kite)
        if price == 0:
            return None

        step = self._get_strike_step(price)
        atm_strike = self.get_atm_strike(price, step)

        if option_type == "CE":
            strike = atm_strike + step
        else:
            strike = atm_strike - step

        premium = self._get_option_premium(symbol, option_type, strike, kite)
        lot_size = STOCK_LOT_SIZES.get(symbol, settings.DEFAULT_LOT_SIZE)
        expiry = self.get_nearest_expiry()

        target_pct = 0.50 if abs(change_pct) >= 1.5 else 0.40
        sl_pct = 0.30

        target_premium = round(premium * (1 + target_pct), 2)
        sl_premium = round(premium * (1 - sl_pct), 2)

        cost_per_lot = round(premium * lot_size, 2)
        max_profit_per_lot = round((target_premium - premium) * lot_size, 2)
        max_loss_per_lot = round((premium - sl_premium) * lot_size, 2)
        risk_reward = round(max_profit_per_lot / max(max_loss_per_lot, 1), 2)

        option_symbol = f"{symbol}{expiry}{strike}{option_type}"

        return {
            "symbol": symbol,
            "option_symbol": option_symbol,
            "option_type": option_type,
            "strike": strike,
            "expiry": expiry,
            "premium": premium,
            "lot_size": lot_size,
            "target_premium": target_premium,
            "sl_premium": sl_premium,
            "cost_per_lot": cost_per_lot,
            "max_profit_per_lot": max_profit_per_lot,
            "max_loss_per_lot": max_loss_per_lot,
            "risk_reward": risk_reward,
            "underlying_price": price,
            "atm_strike": atm_strike,
            "sector": stock.get("sector"),
            "sector_trend": trend,
            "filter_score": stock.get("filter_score", 0),
            "filter_reasons": stock.get("filter_reasons", []),
            "5min_low_hold": stock.get("5min_low_hold", True),
            "tradeable": risk_reward >= 1.5,
        }

    def _get_price(self, symbol: str, kite=None) -> float:
        if self.paper_trade or kite is None:
            return MOCK_OPTION_PRICES.get(symbol, {}).get("price", 1000.0)
        try:
            quote = kite.quote(f"NSE:{symbol}")
            return float(quote[f"NSE:{symbol}"]["last_price"])
        except Exception as e:
            logger.warning(f"Price fetch failed for {symbol}: {e}")
            return MOCK_OPTION_PRICES.get(symbol, {}).get("price", 1000.0)

    def _get_strike_step(self, price: float) -> int:
        if price < 100:   return 5
        if price < 500:   return 10
        if price < 1000:  return 20
        if price < 2000:  return 50
        if price < 5000:  return 100
        return 200

    def _get_option_premium(self, symbol: str, option_type: str, strike: int, kite=None) -> float:
        if self.paper_trade or kite is None:
            data = MOCK_OPTION_PRICES.get(symbol, {})
            base = data.get("atm_ce", 40.0) if option_type == "CE" else data.get("atm_pe", 35.0)
            return round(base * 0.85, 2)
        try:
            expiry = self.get_nearest_expiry()
            opt_sym = f"NFO:{symbol}{expiry}{strike}{option_type}"
            quote = kite.quote(opt_sym)
            return float(quote[opt_sym]["last_price"])
        except Exception as e:
            logger.warning(f"Option premium fetch failed: {e}")
            data = MOCK_OPTION_PRICES.get(symbol, {})
            return data.get("atm_ce", 40.0) if option_type == "CE" else data.get("atm_pe", 35.0)

    def select_best_options(self, filtered_stocks: List[Dict], kite=None, max_picks: int = 3) -> List[Dict]:
        options = []
        for stock in filtered_stocks:
            opt = self.select_option(stock, kite)
            if opt and opt["tradeable"]:
                options.append(opt)

        options.sort(key=lambda x: (x["risk_reward"] * x["filter_score"]), reverse=True)
        return options[:max_picks]
