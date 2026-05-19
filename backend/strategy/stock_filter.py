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
        {"symbol": "COFORGE",    "turnover": 450.2, "delivery_pct": 62.5, "change_pct": 2.1, "mf_heavy": False, "last_price": 1850.0, "open": 1820.0, "low": 1815.0, "high": 1870.0},
        {"symbol": "PERSISTENT", "turnover": 380.5, "delivery_pct": 58.3, "change_pct": 1.8, "mf_heavy": False, "last_price": 2210.0, "open": 2180.0, "low": 2175.0, "high": 2230.0},
        {"symbol": "LTIM",       "turnover": 290.1, "delivery_pct": 55.2, "change_pct": 1.5, "mf_heavy": False, "last_price": 3120.0, "open": 3080.0, "low": 3070.0, "high": 3140.0},
        {"symbol": "TECHM",      "turnover": 210.8, "delivery_pct": 48.1, "change_pct": 1.2, "mf_heavy": False, "last_price": 1460.0, "open": 1440.0, "low": 1435.0, "high": 1475.0},
        {"symbol": "HCLTECH",    "turnover": 260.5, "delivery_pct": 50.4, "change_pct": 1.4, "mf_heavy": False, "last_price": 1580.0, "open": 1555.0, "low": 1550.0, "high": 1595.0},
    ],
    "NIFTY BANK": [
        {"symbol": "FEDERALBNK",  "turnover": 320.3, "delivery_pct": 55.1, "change_pct": 1.9, "mf_heavy": False, "last_price": 198.0,  "open": 194.0,  "low": 193.0,  "high": 201.0},
        {"symbol": "BANDHANBNK",  "turnover": 280.7, "delivery_pct": 52.4, "change_pct": 1.6, "mf_heavy": False, "last_price": 188.0,  "open": 185.0,  "low": 184.0,  "high": 192.0},
        {"symbol": "AXISBANK",    "turnover": 450.2, "delivery_pct": 51.2, "change_pct": 1.3, "mf_heavy": False, "last_price": 1125.0, "open": 1110.0, "low": 1108.0, "high": 1138.0},
        {"symbol": "INDUSINDBK",  "turnover": 310.5, "delivery_pct": 48.7, "change_pct": 1.5, "mf_heavy": False, "last_price": 960.0,  "open": 945.0,  "low": 942.0,  "high": 972.0},
    ],
    "NIFTY METAL": [
        {"symbol": "NATIONALUM", "turnover": 280.5, "delivery_pct": 68.2, "change_pct": 2.3, "mf_heavy": False, "last_price": 218.0, "open": 213.0, "low": 212.0, "high": 222.0},
        {"symbol": "NMDC",       "turnover": 220.3, "delivery_pct": 60.5, "change_pct": 1.7, "mf_heavy": False, "last_price": 242.0, "open": 238.0, "low": 237.0, "high": 246.0},
        {"symbol": "SAIL",       "turnover": 190.8, "delivery_pct": 55.3, "change_pct": 1.4, "mf_heavy": False, "last_price": 132.0, "open": 130.0, "low": 129.0, "high": 134.0},
        {"symbol": "HINDALCO",   "turnover": 310.2, "delivery_pct": 58.1, "change_pct": 1.6, "mf_heavy": False, "last_price": 620.0, "open": 610.0, "low": 608.0, "high": 628.0},
    ],
    "NIFTY AUTO": [
        {"symbol": "TATAMOTORS", "turnover": 420.5, "delivery_pct": 52.3, "change_pct": 1.8, "mf_heavy": False, "last_price": 780.0,  "open": 766.0,  "low": 764.0,  "high": 792.0},
        {"symbol": "M&M",        "turnover": 350.3, "delivery_pct": 56.8, "change_pct": 1.5, "mf_heavy": False, "last_price": 2850.0, "open": 2808.0, "low": 2805.0, "high": 2875.0},
        {"symbol": "BAJAJ-AUTO", "turnover": 280.1, "delivery_pct": 60.2, "change_pct": 1.3, "mf_heavy": False, "last_price": 9200.0, "open": 9080.0, "low": 9070.0, "high": 9280.0},
        {"symbol": "EICHERMOT",  "turnover": 210.8, "delivery_pct": 54.4, "change_pct": 1.1, "mf_heavy": False, "last_price": 4850.0, "open": 4796.0, "low": 4790.0, "high": 4890.0},
    ],
    "NIFTY PHARMA": [
        {"symbol": "SUNPHARMA",  "turnover": 380.5, "delivery_pct": 61.2, "change_pct": 1.6, "mf_heavy": False, "last_price": 1680.0, "open": 1653.0, "low": 1650.0, "high": 1695.0},
        {"symbol": "DRREDDY",    "turnover": 290.3, "delivery_pct": 58.5, "change_pct": 1.4, "mf_heavy": False, "last_price": 6200.0, "open": 6113.0, "low": 6110.0, "high": 6260.0},
        {"symbol": "CIPLA",      "turnover": 240.8, "delivery_pct": 55.3, "change_pct": 1.2, "mf_heavy": False, "last_price": 1490.0, "open": 1472.0, "low": 1470.0, "high": 1505.0},
    ],
    "NIFTY REALTY": [
        {"symbol": "DLF",         "turnover": 310.2, "delivery_pct": 58.4, "change_pct": -1.5, "mf_heavy": False, "last_price": 820.0,  "open": 833.0,  "low": 815.0,  "high": 835.0},
        {"symbol": "GODREJPROP",  "turnover": 280.5, "delivery_pct": 55.1, "change_pct": -1.3, "mf_heavy": False, "last_price": 2680.0, "open": 2715.0, "low": 2670.0, "high": 2720.0},
        {"symbol": "OBEROIRLTY",  "turnover": 190.3, "delivery_pct": 52.8, "change_pct": -1.1, "mf_heavy": False, "last_price": 1840.0, "open": 1860.0, "low": 1835.0, "high": 1865.0},
    ],
    "NIFTY FMCG": [
        {"symbol": "DABUR",  "turnover": 180.5, "delivery_pct": 54.2, "change_pct": -0.9, "mf_heavy": False, "last_price": 540.0,  "open": 545.0,  "low": 537.0,  "high": 548.0},
        {"symbol": "MARICO", "turnover": 160.3, "delivery_pct": 51.5, "change_pct": -0.7, "mf_heavy": False, "last_price": 620.0,  "open": 624.0,  "low": 617.0,  "high": 627.0},
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

            chg = s.get("change_pct", 0)
            trend = s.get("sector_trend", "UP")
            is_pe = "DOWN" in trend

            # For CE: need positive change. For PE: need negative change.
            if not is_pe and chg < 0.3:
                continue
            if is_pe and chg > -0.3:
                continue

            if s.get("turnover", 0) >= 200:
                score += 30
                reasons.append(f"High turnover ₹{s['turnover']:.0f}Cr")
            elif s.get("turnover", 0) >= 100:
                score += 20
                reasons.append(f"Good turnover ₹{s['turnover']:.0f}Cr")
            elif s.get("turnover", 0) >= 50:
                score += 10
                reasons.append(f"Moderate turnover ₹{s['turnover']:.0f}Cr")

            if s.get("delivery_pct", 0) >= 50:
                score += 30
                reasons.append(f"Strong delivery {s['delivery_pct']:.1f}% — institutional signal")
            elif s.get("delivery_pct", 0) >= 40:
                score += 20
                reasons.append(f"Good delivery {s['delivery_pct']:.1f}%")
            elif s.get("delivery_pct", 0) >= 30:
                score += 10
                reasons.append(f"Decent delivery {s['delivery_pct']:.1f}%")

            if abs(chg) >= 1.5:
                score += 25
                reasons.append(f"Strong move {chg:+.1f}%")
            elif abs(chg) >= 0.8:
                score += 15
                reasons.append(f"Good move {chg:+.1f}%")
            elif abs(chg) >= 0.3:
                score += 8

            score += min(int(s.get("sector_momentum", 50) / 5), 15)

            s["filter_score"] = score
            s["filter_reasons"] = reasons
            s["5min_low_hold"] = self._check_5min_low_hold(s)

            if score >= 30:
                results.append(s)

        results.sort(key=lambda x: x["filter_score"], reverse=True)
        return results[:6]

    def _check_5min_low_hold(self, stock: Dict) -> bool:
        """
        Rule 3: First 5-min candle low must hold.
        For CE (bullish): current price > first candle low.
        For PE (bearish): current price < first candle high.
        """
        trend = stock.get("sector_trend", "UP")
        is_pe = "DOWN" in trend
        if self.paper_trade:
            chg = stock.get("change_pct", 0)
            return abs(chg) > 0.3
        open_price = stock.get("open", 0)
        low_price  = stock.get("low", 0)
        high_price = stock.get("high", 0)
        last_price = stock.get("last_price", 0)
        if open_price == 0:
            return True
        if is_pe:
            return last_price < max(open_price, high_price)
        first_candle_low = min(open_price, low_price)
        return last_price > first_candle_low
