import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ZERODHA_API_KEY", "test_api_key")
os.environ.setdefault("ZERODHA_API_SECRET", "test_api_secret")
os.environ.setdefault("ZERODHA_USER_ID", "TEST001")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
os.environ.setdefault("PAPER_TRADE", "true")
os.environ.setdefault("RISK_PER_TRADE", "1.0")
os.environ.setdefault("MAX_DAILY_LOSS", "3.0")

from fastapi.testclient import TestClient
from main import app
from auth.zerodha_auth import ZerodhaAuth
from data.market_data import MarketData
from ai.claude_analyzer import ClaudeAnalyzer
from risk.risk_manager import RiskManager
from execution.trade_executor import TradeExecutor

@pytest.fixture(scope="session")
def client():
    os.makedirs("logs", exist_ok=True)
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth():
    return ZerodhaAuth(paper_trade=True)

@pytest.fixture
def market_data():
    return MarketData(paper_trade=True)

@pytest.fixture
def analyzer():
    return ClaudeAnalyzer(paper_trade=True)

@pytest.fixture
def risk_manager(market_data):
    return RiskManager(market_data=market_data)

@pytest.fixture
def executor():
    return TradeExecutor(paper_trade=True)

@pytest.fixture
def sample_signal_buy():
    return {
        "action": "BUY",
        "confidence": 82,
        "entry_price": 2850.0,
        "stop_loss": 2815.0,
        "target": 2920.0,
        "reasoning": "RSI oversold, price above SMA20, high volume",
        "risk_reward_ratio": 2.0,
        "position_size_multiplier": 1.0,
    }

@pytest.fixture
def sample_signal_hold():
    return {
        "action": "HOLD",
        "confidence": 55,
        "entry_price": None,
        "stop_loss": 2800.0,
        "target": 2900.0,
        "reasoning": "Mixed signals",
        "risk_reward_ratio": 0,
        "position_size_multiplier": 0.5,
    }

@pytest.fixture
def sample_signal_low_confidence():
    return {
        "action": "BUY",
        "confidence": 60,
        "entry_price": 2850.0,
        "stop_loss": 2820.0,
        "target": 2890.0,
        "reasoning": "Weak signal",
        "risk_reward_ratio": 1.33,
        "position_size_multiplier": 0.25,
    }
