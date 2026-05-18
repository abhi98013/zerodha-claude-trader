import pytest

REQUIRED_SIGNAL_KEYS = [
    "action", "confidence", "entry_price", "stop_loss",
    "target", "reasoning", "risk_reward_ratio", "position_size_multiplier"
]

VALID_ACTIONS = {"BUY", "SELL", "HOLD"}
VALID_MULTIPLIERS = {0.25, 0.5, 0.75, 1.0}

def build_mock_context(symbol="RELIANCE", rsi=45.0, price=2850.0):
    return {
        "symbol": symbol,
        "current_price": price,
        "open": price * 0.998,
        "high": price * 1.005,
        "low": price * 0.995,
        "volume": 250000,
        "volume_avg_20": 200000,
        "sma_20": price * 0.99,
        "sma_50": price * 0.985,
        "ema_9": price * 1.001,
        "rsi_14": rsi,
        "bb_upper": price * 1.02,
        "bb_lower": price * 0.98,
        "last_5_candles": [
            {"open": price*0.998, "high": price*1.003, "low": price*0.995, "close": price, "volume": 50000}
        ] * 5
    }

class TestClaudeAnalyzer:
    def test_analyzer_initializes_paper_trade(self, analyzer):
        assert analyzer.paper_trade is True
        assert analyzer.client is None

    def test_analyze_returns_dict(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        assert isinstance(signal, dict)

    def test_signal_has_all_required_keys(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        for key in REQUIRED_SIGNAL_KEYS:
            assert key in signal, f"Missing key: {key}"

    def test_signal_action_is_valid(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        assert signal["action"] in VALID_ACTIONS

    def test_signal_confidence_range(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        assert 0 <= signal["confidence"] <= 100

    def test_position_size_multiplier_is_valid(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        assert signal["position_size_multiplier"] in VALID_MULTIPLIERS

    def test_oversold_rsi_suggests_buy(self, analyzer):
        context = build_mock_context(rsi=28.0)
        signal = analyzer.analyze_trade_signal(context)
        assert signal["action"] in {"BUY", "HOLD"}

    def test_overbought_rsi_suggests_sell(self, analyzer):
        context = build_mock_context(rsi=75.0)
        signal = analyzer.analyze_trade_signal(context)
        assert signal["action"] in {"SELL", "HOLD"}

    def test_stop_loss_below_entry_for_buy(self, analyzer):
        context = build_mock_context(rsi=28.0)
        signal = analyzer.analyze_trade_signal(context)
        if signal["action"] == "BUY":
            assert signal["stop_loss"] < signal["entry_price"]

    def test_target_above_entry_for_buy(self, analyzer):
        context = build_mock_context(rsi=28.0)
        signal = analyzer.analyze_trade_signal(context)
        if signal["action"] == "BUY":
            assert signal["target"] > signal["entry_price"]

    def test_stop_loss_above_entry_for_sell(self, analyzer):
        context = build_mock_context(rsi=78.0)
        signal = analyzer.analyze_trade_signal(context)
        if signal["action"] == "SELL":
            assert signal["stop_loss"] > signal["entry_price"]

    def test_reasoning_is_string(self, analyzer):
        context = build_mock_context()
        signal = analyzer.analyze_trade_signal(context)
        assert isinstance(signal["reasoning"], str)
        assert len(signal["reasoning"]) > 0

    def test_multiple_symbols(self, analyzer):
        symbols = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"]
        for sym in symbols:
            context = build_mock_context(symbol=sym)
            signal = analyzer.analyze_trade_signal(context)
            assert signal["action"] in VALID_ACTIONS

    def test_exit_signal_returns_dict(self, analyzer):
        position = {
            "order_id": "PAPER_ABC123",
            "symbol": "RELIANCE",
            "action": "BUY",
            "entry_price": 2850.0,
            "qty": 10,
        }
        current_data = {"current_price": 2900.0}
        result = analyzer.analyze_exit_signal(position, current_data)
        assert isinstance(result, dict)
        assert "exit_now" in result
        assert "reason" in result
        assert "urgency" in result

    def test_exit_signal_profit_target(self, analyzer):
        position = {"symbol": "RELIANCE", "action": "BUY", "entry_price": 2850.0, "qty": 10}
        current_data = {"current_price": 2920.0}
        result = analyzer.analyze_exit_signal(position, current_data)
        assert isinstance(result["exit_now"], bool)

    def test_exit_signal_stop_loss_hit(self, analyzer):
        position = {"symbol": "RELIANCE", "action": "BUY", "entry_price": 2850.0, "qty": 10}
        current_data = {"current_price": 2810.0}
        result = analyzer.analyze_exit_signal(position, current_data)
        assert result["exit_now"] is True


class TestClaudeAnalyzerAPI:
    def test_analyze_symbol_endpoint(self, client):
        response = client.get("/ai/analyze/RELIANCE")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "signal" in data
        assert "context" in data
        assert "trade_valid" in data

    def test_analyze_symbol_signal_structure(self, client):
        response = client.get("/ai/analyze/INFY")
        data = response.json()
        signal = data["signal"]
        for key in REQUIRED_SIGNAL_KEYS:
            assert key in signal, f"Missing key: {key}"

    def test_analyze_all_endpoint(self, client):
        response = client.get("/ai/analyze-all")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_analyze_all_covers_watchlist(self, client):
        response = client.get("/ai/analyze-all")
        data = response.json()
        symbols = {item["symbol"] for item in data["data"] if "symbol" in item}
        assert len(symbols) >= 3
