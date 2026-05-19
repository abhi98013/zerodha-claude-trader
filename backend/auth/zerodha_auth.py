import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

ACCESS_TOKEN_FILE = ".access_token"

class ZerodhaAuth:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade
        self.kite = None
        self._access_token: Optional[str] = None
        self._mock_instruments = self._generate_mock_instruments()

        if not paper_trade:
            try:
                from kiteconnect import KiteConnect
                from config.settings import settings
                if not settings.ZERODHA_API_KEY:
                    raise ValueError("ZERODHA_API_KEY is not set in .env")
                self.kite = KiteConnect(api_key=settings.ZERODHA_API_KEY)
                logger.info(f"KiteConnect initialized for user, API key: {settings.ZERODHA_API_KEY[:6]}...")
            except ImportError as e:
                logger.error(f"kiteconnect not installed: {e}. Run: pip install kiteconnect")
                self.paper_trade = True
            except Exception as e:
                logger.error(f"KiteConnect init failed: {e}")
                self.paper_trade = True

    def _generate_mock_instruments(self):
        return [
            {"tradingsymbol": "RELIANCE", "instrument_token": 738561, "exchange": "NSE"},
            {"tradingsymbol": "INFY", "instrument_token": 408065, "exchange": "NSE"},
            {"tradingsymbol": "TCS", "instrument_token": 2953217, "exchange": "NSE"},
            {"tradingsymbol": "HDFCBANK", "instrument_token": 341249, "exchange": "NSE"},
            {"tradingsymbol": "ICICIBANK", "instrument_token": 1270529, "exchange": "NSE"},
            {"tradingsymbol": "NIFTY 50", "instrument_token": 256265, "exchange": "NSE"},
        ]

    def get_login_url(self) -> str:
        if self.paper_trade:
            return "https://kite.zerodha.com/connect/login?mock=true&paper_trade=true"
        return self.kite.login_url()

    def generate_session(self, request_token: str) -> dict:
        if self.paper_trade:
            mock_token = f"mock_access_token_{datetime.now().strftime('%Y%m%d')}"
            self._access_token = mock_token
            self._save_token(mock_token)
            return {"access_token": mock_token, "user_id": "MOCK_USER", "paper_trade": True}

        from config.settings import settings
        data = self.kite.generate_session(request_token, api_secret=settings.ZERODHA_API_SECRET)
        self._access_token = data["access_token"]
        self.kite.set_access_token(self._access_token)
        self._save_token(self._access_token)
        return data

    def load_existing_session(self) -> bool:
        if os.path.exists(ACCESS_TOKEN_FILE):
            with open(ACCESS_TOKEN_FILE) as f:
                data = json.load(f)
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                self._access_token = data["token"]
                if not self.paper_trade and self.kite:
                    self.kite.set_access_token(self._access_token)
                return True
        return False

    def _save_token(self, token: str):
        with open(ACCESS_TOKEN_FILE, "w") as f:
            json.dump({"token": token, "date": datetime.now().strftime("%Y-%m-%d")}, f)

    def is_authenticated(self) -> bool:
        return self._access_token is not None

    def get_access_token(self) -> Optional[str]:
        return self._access_token
