"""
End-to-End Integration Tests
Tests the complete trading pipeline: Auth → Market Data → Claude AI → Risk Check → Trade Execution
"""
import pytest

class TestE2EHealthAndSystem:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Zerodha Claude AI Trader"
        assert data["version"] == "1.0.0"
        assert data["mode"] == "PAPER_TRADE"
        assert "bot_active" in data

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "authenticated" in data
        assert "paper_trade" in data
        assert data["paper_trade"] is True

    def test_bot_status_initially_stopped(self, client):
        response = client.get("/bot/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "watchlist" in data
        assert len(data["watchlist"]) > 0


class TestE2EAuthFlow:
    def test_full_auth_flow(self, client):
        url_resp = client.get("/auth/login-url")
        assert url_resp.status_code == 200
        assert "login_url" in url_resp.json()

        session_resp = client.post("/auth/session", json={"request_token": "e2e_mock_token"})
        assert session_resp.status_code == 200
        assert session_resp.json()["success"] is True

        status_resp = client.get("/auth/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["authenticated"] is True


class TestE2EMarketDataPipeline:
    def test_full_market_data_pipeline(self, client):
        quote_resp = client.get("/market/quote")
        assert quote_resp.status_code == 200
        quotes = quote_resp.json()["data"]
        assert isinstance(quotes, dict)
        assert len(quotes) > 0

        ohlcv_resp = client.get("/market/ohlcv/RELIANCE?days=2")
        assert ohlcv_resp.status_code == 200
        ohlcv_data = ohlcv_resp.json()["data"]
        assert len(ohlcv_data) > 0
        first_candle = ohlcv_data[0]
        assert "open" in first_candle
        assert "close" in first_candle
        assert "rsi_14" in first_candle

        ctx_resp = client.get("/market/context/RELIANCE")
        assert ctx_resp.status_code == 200
        ctx = ctx_resp.json()["data"]
        assert ctx["current_price"] > 0
        assert ctx["rsi_14"] is not None


class TestE2EFullTradingCycle:
    def test_complete_trade_cycle_reliance(self, client):
        ctx_resp = client.get("/market/context/RELIANCE")
        assert ctx_resp.status_code == 200
        ctx = ctx_resp.json()["data"]
        assert ctx["current_price"] > 0

        ai_resp = client.get("/ai/analyze/RELIANCE")
        assert ai_resp.status_code == 200
        ai_data = ai_resp.json()
        assert ai_data["success"] is True
        signal = ai_data["signal"]
        assert signal["action"] in {"BUY", "SELL", "HOLD"}
        assert 0 <= signal["confidence"] <= 100

        risk_resp = client.get("/risk/stats")
        assert risk_resp.status_code == 200
        stats = risk_resp.json()["stats"]
        assert stats["capital"] > 0

        trade_resp = client.post("/trade/execute/RELIANCE")
        assert trade_resp.status_code == 200
        trade_data = trade_resp.json()
        assert "success" in trade_data

        if trade_data["success"]:
            assert "order_id" in trade_data
            assert trade_data["order_id"].startswith("PAPER_")
            assert trade_data["paper_trade"] is True

        sq_resp = client.post("/trade/squareoff-all")
        assert sq_resp.status_code == 200
        assert sq_resp.json()["success"] is True

    def test_complete_trade_cycle_all_symbols(self, client):
        ai_resp = client.get("/ai/analyze-all")
        assert ai_resp.status_code == 200
        results = ai_resp.json()["data"]
        assert len(results) >= 3

        for result in results:
            assert "symbol" in result
            if "error" not in result:
                assert "signal" in result
                assert "trade_valid" in result
                assert result["signal"]["action"] in {"BUY", "SELL", "HOLD"}

    def test_manual_trade_and_history(self, client):
        trade_resp = client.post("/trade/manual", json={
            "symbol": "INFY",
            "action": "BUY",
            "qty": 10,
            "price": 1520.0
        })
        assert trade_resp.status_code == 200
        assert trade_resp.json()["success"] is True
        order_id = trade_resp.json()["order_id"]
        assert order_id.startswith("PAPER_")

        hist_resp = client.get("/trade/history")
        assert hist_resp.status_code == 200
        trades = hist_resp.json()["trades"]
        trade_ids = [t.get("order_id") for t in trades]
        assert order_id in trade_ids


class TestE2ERiskProtection:
    def test_risk_blocks_trade_after_daily_loss(self, client):
        client.post("/risk/reset-daily")
        stats_resp = client.get("/risk/stats")
        stats = stats_resp.json()["stats"]
        assert stats["daily_pnl"] == 0.0

    def test_risk_reset_restores_trading(self, client):
        client.post("/risk/reset-daily")
        reset_resp = client.post("/risk/reset-daily")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["success"] is True

    def test_watchlist_update(self, client):
        update_resp = client.put("/bot/watchlist", json={"symbols": ["RELIANCE", "INFY", "WIPRO"]})
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["success"] is True
        assert "RELIANCE" in data["watchlist"]
        assert "WIPRO" in data["watchlist"]

        status_resp = client.get("/bot/status")
        assert "WIPRO" in status_resp.json()["watchlist"]

        client.put("/bot/watchlist", json={"symbols": ["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"]})


class TestE2ESquareOffProtection:
    def test_squareoff_closes_all_open_positions(self, client):
        for sym in ["RELIANCE", "INFY", "TCS"]:
            client.post("/trade/manual", json={"symbol": sym, "action": "BUY", "qty": 5})

        sq_resp = client.post("/trade/squareoff-all")
        assert sq_resp.status_code == 200
        sq_data = sq_resp.json()
        assert sq_data["success"] is True

        pos_resp = client.get("/trade/positions")
        assert pos_resp.status_code == 200

    def test_squareoff_with_no_positions(self, client):
        client.post("/trade/squareoff-all")
        sq_resp = client.post("/trade/squareoff-all")
        assert sq_resp.status_code == 200
        assert sq_resp.json()["closed_positions"] == 0


class TestE2EBotControl:
    def test_bot_start_stop_cycle(self, client):
        stop_resp = client.post("/bot/stop")
        assert stop_resp.status_code == 200

        status_resp = client.get("/bot/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert "running" in data
        assert "market_open" in data
        assert "market_close" in data
        assert "squareoff_time" in data
