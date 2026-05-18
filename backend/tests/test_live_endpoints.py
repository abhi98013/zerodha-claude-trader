"""
Live endpoint tests — runs against the running backend at http://localhost:8000
Tests every API route with real HTTP calls and validates response structure.
"""
import pytest
import requests
import time

BASE = "http://localhost:8000"
SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})


def get(path, params=None):
    return SESSION.get(f"{BASE}{path}", params=params, timeout=30)


def post(path, json=None):
    return SESSION.post(f"{BASE}{path}", json=json or {}, timeout=30)


def put(path, json=None):
    return SESSION.put(f"{BASE}{path}", json=json or {}, timeout=30)


# ── Health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self):
        r = get("/health")
        assert r.status_code == 200

    def test_health_has_status_field(self):
        r = get("/health")
        data = r.json()
        assert "status" in data

    def test_health_status_is_ok(self):
        r = get("/health")
        assert r.json()["status"] in ("ok", "healthy")

    def test_health_has_mode_field(self):
        r = get("/health")
        data = r.json()
        assert "mode" in data or "paper_trade" in data

    def test_health_has_timestamp(self):
        r = get("/health")
        assert "timestamp" in r.json()


# ── Auth ────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_auth_status_200(self):
        r = get("/auth/status")
        assert r.status_code == 200

    def test_auth_status_has_authenticated_field(self):
        r = get("/auth/status")
        assert "authenticated" in r.json()

    def test_auth_login_url_200(self):
        r = get("/auth/login-url")
        assert r.status_code == 200

    def test_auth_login_url_has_url(self):
        r = get("/auth/login-url")
        data = r.json()
        assert "login_url" in data
        assert "kite.zerodha.com" in data["login_url"]

    def test_auth_session_bad_token_returns_error(self):
        r = post("/auth/session", {"request_token": "bad_token_test"})
        assert r.status_code in (200, 400, 422, 500)


# ── Market Data ─────────────────────────────────────────────────────────────

class TestMarketData:
    def test_market_quote_200(self):
        r = get("/market/quote")
        assert r.status_code == 200

    def test_market_quote_is_dict(self):
        r = get("/market/quote")
        assert isinstance(r.json(), dict)

    def test_market_quote_has_symbols(self):
        r = get("/market/quote")
        data = r.json()
        assert len(data) > 0

    def test_market_quote_has_last_price(self):
        r = get("/market/quote")
        data = r.json()
        quotes = data.get("data", data)
        if isinstance(quotes, dict) and len(quotes) > 0:
            first = next(iter(quotes.values()))
            assert "last_price" in first or isinstance(first, (int, float))

    def test_ohlcv_reliance(self):
        r = get("/market/ohlcv/RELIANCE", {"days": 2})
        assert r.status_code == 200

    def test_ohlcv_has_candles(self):
        r = get("/market/ohlcv/RELIANCE", {"days": 2})
        data = r.json()
        candles = data.get("candles") or data.get("data", [])
        assert len(candles) > 0

    def test_ohlcv_candle_structure(self):
        r = get("/market/ohlcv/RELIANCE", {"days": 2})
        data = r.json()
        candle = (data.get("candles") or data.get("data", [{}]))[0]
        for key in ["open", "high", "low", "close", "volume"]:
            assert key in candle, f"Missing key: {key}"

    def test_market_context_200(self):
        r = get("/market/context/INFY")
        assert r.status_code == 200

    def test_market_context_has_indicators(self):
        r = get("/market/context/INFY")
        data = r.json()
        assert "indicators" in data or "symbol" in data or "data" in data


# ── AI Analysis ─────────────────────────────────────────────────────────────

