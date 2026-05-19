import logging
import asyncio
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from config.settings import settings
from auth.zerodha_auth import ZerodhaAuth
from data.market_data import MarketData
from ai.claude_analyzer import ClaudeAnalyzer
from risk.risk_manager import RiskManager
from execution.trade_executor import TradeExecutor
from strategy.strategy_engine import StrategyEngine
from strategy.backtester import Backtester
from strategy.recommender import build_recommendations

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/trader.log", mode="a"),
    ]
)
logger = logging.getLogger(__name__)

auth = ZerodhaAuth(paper_trade=settings.PAPER_TRADE)
market_data = MarketData(paper_trade=settings.PAPER_TRADE)
analyzer = ClaudeAnalyzer(paper_trade=settings.PAPER_TRADE)
risk_mgr = RiskManager(market_data=market_data)
executor = TradeExecutor(paper_trade=settings.PAPER_TRADE)
strategy_engine = StrategyEngine(paper_trade=settings.PAPER_TRADE)
bot_running = False
_ohlcv_cache: dict = {}
_CACHE_TTL = 30

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("logs", exist_ok=True)
    auth.load_existing_session()
    logger.info("Zerodha Claude Trader API started")
    logger.info(f"Mode: {'PAPER TRADE' if settings.PAPER_TRADE else 'LIVE TRADE'}")
    yield
    logger.info("Shutting down trader API")

app = FastAPI(
    title="Zerodha Claude AI Trader",
    description="Automated trading system powered by Claude AI and Zerodha Kite",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenRequest(BaseModel):
    request_token: str

class ManualTradeRequest(BaseModel):
    symbol: str
    action: str
    qty: int = 1
    quantity: Optional[int] = None
    price: Optional[float] = None
    order_type: Optional[str] = None

class WatchlistUpdate(BaseModel):
    symbols: List[str]

def build_market_context(symbol: str) -> dict:
    df = market_data.get_ohlcv(symbol, interval="5minute", days=2)
    df = market_data.compute_indicators(df)
    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "current_price": round(float(latest["close"]), 2),
        "open": round(float(latest["open"]), 2),
        "high": round(float(latest["high"]), 2),
        "low": round(float(latest["low"]), 2),
        "volume": int(latest["volume"]),
        "volume_avg_20": round(float(latest["volume_avg_20"]), 0) if not str(latest["volume_avg_20"]) == "nan" else 0,
        "sma_20": round(float(latest["sma_20"]), 2) if not str(latest["sma_20"]) == "nan" else float(latest["close"]),
        "sma_50": round(float(latest["sma_50"]), 2) if not str(latest["sma_50"]) == "nan" else float(latest["close"]),
        "ema_9": round(float(latest["ema_9"]), 2),
        "rsi_14": round(float(latest["rsi_14"]), 2) if not str(latest["rsi_14"]) == "nan" else 50.0,
        "bb_upper": round(float(latest["bb_upper"]), 2) if not str(latest["bb_upper"]) == "nan" else float(latest["close"]) * 1.02,
        "bb_lower": round(float(latest["bb_lower"]), 2) if not str(latest["bb_lower"]) == "nan" else float(latest["close"]) * 0.98,
        "last_5_candles": df.tail(5)[["open", "high", "low", "close", "volume"]].round(2).to_dict("records"),
    }

async def run_trading_cycle():
    global bot_running
    while bot_running:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        if settings.MARKET_OPEN <= current_time <= settings.MARKET_CLOSE:
            if current_time >= settings.SQUAREOFF_TIME:
                logger.info("⏰ Auto square-off time reached")
                executor.squareoff_all(market_data)
                await asyncio.sleep(300)
                continue

            allowed, reason = risk_mgr.is_trade_allowed()
            if not allowed:
                logger.info(f"Trade not allowed: {reason}")
                await asyncio.sleep(60)
                continue

            capital = risk_mgr.get_capital()
            for symbol in settings.WATCHLIST:
                try:
                    context = build_market_context(symbol)
                    signal = analyzer.analyze_trade_signal(context)
                    logger.info(f"{symbol}: {signal['action']} | Confidence: {signal['confidence']}% | R:R {signal.get('risk_reward_ratio', 0)}")

                    valid, validation_msg = risk_mgr.validate_signal(signal)
                    if valid:
                        qty = risk_mgr.calculate_position_size(
                            capital,
                            context["current_price"],
                            signal["stop_loss"],
                            signal["position_size_multiplier"],
                        )
                        if qty > 0:
                            order_id = executor.place_bracket_order(
                                symbol, signal["action"], qty,
                                context["current_price"],
                                signal["stop_loss"],
                                signal["target"],
                            )
                            logger.info(f"Order placed: {order_id}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")

        await asyncio.sleep(300)

