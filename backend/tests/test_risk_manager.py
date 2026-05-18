import pytest

class TestRiskManager:
    def test_get_capital_paper_trade(self, risk_manager):
        capital = risk_manager.get_capital()
        assert capital > 0
        assert isinstance(capital, float)

    def test_calculate_position_size_basic(self, risk_manager):
        qty = risk_manager.calculate_position_size(100000, 2850, 2815, 1.0)
        assert qty > 0
        assert isinstance(qty, int)

    def test_calculate_position_size_zero_risk(self, risk_manager):
        qty = risk_manager.calculate_position_size(100000, 2850, 2850, 1.0)
        assert qty == 0

    def test_calculate_position_size_multiplier(self, risk_manager):
        qty_full = risk_manager.calculate_position_size(100000, 2850, 2815, 1.0)
        qty_half = risk_manager.calculate_position_size(100000, 2850, 2815, 0.5)
        assert qty_half < qty_full

    def test_is_trade_allowed_initial(self, risk_manager):
        allowed, msg = risk_manager.is_trade_allowed()
        assert allowed is True
        assert isinstance(msg, str)

    def test_is_trade_not_allowed_after_loss_limit(self, risk_manager):
        risk_manager.set_mock_capital(100000)
        risk_manager.daily_pnl = -3500.0
        allowed, msg = risk_manager.is_trade_allowed()
        assert allowed is False
        assert "loss" in msg.lower() or "limit" in msg.lower()

    def test_is_trade_not_allowed_after_max_trades(self, risk_manager):
        risk_manager.daily_trades = 10
        allowed, msg = risk_manager.is_trade_allowed()
        assert allowed is False

    def test_validate_signal_good(self, risk_manager, sample_signal_buy):
        valid, msg = risk_manager.validate_signal(sample_signal_buy)
        assert valid is True

    def test_validate_signal_hold(self, risk_manager, sample_signal_hold):
        valid, msg = risk_manager.validate_signal(sample_signal_hold)
        assert valid is False
        assert isinstance(msg, str) and len(msg) > 0

    def test_validate_signal_low_confidence(self, risk_manager, sample_signal_low_confidence):
        valid, msg = risk_manager.validate_signal(sample_signal_low_confidence)
        assert valid is False

    def test_validate_signal_low_rr(self, risk_manager):
        signal = {
            "action": "BUY",
            "confidence": 80,
            "risk_reward_ratio": 1.2,
        }
        valid, msg = risk_manager.validate_signal(signal)
        assert valid is False
        assert "R:R" in msg or "risk" in msg.lower()

    def test_update_pnl(self, risk_manager):
        initial_pnl = risk_manager.daily_pnl
        risk_manager.update_pnl(500.0)
        assert risk_manager.daily_pnl == initial_pnl + 500.0
        assert risk_manager.daily_trades == 1

    def test_update_pnl_negative(self, risk_manager):
        risk_manager.update_pnl(-300.0)
        assert risk_manager.daily_pnl < 0

    def test_reset_daily(self, risk_manager):
        risk_manager.daily_pnl = -1000.0
        risk_manager.daily_trades = 5
        risk_manager.reset_daily()
        assert risk_manager.daily_pnl == 0.0
        assert risk_manager.daily_trades == 0

    def test_get_stats_structure(self, risk_manager):
        stats = risk_manager.get_stats()
        required = ["daily_pnl", "daily_trades", "capital", "max_daily_loss_amount", "remaining_risk"]
        for key in required:
            assert key in stats, f"Missing stat: {key}"

    def test_position_size_risk_1_percent(self, risk_manager):
        capital = 100000
        entry = 1000.0
        stop_loss = 990.0
        qty = risk_manager.calculate_position_size(capital, entry, stop_loss, 1.0)
        risk_amount = qty * abs(entry - stop_loss)
        assert risk_amount <= capital * 0.015

    def test_position_size_minimum_1(self, risk_manager):
        qty = risk_manager.calculate_position_size(1000, 50000, 49990, 0.25)
        assert qty >= 1


class TestRiskManagerAPI:
    def test_risk_stats_endpoint(self, client):
        response = client.get("/risk/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data

    def test_risk_stats_values(self, client):
        response = client.get("/risk/stats")
        stats = response.json()["stats"]
        assert stats["capital"] > 0
        assert isinstance(stats["daily_pnl"], float)
        assert isinstance(stats["daily_trades"], int)

    def test_reset_daily_endpoint(self, client):
        response = client.post("/risk/reset-daily")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
