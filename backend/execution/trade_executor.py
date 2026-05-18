import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, kite=None, paper_trade: bool = True):
        self.kite = kite
        self.paper_trade = paper_trade
        self.paper_trades: list = []
        self.open_positions: dict = {}

    def place_order(self, symbol: str, action: str, qty: int,
                    order_type: str = "MARKET", price: Optional[float] = None) -> str:
        if self.paper_trade:
            return self._paper_order(symbol, action, qty, order_type, price)

        try:
            transaction = (
                self.kite.TRANSACTION_TYPE_BUY if action == "BUY"
                else self.kite.TRANSACTION_TYPE_SELL
            )
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=transaction,
                quantity=qty,
                product=self.kite.PRODUCT_MIS,
                order_type=self.kite.ORDER_TYPE_MARKET if order_type == "MARKET"
                           else self.kite.ORDER_TYPE_LIMIT,
                price=price,
            )
            logger.info(f"✅ Live order: {action} {qty} {symbol} | ID: {order_id}")
            return str(order_id)
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            raise

    def place_bracket_order(self, symbol: str, action: str, qty: int,
                             entry: float, stop_loss: float, target: float) -> str:
        if self.paper_trade:
            order_id = self._paper_order(symbol, action, qty, "LIMIT", entry)
            self.open_positions[order_id] = {
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "entry_price": entry,
                "stop_loss": stop_loss,
                "target": target,
                "status": "OPEN",
                "timestamp": datetime.now().isoformat(),
                "paper_trade": True,
            }
            return order_id

        try:
            transaction = (
                self.kite.TRANSACTION_TYPE_BUY if action == "BUY"
                else self.kite.TRANSACTION_TYPE_SELL
            )
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_BO,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=transaction,
                quantity=qty,
                product=self.kite.PRODUCT_MIS,
                order_type=self.kite.ORDER_TYPE_LIMIT,
                price=entry,
                squareoff=abs(target - entry),
                stoploss=abs(entry - stop_loss),
            )
            logger.info(f"✅ Bracket order: {action} {qty} {symbol} @ {entry} | SL:{stop_loss} T:{target} | ID:{order_id}")
            return str(order_id)
        except Exception as e:
            logger.error(f"❌ Bracket order failed: {e}")
            raise

    def close_position(self, order_id: str, current_price: float) -> dict:
        if order_id in self.open_positions:
            pos = self.open_positions[order_id]
            entry = pos["entry_price"]
            qty = pos["qty"]
            action = pos["action"]
            pnl = (current_price - entry) * qty if action == "BUY" else (entry - current_price) * qty
            pos["status"] = "CLOSED"
            pos["exit_price"] = current_price
            pos["pnl"] = round(pnl, 2)
            pos["closed_at"] = datetime.now().isoformat()
            self.paper_trades.append(pos)
            del self.open_positions[order_id]
            logger.info(f"Position closed: {order_id} | PnL: ₹{pnl:.2f}")
            return pos
        return {}

    def squareoff_all(self, market_data=None) -> list:
        closed = []
        for order_id in list(self.open_positions.keys()):
            pos = self.open_positions[order_id]
            price = pos["entry_price"] * 1.005
            if market_data:
                quotes = market_data.get_live_quote([pos["symbol"]])
                price = quotes.get(pos["symbol"], {}).get("last_price", price)
            closed.append(self.close_position(order_id, price))
        logger.info(f"Squared off {len(closed)} positions.")
        return closed

    def _paper_order(self, symbol: str, action: str, qty: int,
                     order_type: str, price: Optional[float]) -> str:
        order_id = f"PAPER_{uuid.uuid4().hex[:8].upper()}"
        trade = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "order_type": order_type,
            "price": price,
            "status": "COMPLETE",
            "timestamp": datetime.now().isoformat(),
            "paper_trade": True,
        }
        self.paper_trades.append(trade)
        logger.info(f"📄 Paper order: {action} {qty} {symbol} @ {price} | ID: {order_id}")
        return order_id

    def get_trade_history(self) -> list:
        return self.paper_trades

    def get_open_positions(self) -> dict:
        return self.open_positions
