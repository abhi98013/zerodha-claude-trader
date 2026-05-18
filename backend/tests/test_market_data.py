import pytest
import pandas as pd
import numpy as np

class TestMarketData:
    def test_get_ohlcv_returns_dataframe(self, market_data):
        df = market_data.get_ohlcv("RELIANCE", interval="5minute", days=2)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_ohlcv_has_required_columns(self, market_data):
        df = market_data.get_ohlcv("INFY", interval="5minute", days=1)
        required_cols = ["open", "high", "low", "close", "volume"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_ohlcv_price_sanity(self, market_data):
        df = market_data.get_ohlcv("TCS", interval="5minute", days=2)
        assert (df["high"] >= df["low"]).all(), "High must be >= Low"
        assert (df["close"] > 0).all(), "Close prices must be positive"
        assert (df["volume"] >= 0).all(), "Volume must be non-negative"

    def test_get_instrument_token(self, market_data):
        token = market_data.get_instrument_token("RELIANCE")
        assert isinstance(token, int)
        assert token > 0

    def test_get_instrument_token_unknown_symbol(self, market_data):
        token = market_data.get_instrument_token("UNKNOWN_XYZ")
        assert isinstance(token, int)

    def test_get_live_quote(self, market_data):
        quotes = market_data.get_live_quote(["RELIANCE", "INFY"])
        assert isinstance(quotes, dict)
        assert "RELIANCE" in quotes
        assert "INFY" in quotes

    def test_live_quote_has_price(self, market_data):
        quotes = market_data.get_live_quote(["TCS"])
        assert "last_price" in quotes["TCS"]
        assert quotes["TCS"]["last_price"] > 0

    def test_get_positions_paper_trade(self, market_data):
        positions = market_data.get_positions()
        assert isinstance(positions, dict)
        assert "net" in positions
        assert "day" in positions

    def test_get_margins_paper_trade(self, market_data):
        margins = market_data.get_margins()
        assert "equity" in margins
        assert margins["equity"]["available"]["live_balance"] > 0

    def test_compute_indicators(self, market_data):
        df = market_data.get_ohlcv("HDFCBANK", days=5)
        df = market_data.compute_indicators(df)
        indicator_cols = ["sma_20", "sma_50", "ema_9", "rsi_14", "bb_upper", "bb_lower"]
        for col in indicator_cols:
            assert col in df.columns, f"Missing indicator: {col}"

    def test_rsi_range(self, market_data):
        df = market_data.get_ohlcv("ICICIBANK", days=5)
        df = market_data.compute_indicators(df)
        valid_rsi = df["rsi_14"].dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all(), "RSI must be 0-100"

    def test_bollinger_bands_ordering(self, market_data):
        df = market_data.get_ohlcv("RELIANCE", days=5)
        df = market_data.compute_indicators(df)
        valid = df.dropna(subset=["bb_upper", "bb_lower"])
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()

    def test_multiple_symbols(self, market_data):
        symbols = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK"]
        for sym in symbols:
            df = market_data.get_ohlcv(sym, days=1)
            assert len(df) > 0, f"No data for {sym}"


class TestMarketDataAPI:
    def test_get_quotes_endpoint(self, client):
        response = client.get("/market/quote")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_ohlcv_endpoint(self, client):
        response = client.get("/market/ohlcv/RELIANCE")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["symbol"] == "RELIANCE"
        assert len(data["data"]) > 0

    def test_get_ohlcv_endpoint_case_insensitive(self, client):
        response = client.get("/market/ohlcv/reliance")
        assert response.status_code == 200

    def test_get_market_context_endpoint(self, client):
        response = client.get("/market/context/INFY")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        ctx = data["data"]
        required = ["symbol", "current_price", "rsi_14", "sma_20", "volume"]
        for field in required:
            assert field in ctx, f"Missing field: {field}"

    def test_market_context_price_validity(self, client):
        response = client.get("/market/context/TCS")
        data = response.json()
        ctx = data["data"]
        assert ctx["current_price"] > 0
        assert ctx["high"] >= ctx["low"]
        assert 0 <= ctx["rsi_14"] <= 100
