"""
Sector Scanner — Strategy Rule 1
Scan NSE sectoral indices 9:15–10:00 AM to find strongest trending sectors.
Ranks sectors by momentum: % change, candle direction, volume surge.
"""
import logging
import requests
import pandas as pd
from datetime import datetime, time
from typing import List, Dict

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

SECTORAL_INDICES = [
    "NIFTY AUTO", "NIFTY BANK", "NIFTY ENERGY", "NIFTY FINANCIAL SERVICES",
    "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL",
    "NIFTY PHARMA", "NIFTY PSU BANK", "NIFTY REALTY", "NIFTY HEALTHCARE INDEX",
    "NIFTY CONSUMER DURABLES", "NIFTY OIL AND GAS", "NIFTY MIDSMALL IT AND TELECOM",
]

MOCK_SECTOR_DATA = [
    {"sector": "NIFTY IT",     "change_pct": 1.85, "momentum_score": 92, "trend": "STRONG_UP",   "volume_surge": 2.1},
    {"sector": "NIFTY BANK",   "change_pct": 1.20, "momentum_score": 78, "trend": "UP",          "volume_surge": 1.6},
    {"sector": "NIFTY METAL",  "change_pct": 0.95, "momentum_score": 71, "trend": "UP",          "volume_surge": 1.4},
    {"sector": "NIFTY AUTO",   "change_pct": 0.60, "momentum_score": 58, "trend": "UP",          "volume_surge": 1.2},
    {"sector": "NIFTY PHARMA", "change_pct": 0.45, "momentum_score": 55, "trend": "WEAK_UP",     "volume_surge": 1.1},
    {"sector": "NIFTY FMCG",   "change_pct": -0.75, "momentum_score": 30, "trend": "DOWN",       "volume_surge": 0.8},
    {"sector": "NIFTY REALTY", "change_pct": -1.10, "momentum_score": 18, "trend": "STRONG_DOWN", "volume_surge": 1.3},
]


class SectorScanner:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade
        self.session = requests.Session()
        self._init_nse_session()

    def _init_nse_session(self):
        try:
            self.session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
        except Exception:
            pass

    def is_early_session(self) -> bool:
        now = datetime.now().time()
        return time(9, 15) <= now <= time(10, 0)

    def get_sector_momentum(self) -> List[Dict]:
        if self.paper_trade:
            return self._mock_sector_data()
        try:
            return self._fetch_nse_sector_data()
        except Exception as e:
            logger.warning(f"NSE fetch failed, using mock: {e}")
            return self._mock_sector_data()

    def _fetch_nse_sector_data(self) -> List[Dict]:
        url = "https://www.nseindia.com/api/allIndices"
        resp = self.session.get(url, headers=NSE_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for item in data:
            name = item.get("index", "")
            if name not in SECTORAL_INDICES:
                continue
            change_pct = float(item.get("percentChange", 0))
            last = float(item.get("last", 0))
            prev = float(item.get("previousClose", 1))
            volume_surge = round(float(item.get("turnover", 0)) / max(float(item.get("previousTurnover", 1)), 1), 2)

            momentum_score = self._compute_momentum_score(change_pct, volume_surge)
            trend = self._classify_trend(change_pct)

            results.append({
                "sector": name,
                "change_pct": round(change_pct, 2),
                "last": round(last, 2),
                "prev_close": round(prev, 2),
                "momentum_score": momentum_score,
                "trend": trend,
                "volume_surge": round(volume_surge, 2),
            })

        results.sort(key=lambda x: x["momentum_score"], reverse=True)
        return results

    def _compute_momentum_score(self, change_pct: float, volume_surge: float) -> int:
        score = 50
        score += min(change_pct * 10, 30)
        score += min((volume_surge - 1.0) * 20, 20)
        return max(0, min(100, int(score)))

    def _classify_trend(self, change_pct: float) -> str:
        if change_pct >= 1.5:   return "STRONG_UP"
        if change_pct >= 0.5:   return "UP"
        if change_pct >= 0.1:   return "WEAK_UP"
        if change_pct >= -0.1:  return "FLAT"
        if change_pct >= -0.5:  return "WEAK_DOWN"
        if change_pct >= -1.5:  return "DOWN"
        return "STRONG_DOWN"

    def _mock_sector_data(self) -> List[Dict]:
        import random
        results = []
        for s in MOCK_SECTOR_DATA:
            noise = round(random.uniform(-0.1, 0.1), 2)
            chg = round(s["change_pct"] + noise, 2)
            results.append({
                "sector": s["sector"],
                "change_pct": chg,
                "last": round(10000 + chg * 100, 2),
                "prev_close": 10000.0,
                "momentum_score": self._compute_momentum_score(chg, s["volume_surge"]),
                "trend": self._classify_trend(chg),
                "volume_surge": s["volume_surge"],
            })
        results.sort(key=lambda x: x["momentum_score"], reverse=True)
        return results

    def get_top_sectors(self, n: int = 3, direction: str = "UP") -> List[Dict]:
        all_sectors = self.get_sector_momentum()
        if direction == "UP":
            up = [s for s in all_sectors if "UP" in s["trend"]]
            # Always return at least top-n even if weak
            return (up if up else all_sectors)[:n]
        elif direction == "DOWN":
            down = [s for s in all_sectors if "DOWN" in s["trend"]]
            return (down if down else [])[:n]
        return all_sectors[:n]
