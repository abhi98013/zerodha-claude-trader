import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ZERODHA_API_KEY: str = os.getenv("ZERODHA_API_KEY", "")
    ZERODHA_API_SECRET: str = os.getenv("ZERODHA_API_SECRET", "")
    ZERODHA_USER_ID: str = os.getenv("ZERODHA_USER_ID", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    RISK_PER_TRADE: float = float(os.getenv("RISK_PER_TRADE", "1.0"))
    MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "3.0"))
    PAPER_TRADE: bool = os.getenv("PAPER_TRADE", "true").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CLAUDE_MODEL: str = "claude-opus-4-5"
    CONFIDENCE_THRESHOLD: int = 70
    MARKET_OPEN: str = "09:20"
    MARKET_CLOSE: str = "15:15"
    SQUAREOFF_TIME: str = "15:10"
    WATCHLIST: list = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"]
    DEFAULT_LOT_SIZE: int = int(os.getenv("DEFAULT_LOT_SIZE", "500"))

settings = Settings()