@app.get("/")
def root():
    return {
        "name": "Zerodha Claude AI Trader",
        "version": "1.0.0",
        "mode": "PAPER_TRADE" if settings.PAPER_TRADE else "LIVE_TRADE",
        "status": "running",
        "bot_active": bot_running,
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ok": True,
        "mode": "PAPER_TRADE" if settings.PAPER_TRADE else "LIVE_TRADE",
        "authenticated": auth.is_authenticated(),
        "paper_trade": settings.PAPER_TRADE,
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/auth/login-url")
def get_login_url():
    return {"login_url": auth.get_login_url()}

@app.get("/auth/callback")
def auth_callback(request: Request):
    request_token = request.query_params.get("request_token")
    status = request.query_params.get("status", "")
    if status == "cancelled" or not request_token:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
            "<h2 style='color:red'>Login Cancelled or Failed</h2>"
            "<p>Close this window and try again.</p></body></html>",
            status_code=400
        )
    try:
        result = auth.generate_session(request_token)
        market_data.kite = auth.kite
        executor.kite = auth.kite
        logger.info(f"Zerodha session created via callback for user: {result.get('user_id', 'unknown')}")
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}?auth=success", status_code=302)
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
            f"<h2 style='color:red'>Authentication Failed</h2>"
            f"<p>{str(e)}</p>"
            f"<p>Close this window and try again.</p></body></html>",
            status_code=400
        )

