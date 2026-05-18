import pytest

class TestTradeExecutor:
    def test_executor_initializes_paper_trade(self, executor):
        assert executor.paper_trade is True
        assert executor.kite is None

    def test_place_market_order(self, executor):
        order_id = executor.place_order("RELIANCE", "BUY", 10)
        assert order_id.startswith("PAPER_")
        assert len(order_id) > 6

    def test_place_sell_order(self, executor):
        order_id = executor.place_order("INFY", "SELL", 5)
        assert order_id.startswith("PAPER_")

    def test_place_limit_order_with_price(self, executor):
        order_id = executor.place_order("TCS", "BUY", 2, order_type="LIMIT", price=3900.0)
        assert order_id.startswith("PAPER_")

    def test_place_bracket_order(self, executor):
        order_id = executor.place_bracket_order("RELIANCE", "BUY", 10, 2850.0, 2815.0, 2920.0)
        assert order_id.startswith("PAPER_")

    def test_bracket_order_creates_position(self, executor):
        order_id = executor.place_bracket_order("HDFCBANK", "BUY", 5, 1680.0, 1660.0, 1720.0)
        positions = executor.get_open_positions()
        assert order_id in positions

    def test_position_has_correct_fields(self, executor):
        order_id = executor.place_bracket_order("INFY", "BUY", 8, 1520.0, 1500.0, 1560.0)
        pos = executor.get_open_positions()[order_id]
        assert pos["symbol"] == "INFY"
        assert pos["action"] == "BUY"
        assert pos["qty"] == 8
        assert pos["entry_price"] == 1520.0
        assert pos["stop_loss"] == 1500.0
        assert pos["target"] == 1560.0
        assert pos["status"] == "OPEN"

    def test_close_position_profit(self, executor):
        order_id = executor.place_bracket_order("TCS", "BUY", 5, 3900.0, 3860.0, 3980.0)
        result = executor.close_position(order_id, 3960.0)
        assert result["status"] == "CLOSED"
        assert result["pnl"] == pytest.approx(300.0, abs=1)
        assert result["exit_price"] == 3960.0

    def test_close_position_loss(self, executor):
        order_id = executor.place_bracket_order("RELIANCE", "BUY", 10, 2850.0, 2815.0, 2920.0)
        result = executor.close_position(order_id, 2820.0)
        assert result["pnl"] == pytest.approx(-300.0, abs=1)

    def test_close_position_sell_side(self, executor):
        order_id = executor.place_bracket_order("ICICIBANK", "SELL", 10, 1240.0, 1255.0, 1215.0)
        result = executor.close_position(order_id, 1220.0)
        assert result["pnl"] == pytest.approx(200.0, abs=1)

    def test_close_removes_from_open_positions(self, executor):
        order_id = executor.place_bracket_order("HDFCBANK", "BUY", 3, 1680.0, 1660.0, 1720.0)
        executor.close_position(order_id, 1710.0)
        assert order_id not in executor.get_open_positions()

    def test_close_nonexistent_position(self, executor):
        result = executor.close_position("FAKE_ORDER_ID", 1000.0)
        assert result == {}

    def test_trade_history_records(self, executor):
        executor.place_order("RELIANCE", "BUY", 5)
        history = executor.get_trade_history()
        assert len(history) >= 1

    def test_squareoff_all(self, executor, market_data):
        executor.place_bracket_order("RELIANCE", "BUY", 5, 2850.0, 2815.0, 2920.0)
        executor.place_bracket_order("INFY", "BUY", 10, 1520.0, 1500.0, 1560.0)
        closed = executor.squareoff_all(market_data)
        assert len(closed) == 2
        assert len(executor.get_open_positions()) == 0

    def test_squareoff_empty_positions(self, executor):
        closed = executor.squareoff_all()
        assert closed == []

    def test_unique_order_ids(self, executor):
        ids = set()
        for _ in range(10):
            oid = executor.place_order("RELIANCE", "BUY", 1)
            ids.add(oid)
        assert len(ids) == 10


class TestTradeExecutorAPI:
    def test_execute_trade_endpoint(self, client):
        response = client.post("/trade/execute/RELIANCE")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_execute_trade_returns_signal(self, client):
        response = client.post("/trade/execute/INFY")
        data = response.json()
        if data["success"]:
            assert "order_id" in data
            assert "signal" in data
            assert data["paper_trade"] is True

    def test_manual_trade_endpoint(self, client):
        response = client.post("/trade/manual", json={
            "symbol": "TCS",
            "action": "BUY",
            "qty": 5,
            "price": 3900.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "order_id" in data

    def test_trade_history_endpoint(self, client):
        client.post("/trade/manual", json={"symbol": "HDFCBANK", "action": "BUY", "qty": 3})
        response = client.get("/trade/history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["trades"], list)

    def test_open_positions_endpoint(self, client):
        response = client.get("/trade/positions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_squareoff_all_endpoint(self, client):
        response = client.post("/trade/squareoff-all")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "closed_positions" in data