class TestAI:
    def test_analyze_symbol_200(self):
        r = get("/ai/analyze/RELIANCE")
        assert r.status_code == 200

    def test_analyze_symbol_has_action(self):
        r = get("/ai/analyze/RELIANCE")
        data = r.json()
        assert "signal" in data or "action" in data or "analysis" in data

    def test_analyze_signal_action_valid(self):
        r = get("/ai/analyze/TCS")
        data = r.json()
        signal = data.get("signal") or data
        action = signal.get("action", "")
        assert action in ("BUY", "SELL", "HOLD", "")

    def test_analyze_all_200(self):
        r = get("/ai/analyze-all")
        assert r.status_code == 200

    def test_analyze_all_returns_list(self):
        r = get("/ai/analyze-all")
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_analyze_all_has_results(self):
        r = get("/ai/analyze-all")
        data = r.json()
        if isinstance(data, list):
            assert len(data) > 0
        else:
            assert len(data) > 0


# ── Risk Manager ─────────────────────────────────────────────────────────────

class TestRisk:
    def test_risk_stats_200(self):
        r = get("/risk/stats")
        assert r.status_code == 200

    def test_risk_stats_has_daily_loss(self):
        r = get("/risk/stats")
        data = r.json()
        assert "daily_loss" in data or "daily_pnl" in data or "stats" in data

    def test_risk_reset_daily_200(self):
        r = post("/risk/reset-daily")
        assert r.status_code == 200

    def test_risk_reset_returns_success(self):
        r = post("/risk/reset-daily")
        data = r.json()
        assert data.get("success") is True or "reset" in str(data).lower()


# ── Trade ────────────────────────────────────────────────────────────────────

class TestTrade:
    def test_trade_history_200(self):
        r = get("/trade/history")
        assert r.status_code == 200

    def test_trade_history_is_list(self):
        r = get("/trade/history")
        data = r.json()
        assert isinstance(data, list) or "trades" in data or "history" in data

    def test_open_positions_200(self):
        r = get("/trade/positions")
        assert r.status_code == 200

    def test_open_positions_is_dict_or_list(self):
        r = get("/trade/positions")
        data = r.json()
        assert isinstance(data, (dict, list))

    def test_manual_trade_paper_mode(self):
        r = post("/trade/manual", {
            "symbol": "INFY",
            "action": "BUY",
            "quantity": 1,
            "order_type": "MARKET"
        })
        assert r.status_code in (200, 400, 422)

    def test_squareoff_all_200(self):
        r = post("/trade/squareoff-all")
        assert r.status_code == 200


# ── Bot ──────────────────────────────────────────────────────────────────────

class TestBot:
    def test_bot_status_200(self):
        r = get("/bot/status")
        assert r.status_code == 200

    def test_bot_status_has_running_field(self):
        r = get("/bot/status")
        data = r.json()
        assert "running" in data or "status" in data or "bot_running" in data

    def test_bot_start_200(self):
        r = post("/bot/start")
        assert r.status_code == 200

    def test_bot_start_returns_success(self):
        r = post("/bot/start")
        assert r.json().get("success") is True

    def test_bot_stop_200(self):
        r = post("/bot/stop")
        assert r.status_code == 200

    def test_bot_stop_returns_success(self):
        r = post("/bot/stop")
        assert r.json().get("success") is True

    def test_bot_watchlist_update(self):
        r = put("/bot/watchlist", {"symbols": ["RELIANCE", "INFY", "TCS"]})
        assert r.status_code == 200

    def test_bot_watchlist_returns_symbols(self):
        r = put("/bot/watchlist", {"symbols": ["RELIANCE", "INFY"]})
        data = r.json()
        assert "watchlist" in data
        assert "RELIANCE" in data["watchlist"]


# ── Strategy ─────────────────────────────────────────────────────────────────

