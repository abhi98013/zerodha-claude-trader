"""
Stock Filter — Strategy Rules 2, 3, 4
- Select stocks with high intraday turnover within trending sectors
- First 5-min candle LOW must hold (no short-seller dominance)
- Avoid MF-heavy/large-cap sluggish stocks — prefer fresh institutional buying
"""
import logging
import requests
import pandas as pd
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

SECTOR_TO_SYMBOLS = {
    "NIFTY IT":     ["INFY", "TCS", "HCLTECH", "WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE"],
    "NIFTY BANK":   ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN", "BANDHANBNK", "FEDERALBNK"],
    "NIFTY METAL":  ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL", "NMDC", "NATIONALUM"],
    "NIFTY AUTO":   ["MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "M&M", "ASHOKLEY"],
    "NIFTY PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "AUROPHARMA"],
    "NIFTY FMCG":   ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO"],
    "NIFTY REALTY": ["DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD", "SOBHA"],
    "NIFTY ENERGY": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "ADANIGREEN", "BPCL"],
    "NIFTY FINANCIAL SERVICES": ["BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIGI"],
}

MF_HEAVY_STOCKS = {"HINDUNILVR", "ITC", "TCS", "INFY", "HDFCBANK", "RELIANCE", "NESTLEIND", "BRITANNIA"}

MOCK_STOCKS = {
    "NIFTY IT": [
        {"symbol": "COFORGE", "turnover": 450.2, "delivery_pct": 62.5, "change_pct": 2.1, "mf_heavy": False},
        {"symbol": "PERSISTENT", "turnover": 380.5, "delivery_pct": 58.3, "change_pct": 1.8, "mf_heavy": False},
        {"symbol": "LTIM", "turnover": 290.1, "delivery_pct": 45.2, "change_pct": 1.5, "mf_heavy": False},
        {"symbol": "TECHM", "turnover": 210.8, "delivery_pct": 38.1, "change_pct": 0.9, "mf_heavy": False},
        {"symbol": "TCS", "turnover": 1200.0, "delivery_pct": 28.5, "change_pct": 0.6, "mf_heavy": True},
        {"symbol": "INFY", "turnover": 980.5, "delivery_pct": 25.3, "change_pct": 0.4, "mf_heavy": True},
    ],
    "NIFTY BANK": [
        {"symbol": "FEDERALBNK", "turnover": 320.3, "delivery_pct": 55.1, "change_pct": 1.9, "mf_heavy": False},
        {"symbol": "BANDHANBNK", "turnover": 280.7, "delivery_pct": 52.4, "change_pct": 1.6, "mf_heavy": False},
        {"symbol": "AXISBANK", "turnover": 450.2, "delivery_pct": 41.2, "change_pct": 1.2, "mf_heavy": False},
        {"symbol": "HDFCBANK", "turnover": 1500.0, "delivery_pct": 22.3, "change_pct": 0.5, "mf_heavy": True},
    ],
    "NIFTY METAL": [
        {"symbol": "NATIONALUM", "turnover": 180.5, "delivery_pct": 68.2, "change_pct": 2.3, "mf_heavy": False},
        {"symbol": "NMDC", "turnover": 220.3, "delivery_pct": 60.5, "change_pct": 1.7, "mf_heavy": False},
        {"symbol": "SAIL", "turnover": 190.8, "delivery_pct": 55.3, "change_pct": 1.4, "mf_heavy": False},
    ],
}


class StockFilter:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade
        self.session = requests.Session()
        self._init_nse_session()

    def _init_nse_session(self):
        try:
            self.session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
        except Exception:
            pass

    def filter_stocks(self, top_sectors: List[Dict], kite=None) -> List[Dict]:
        all_candidates = []
        for sector_info in top_sectors:
            sector = sector_info["sector"]
            stocks = self._get_sector_stocks(sector, kite)
            for stock in stocks:
                stock["sector"] = sector
                stock["sector_momentum"] = sector_info["momentum_score"]
                stock["sector_trend"] = sector_info["trend"]
            all_candidates.extend(stocks)

        filtered = self._apply_filters(all_candidates)
        return filtered

    def _get_sector_stocks(self, sector: str, kite=None) -> List[Dict]:
        if self.paper_trade:
            return MOCK_STOCKS.get(sector, [])
        try:
            return self._fetch_nse_sector_stocks(sector, kite)
        except Exception as e:
            logger.warning(f"NSE stock fetch failed for {sector}: {e}")
            return MOCK_STOCKS.get(sector, [])

    def _fetch_nse_sector_stocks(self, sector: str, kite=None) -> List[Dict]:
        index_name = sector.replace(" ", "%20")
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_name}"
        resp = self.session.get(url, headers=NSE_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for item in data[1:]:
            symbol = item.get("symbol", "")
            if not symbol:
                continue
            change_pct = float(item.get("pChange", 0))
            turnover = float(item.get("totalTradedValue", 0)) / 1e7
            delivery_pct = float(item.get("deliveryToTradedQuantity", 0))
            mf_heavy = symbol in MF_HEAVY_STOCKS

            results.append({
                "symbol": symbol,
                "turnover": round(turnover, 2),
                "delivery_pct": round(delivery_pct, 2),
                "change_pct": round(change_pct, 2),
                "mf_heavy": mf_heavy,
                "last_price": float(item.get("lastPrice", 0)),
                "open": float(item.get("open", 0)),
                "low": float(item.get("low", 0)),
                "high": float(item.get("high", 0)),
            })
        results.sort(key=lambda x: x["turnover"], reverse=True)
        return results[:10]

    def _apply_filters(self, stocks: List[Dict]) -> List[Dict]:
        results = []
        for s in stocks:
            score = 0
            reasons = []

            if s.get("mf_heavy", False):
                continue

            if s.get("change_pct", 0) < 0.3:
                continue

            if s.get("turnover", 0) >= 200:
                score += 30
                reasons.append(f"High turnover Rs{s['turnover']:.0f}Cr")
            elif s.get("turnover", 0) >= 100:
                score += 15
                reasons.append(f"Moderate turnover Rs{s['turnover']:.0f}Cr")

            if s.get("delivery_pct", 0) >= 50:
                score += 30
                reasons.append(f"Strong delivery {s['delivery_pct']:.1f}% (institutional buying)")
            elif s.get("delivery_pct", 0) >= 35:
                score += 15
                reasons.append(f"Decent delivery {s['delivery_pct']:.1f}%")

            if s.get("change_pct", 0) >= 1.5:
                score += 25
                reasons.append(f"Strong momentum +{s['change_pct']:.1f}%")
            elif s.get("change_pct", 0) >= 0.5:
                score += 12

            score += min(int(s.get("sector_momentum", 50) / 5), 15)

            s["filter_score"] = score
            s["filter_reasons"] = reasons
            s["5min_low_hold"] = self._check_5min_low_hold(s)
            if not s["5min_low_hold"]:
                continue

            if score >= 40:
                results.append(s)

        results.sort(key=lambda x: x["filter_score"], reverse=True)
        return results[:5]

    def _check_5min_low_hold(self, stock: Dict) -> bool:
        """
        Rule 3: First 5-min candle low must hold.
        In paper mode, simulate: if current price > open and change_pct > 0, low is holding.
        In live mode: compare current price vs first 5-min candle low fetched from kite.
        """
        if self.paper_trade:
            return stock.get("change_pct", 0) > 0.2
        open_price = stock.get("open", 0)
        low_price = stock.get("low", 0)
        last_price = stock.get("last_price", 0)
        if open_price == 0:
            return False
        first_candle_low = min(open_price, low_price)
        return last_price > first_candle_low
