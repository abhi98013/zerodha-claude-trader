import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ClaudeAnalyzer:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade
        self.client = None
        self._setup_client()

    def _setup_client(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key and not self.paper_trade:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude AI client initialized")
            except ImportError:
                logger.warning("anthropic package not installed, using mock responses")
        else:
            logger.info("Running with mock Claude responses (paper trade mode)")

    def analyze_trade_signal(self, market_context: dict) -> dict:
        if self.client is None:
            return self._mock_trade_signal(market_context)

        prompt = f"""
You are an expert quantitative trader with 20 years of experience in Indian markets (NSE/BSE).
Analyze the following market data and provide a precise trading decision.

MARKET CONTEXT:
{json.dumps(market_context, indent=2)}

Your task:
1. Analyze price action, volume, RSI, SMA, Bollinger Bands provided
2. Consider momentum and trend direction
3. Apply strict risk management principles (minimum 1:2 risk-reward)
4. Make a final trading decision based on confluence of signals

Respond ONLY in this exact JSON format with no extra text:
{{
    "action": "BUY" or "SELL" or "HOLD",
    "confidence": <integer 0-100>,
    "entry_price": <float or null>,
    "stop_loss": <float>,
    "target": <float>,
    "reasoning": "<brief explanation under 100 words>",
    "risk_reward_ratio": <float>,
    "position_size_multiplier": <one of: 0.25, 0.5, 0.75, 1.0>
}}

Rules:
- Only BUY/SELL if confidence >= 70
- stop_loss must be realistic (within 1-2% of entry)
- risk_reward_ratio must be >= 1.5
- If signals are mixed or unclear, action must be HOLD
"""
        try:
            from config.settings import settings
            response = self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            result = json.loads(raw[start:end])
            logger.info(f"Claude signal for {market_context.get('symbol')}: {result['action']} ({result['confidence']}%)")
            return result
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._mock_trade_signal(market_context)

    def analyze_exit_signal(self, position: dict, current_data: dict) -> dict:
        if self.client is None:
            return self._mock_exit_signal(position, current_data)

        prompt = f"""
You are managing an active trade. Determine if we should EXIT now.

ACTIVE POSITION:
{json.dumps(position, indent=2)}

CURRENT MARKET:
{json.dumps(current_data, indent=2)}

Respond ONLY in JSON:
{{
    "exit_now": true or false,
    "reason": "<string>",
    "urgency": "immediate" or "next_candle" or "wait"
}}
"""
        try:
            from config.settings import settings
            response = self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except Exception as e:
            logger.error(f"Claude exit API error: {e}")
            return self._mock_exit_signal(position, current_data)

    def _mock_trade_signal(self, context: dict) -> dict:
        import random
        rsi = context.get("rsi_14", 50)
        price = context.get("current_price", 1000)
        sma20 = context.get("sma_20", price)

        if rsi < 35 and price > sma20 * 0.98:
            action, confidence = "BUY", random.randint(72, 88)
        elif rsi > 65 and price < sma20 * 1.02:
            action, confidence = "SELL", random.randint(70, 85)
        else:
            action, confidence = "HOLD", random.randint(40, 65)

        sl = round(price * 0.988, 2) if action == "BUY" else round(price * 1.012, 2)
        target = round(price * 1.025, 2) if action == "BUY" else round(price * 0.975, 2)
        rr = round(abs(target - price) / abs(price - sl), 2) if action != "HOLD" else 0

        return {
            "action": action,
            "confidence": confidence,
            "entry_price": price if action != "HOLD" else None,
            "stop_loss": sl,
            "target": target,
            "reasoning": f"Mock: RSI={rsi:.1f}, Price vs SMA20 = {((price/sma20)-1)*100:.2f}%",
            "risk_reward_ratio": rr,
            "position_size_multiplier": 0.5 if confidence < 80 else 1.0,
        }

    def _mock_exit_signal(self, position: dict, current_data: dict) -> dict:
        current_price = current_data.get("current_price", 0)
        entry = position.get("entry_price", current_price)
        action = position.get("action", "BUY")
        pnl_pct = ((current_price - entry) / entry * 100) if action == "BUY" else ((entry - current_price) / entry * 100)

        exit_now = pnl_pct >= 2.0 or pnl_pct <= -1.2
        return {
            "exit_now": exit_now,
            "reason": f"Mock exit: PnL={pnl_pct:.2f}%",
            "urgency": "immediate" if pnl_pct <= -1.2 else "next_candle",
        }