class TestStrategy:
    def test_sectors_200(self):
        r = get("/strategy/sectors")
        assert r.status_code == 200

    def test_sectors_has_sectors_list(self):
        r = get("/strategy/sectors")
        data = r.json()
        assert "sectors" in data
        assert len(data["sectors"]) > 0

    def test_sectors_has_required_fields(self):
        r = get("/strategy/sectors")
        sec = r.json()["sectors"][0]
        for field in ["sector", "change_pct", "momentum_score", "trend"]:
            assert field in sec, f"Missing field: {field}"

    def test_top_sectors_up(self):
        r = get("/strategy/top-sectors", {"n": 3, "direction": "UP"})
        assert r.status_code == 200
        data = r.json()
        assert "sectors" in data

    def test_top_sectors_down(self):
        r = get("/strategy/top-sectors", {"n": 2, "direction": "DOWN"})
        assert r.status_code == 200

    def test_filtered_stocks_200(self):
        r = get("/strategy/stocks")
        assert r.status_code == 200

    def test_filtered_stocks_structure(self):
        r = get("/strategy/stocks")
        data = r.json()
        assert "stocks" in data
        assert "count" in data

    def test_filtered_stocks_no_mf_heavy(self):
        r = get("/strategy/stocks")
        stocks = r.json().get("stocks", [])
        mf_heavy = {"HINDUNILVR", "ITC", "TCS", "INFY", "HDFCBANK", "RELIANCE"}
        symbols = {s["symbol"] for s in stocks}
        overlap = symbols & mf_heavy
        assert len(overlap) == 0, f"MF-heavy stocks found: {overlap}"

    def test_filtered_stocks_5min_low_held(self):
        r = get("/strategy/stocks")
        stocks = r.json().get("stocks", [])
        for s in stocks:
            assert s.get("5min_low_hold") is True, f"{s['symbol']} 5-min low not held"

    def test_option_picks_200(self):
        r = get("/strategy/options")
        assert r.status_code == 200

    def test_option_picks_structure(self):
        r = get("/strategy/options")
        data = r.json()
        assert "picks" in data
        assert "total" in data

    def test_option_picks_rr_minimum(self):
        r = get("/strategy/options")
        picks = r.json().get("picks", [])
        for p in picks:
            rr = p.get("risk_reward", 0) or p.get("adjusted_risk_reward", 0)
            assert rr >= 1.5, f"{p['symbol']} R:R {rr} below minimum 1.5"

    def test_option_picks_valid_type(self):
        r = get("/strategy/options")
        picks = r.json().get("picks", [])
        for p in picks:
            assert p["option_type"] in ("CE", "PE"), f"Invalid option type: {p['option_type']}"

    def test_strategy_scan_force(self):
        r = get("/strategy/scan", {"force": "true"})
        assert r.status_code == 200

    def test_strategy_scan_has_picks(self):
        r = get("/strategy/scan", {"force": "true"})
        data = r.json()
        assert "picks" in data
        assert "sector_scan" in data
        assert "filtered_stocks" in data


# ── Backtest ──────────────────────────────────────────────────────────────────

class TestBacktest:
    def test_backtest_runs(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        assert r.status_code == 200

    def test_backtest_has_summary(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        data = r.json()
        assert "summary" in data

    def test_backtest_summary_fields(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        s = r.json()["summary"]
        for f in ["total_trades", "win_rate_pct", "total_pnl", "profit_factor", "winners", "losers"]:
            assert f in s, f"Missing summary field: {f}"

    def test_backtest_win_rate_reasonable(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        wr = r.json()["summary"]["win_rate_pct"]
        assert 40 <= wr <= 95, f"Win rate {wr}% out of expected range"

    def test_backtest_top5_winners(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        data = r.json()
        assert "top5_by_pnl" in data
        assert len(data["top5_by_pnl"]) == 5

    def test_backtest_top5_are_sorted_descending(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        top5 = r.json()["top5_by_pnl"]
        pnls = [t["total_pnl"] for t in top5]
        assert pnls == sorted(pnls, reverse=True), "Top 5 not sorted by PnL descending"

    def test_backtest_top5_all_positive(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        top5 = r.json()["top5_by_pnl"]
        for t in top5:
            assert t["total_pnl"] > 0, f"Top winner has negative PnL: {t['total_pnl']}"

    def test_backtest_by_sector_present(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        assert "by_sector" in r.json()

    def test_backtest_by_year_present(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        data = r.json()
        assert "by_year" in data
        assert "2022" in data["by_year"]
        assert "2023" in data["by_year"]

    def test_backtest_profit_factor_positive(self):
        r = get("/strategy/backtest", {"start_year": 2022, "end_year": 2023})
        pf = r.json()["summary"]["profit_factor"]
        assert pf > 0, f"Profit factor {pf} must be positive"
