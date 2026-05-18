import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

MOCK_PRICES = {
    "RELIANCE": 2850.0,
    "INFY": 1520.0,
    "TCS": 3900.0,
    "HDFCBANK": 1680.0,
    "ICICIBANK": 1240.0,
    "NIFTY 50": 22500.0,
}

class MarketData:
    def __init__(self, kite=None, paper_trade: bool = True):
        self.kite = kite
        self.paper_trade = paper_trade

    def get_ohlcv(self, symbol: str, interval: str = "5minute", days: int = 5) -> pd.DataFrame:
        if self.paper_trade:
            return self._generate_mock_ohlcv(symbol, interval, days)

        instrument_token = self.get_instrument_token(symbol)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        data = self.kite.historical_data(instrument_token, from_date, to_date, interval)
        return pd.DataFrame(data)

    def _generate_mock_ohlcv(self, symbol: str, interval: str, days: int) -> pd.DataFrame:
        base_price = MOCK_PRICES.get(symbol, 1000.0)
        np.random.seed(hash(symbol) % 2**31)
        n = days * 75
        dates = pd.date_range(end=datetime.now(), periods=n, freq="5min")
        closes = base_price + np.cumsum(np.random.randn(n) * base_price * 0.002)
        highs = closes + np.abs(np.random.randn(n) * base_price * 0.003)
        lows = closes - np.abs(np.random.randn(n) * base_price * 0.003)
        opens = np.roll(closes, 1)
        opens[0] = base_price
        volumes = np.random.randint(10000, 500000, n)
        return pd.DataFrame({
            "date": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        })

    def get_instrument_token(self, symbol: str, exchange: str = "NSE") -> int:
        if self.paper_trade:
            mock_tokens = {
                "RELIANCE": 738561, "INFY": 408065, "TCS": 2953217,
                "HDFCBANK": 341249, "ICICIBANK": 1270529, "NIFTY 50": 256265,
            }
            return mock_tokens.get(symbol, 999999)

        instruments = self.kite.instruments(exchange)
        for i in instruments:
            if i["tradingsymbol"] == symbol:
                return i["instrument_token"]
        raise ValueError(f"Symbol {symbol} not found on {exchange}")

    def get_live_quote(self, symbols: list) -> dict:
        if self.paper_trade:
            return {
                s: {
                    "last_price": MOCK_PRICES.get(s, 1000.0) * (1 + np.random.randn() * 0.001),
                    "volume": np.random.randint(100000, 1000000),
                    "change": np.random.randn() * 0.5,
                }
                for s in symbols
            }
        return self.kite.quote([f"NSE:{s}" for s in symbols])

    def get_positions(self) -> dict:
        if self.paper_trade:
            return {"net": [], "day": []}
        return self.kite.positions()

    def get_margins(self) -> dict:
        if self.paper_trade:
            return {"equity": {"available": {"live_balance": 100000.0}}}
        return self.kite.margins()

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["ema_9"] = df["close"].ewm(span=9).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))
        df["volume_avg_20"] = df["volume"].rolling(20).mean()
        df["bb_mid"] = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_mid"] + 2 * std
        df["bb_lower"] = df["bb_mid"] - 2 * std
        return df