@app.post("/auth/session")
def create_session(req: TokenRequest):
    try:
        result = auth.generate_session(req.request_token)
        market_data.kite = auth.kite
        executor.kite = auth.kite
        return {"success": True, "message": "Session created", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/status")
def auth_status():
    return {
        "authenticated": auth.is_authenticated(),
        "paper_trade": settings.PAPER_TRADE,
        "access_token_preview": (auth.get_access_token() or "")[:12] + "..." if auth.get_access_token() else None,
    }

@app.get("/market/quote")
def get_quotes():
    try:
        quotes = market_data.get_live_quote(settings.WATCHLIST)
        return {"success": True, "data": quotes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market/ohlcv/{symbol}")
def get_ohlcv(symbol: str, interval: str = "5minute", days: int = 2):
    import time as _time
    cache_key = f"{symbol.upper()}_{interval}_{days}"
    cached = _ohlcv_cache.get(cache_key)
    if cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]
    try:
        df = market_data.get_ohlcv(symbol.upper(), interval, days)
        df = market_data.compute_indicators(df)
        records = df.tail(50).fillna(0).reset_index()
        if "index" in records.columns:
            records = records.rename(columns={"index": "timestamp"})
        elif "date" in records.columns:
            records = records.rename(columns={"date": "timestamp"})
        else:
            records["timestamp"] = list(range(len(records)))
        candles = records.to_dict("records")
        for c in candles:
            if "timestamp" not in c:
                c["timestamp"] = str(c.get("Unnamed: 0", ""))
        result = {"success": True, "symbol": symbol.upper(), "candles": candles, "data": candles}
        _ohlcv_cache[cache_key] = {"ts": _time.time(), "data": result}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market/context/{symbol}")
def get_market_context(symbol: str):
    try:
        context = build_market_context(symbol.upper())
        return {"success": True, "symbol": symbol.upper(), "indicators": context, "data": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/analyze/{symbol}")
def analyze_symbol(symbol: str):
    try:
        context = build_market_context(symbol.upper())
        signal = analyzer.analyze_trade_signal(context)
        valid, msg = risk_mgr.validate_signal(signal)
        return {
            "success": True,
            "symbol": symbol.upper(),
            "context": context,
            "signal": signal,
            "trade_valid": valid,
            "validation_message": msg,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/analyze-all")
def analyze_all():
    results = []
    for symbol in settings.WATCHLIST:
        try:
            context = build_market_context(symbol)
            signal = analyzer.analyze_trade_signal(context)
            valid, msg = risk_mgr.validate_signal(signal)
            results.append({
                "symbol": symbol,
                "signal": signal,
                "trade_valid": valid,
                "validation_message": msg,
                "current_price": context["current_price"],
            })
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
    return {"success": True, "data": results}

@app.post("/trade/execute/{symbol}")
def execute_trade(symbol: str):
    try:
        allowed, reason = risk_mgr.is_trade_allowed()
        if not allowed:
            raise HTTPException(status_code=400, detail=reason)

        context = build_market_context(symbol.upper())
        signal = analyzer.analyze_trade_signal(context)
        valid, msg = risk_mgr.validate_signal(signal)

        if not valid:
            return {"success": False, "message": msg, "signal": signal}

        capital = risk_mgr.get_capital()
        qty = risk_mgr.calculate_position_size(
            capital, context["current_price"],
            signal["stop_loss"], signal["position_size_multiplier"]
        )

        order_id = executor.place_bracket_order(
            symbol.upper(), signal["action"], qty,
            context["current_price"], signal["stop_loss"], signal["target"]
        )

        return {
            "success": True,
            "order_id": order_id,
            "symbol": symbol.upper(),
            "signal": signal,
            "qty": qty,
            "paper_trade": settings.PAPER_TRADE,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trade/manual")
def manual_trade(req: ManualTradeRequest):
    try:
        qty = req.quantity or req.qty or 1
        order_id = executor.place_order(
            req.symbol.upper(), req.action.upper(),
            qty, price=req.price
        )
        return {"success": True, "order_id": order_id, "paper_trade": settings.PAPER_TRADE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trade/squareoff-all")
def squareoff_all():
    closed = executor.squareoff_all(market_data)
    for pos in closed:
        if "pnl" in pos:
            risk_mgr.update_pnl(pos["pnl"])
    return {"success": True, "closed_positions": len(closed), "positions": closed}

@app.get("/trade/history")
def trade_history():
    return {"success": True, "trades": executor.get_trade_history()}

@app.get("/trade/positions")
def open_positions():
    return {"success": True, "positions": executor.get_open_positions()}

@app.get("/risk/stats")
def risk_stats():
    return {"success": True, "stats": risk_mgr.get_stats()}

@app.post("/risk/reset-daily")
def reset_daily():
    risk_mgr.reset_daily()
    return {"success": True, "message": "Daily stats reset"}

@app.get("/bot/status")
def bot_status():
    return {
        "running": bot_running,
        "paper_trade": settings.PAPER_TRADE,
        "watchlist": settings.WATCHLIST,
        "market_open": settings.MARKET_OPEN,
        "market_close": settings.MARKET_CLOSE,
        "squareoff_time": settings.SQUAREOFF_TIME,
    }

@app.post("/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    global bot_running
    if bot_running:
        return {"success": True, "message": "Bot is already running"}
    bot_running = True
    background_tasks.add_task(run_trading_cycle)
    logger.info("🤖 Trading bot started")
    return {"success": True, "message": "Trading bot started"}

@app.post("/bot/stop")
def stop_bot():
    global bot_running
    bot_running = False
    logger.info("🛑 Trading bot stopped")
    return {"success": True, "message": "Trading bot stopped"}

@app.put("/bot/watchlist")
def update_watchlist(req: WatchlistUpdate):
    settings.WATCHLIST = [s.upper() for s in req.symbols]
    return {"success": True, "watchlist": settings.WATCHLIST}

# ── Strategy Endpoints (NSE Sector Scope Strategy) ──────────────────────────

@app.get("/strategy/scan")
def strategy_scan(force: bool = False):
    """Full strategy run: sector scan → stock filter → options pick → Claude AI validation"""
    kite = auth.kite if auth.is_authenticated() else None
    result = strategy_engine.run(kite=kite, force=force)
    return result

@app.get("/strategy/sectors")
def get_sectors():
    """Get live NSE sectoral index momentum rankings"""
    sectors = strategy_engine.sector_scanner.get_sector_momentum()
    return {"sectors": sectors, "timestamp": datetime.now().isoformat()}

@app.get("/strategy/top-sectors")
def get_top_sectors(n: int = 3, direction: str = "UP"):
    """Get top N trending sectors in given direction"""
    sectors = strategy_engine.sector_scanner.get_top_sectors(n=n, direction=direction)
    return {"sectors": sectors, "direction": direction}

@app.get("/strategy/stocks")
def get_filtered_stocks():
    """Get stocks filtered by turnover, 5-min low hold, and institutional buying"""
    top_sectors = strategy_engine.sector_scanner.get_top_sectors(n=3)
    kite = auth.kite if auth.is_authenticated() else None
    stocks = strategy_engine.stock_filter.filter_stocks(top_sectors, kite)
    return {"stocks": stocks, "count": len(stocks), "timestamp": datetime.now().isoformat()}

@app.get("/strategy/options")
def get_option_picks():
    """Get validated CE/PE option picks with Claude AI analysis"""
    kite = auth.kite if auth.is_authenticated() else None
    result = strategy_engine.run(kite=kite, force=True)
    return {
        "picks": result.get("picks", []),
        "total": result.get("total_picks", 0),
        "timestamp": datetime.now().isoformat(),
    }

# ── Recommendations Endpoint ────────────────────────────────────────────────

@app.get("/strategy/recommendations")
def get_recommendations():
    """Backtest-scored live trade recommendations with strike, SL, target, win probability"""
    try:
        sectors = strategy_engine.sector_scanner.get_sector_momentum()
        top_sectors = strategy_engine.sector_scanner.get_top_sectors(n=5)
        kite = auth.kite if auth.is_authenticated() else None
        stocks = strategy_engine.stock_filter.filter_stocks(top_sectors, kite)
        recs = build_recommendations(stocks, sectors)
        high_prob = [r for r in recs if r["win_probability"] >= 80]
        return {
            "recommendations": recs,
            "high_probability": high_prob,
            "total": len(recs),
            "high_prob_count": len(high_prob),
            "timestamp": datetime.now().isoformat(),
            "generated_at": datetime.now().strftime("%d %b %Y %I:%M %p"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Backtest Endpoints ───────────────────────────────────────────────────────

@app.get("/strategy/backtest")
def run_backtest(start_year: int = 2015, end_year: int = 2026, min_score: int = 55):
    """Run 10-year strategy backtest and return results with top 5 winners"""
    logger.info(f"Backtest requested: {start_year}–{end_year}")
    bt = Backtester()
    result = bt.run(start_year=start_year, end_year=end_year, min_score=min_score)
    return result

if __name__ == "__main__":
    import uvicorn
    import os
    os.makedirs("logs", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
