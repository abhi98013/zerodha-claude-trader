"""
Strategy Engine — Orchestrator
Combines: SectorScanner → StockFilter → OptionsSelector → Claude AI Validation
Strictly follows the video strategy rules:
1. Scan sectors 9:15-10:00 AM
2. Filter stocks: high turnover + 5-min candle low hold + institutional buying
3. Avoid MF-heavy stocks
4. Select CE/PE options on filtered stocks
5. Claude AI validates and improves signal quality
6. Risk: small consistent profits, controlled losses
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from strategy.sector_scanner import SectorScanner
from strategy.stock_filter import StockFilter
from strategy.options_selector import OptionsSelector

logger = logging.getLogger(__name__)

CLAUDE_OPTION_PROMPT = """You are an expert NSE options trader with 20 years of experience.

Analyze the following option trade opportunity and validate/improve it:

SECTOR CONTEXT:
- Sector: {sector}
- Sector Trend: {sector_trend}
- Sector Momentum Score: {sector_momentum}/100

STOCK FUNDAMENTALS:
- Symbol: {symbol}
- Change %: {change_pct}%
- Intraday Turnover: ₹{turnover}Cr
- Delivery %: {delivery_pct}% (institutional buying signal)
- 5-min Candle Low Holding: {low_hold}
- Filter Score: {filter_score}/100
- Reasons: {reasons}

OPTION DETAILS:
- Type: {option_type} ({"BULLISH" if option_type == "CE" else "BEARISH"} bet)
- Strike: {strike}
- Premium: ₹{premium}
- Target Premium: ₹{target_premium} (+{target_pct}%)
- Stop Loss Premium: ₹{sl_premium} (-{sl_pct}%)
- Risk:Reward = {risk_reward}
- Lot Size: {lot_size}
- Cost/Lot: ₹{cost_per_lot}

STRATEGY RULES TO VALIDATE:
1. Sector must be strongly trending (UP/STRONG_UP for CE, DOWN/STRONG_DOWN for PE)
2. Stock must have high intraday turnover (fresh activity, not just large-cap sluggishness)
3. First 5-min candle low MUST hold — if broken, DO NOT trade
4. Delivery % >= 40% indicates institutional accumulation (preferred)
5. Avoid MF-heavy large-cap stocks (they lag)
6. R:R must be at least 1.5:1
7. Trade small capital, accept small consistent profits

Respond in this EXACT JSON format:
{{
  "approved": true/false,
  "confidence": 0-100,
  "action": "BUY_CE" or "BUY_PE" or "SKIP",
  "adjusted_target_premium": <float>,
  "adjusted_sl_premium": <float>,
  "adjusted_risk_reward": <float>,
  "max_lots": 1-3,
  "key_risk": "<main risk factor>",
  "reasoning": "<2-3 sentence analysis>",
  "improvement": "<what Claude suggests to improve entry/exit>"
}}"""


class StrategyEngine:
    def __init__(self, paper_trade: bool = True, anthropic_client=None):
        self.paper_trade = paper_trade
        self.anthropic = anthropic_client
        self.sector_scanner = SectorScanner(paper_trade=paper_trade)
        self.stock_filter = StockFilter(paper_trade=paper_trade)
        self.options_selector = OptionsSelector(paper_trade=paper_trade)

    def is_valid_trading_window(self) -> bool:
        now = datetime.now().time()
        from datetime import time
        return time(9, 15) <= now <= time(15, 10)

    def is_early_session(self) -> bool:
        now = datetime.now().time()
        from datetime import time
        return time(9, 15) <= now <= time(10, 0)

    def run(self, kite=None, force: bool = False) -> Dict:
        if not force and not self.is_valid_trading_window():
            return {"status": "market_closed", "message": "Market is closed. Strategy runs 9:15 AM – 3:10 PM.", "picks": []}

        logger.info("=== Strategy Engine: Starting scan ===")

        top_sectors    = self.sector_scanner.get_top_sectors(n=3, direction="UP")
        bottom_sectors = self.sector_scanner.get_top_sectors(n=2, direction="DOWN")
        all_sectors    = self.sector_scanner.get_sector_momentum()

        logger.info(f"Top UP sectors: {[s['sector'] for s in top_sectors]}")
        logger.info(f"Top DOWN sectors: {[s['sector'] for s in bottom_sectors]}")

        filtered_stocks = self.stock_filter.filter_stocks(top_sectors + bottom_sectors, kite)
        logger.info(f"Filtered stocks ({len(filtered_stocks)}): {[s['symbol'] for s in filtered_stocks]}")

        raw_options = self.options_selector.select_best_options(filtered_stocks, kite, max_picks=6)
        logger.info(f"Raw option picks: {[o['option_symbol'] for o in raw_options]}")

        validated_picks = []
        for opt in raw_options:
            validated = self._validate_with_claude(opt)
            if validated.get("approved"):
                opt.update(validated)
                validated_picks.append(opt)

        validated_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        final_picks = validated_picks[:3]

        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "early_session": self.is_early_session(),
            "sector_scan": all_sectors[:7],
            "top_sectors": top_sectors,
            "filtered_stocks": filtered_stocks,
            "raw_options": len(raw_options),
            "picks": final_picks,
            "total_picks": len(final_picks),
            "message": f"Found {len(final_picks)} validated option trade(s)",
        }

    def _validate_with_claude(self, opt: Dict) -> Dict:
        if self.paper_trade or self.anthropic is None:
            return self._mock_claude_validation(opt)

        try:
            prompt = CLAUDE_OPTION_PROMPT.format(
                sector=opt.get("sector", ""),
                sector_trend=opt.get("sector_trend", "UP"),
                sector_momentum=opt.get("filter_score", 70),
                symbol=opt.get("symbol", ""),
                change_pct=opt.get("change_pct", 0),
                turnover=opt.get("turnover", 0),
                delivery_pct=opt.get("delivery_pct", 50),
                low_hold=opt.get("5min_low_hold", True),
                filter_score=opt.get("filter_score", 70),
                reasons=", ".join(opt.get("filter_reasons", [])),
                option_type=opt.get("option_type", "CE"),
                strike=opt.get("strike", 0),
                premium=opt.get("premium", 0),
                target_premium=opt.get("target_premium", 0),
                target_pct=50,
                sl_premium=opt.get("sl_premium", 0),
                sl_pct=30,
                risk_reward=opt.get("risk_reward", 0),
                lot_size=opt.get("lot_size", 500),
                cost_per_lot=opt.get("cost_per_lot", 0),
            )

            msg = self.anthropic.messages.create(
                model="claude-opus-4-5",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            import json, re
            text = msg.content[0].text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Claude validation failed: {e}")

        return self._mock_claude_validation(opt)

    def _mock_claude_validation(self, opt: Dict) -> Dict:
        score = opt.get("filter_score", 0)
        rr = opt.get("risk_reward", 0)
        approved = score >= 55 and rr >= 1.5

        if approved:
            adj_target = round(opt.get("target_premium", opt.get("premium", 40) * 1.5) * 1.05, 2)
            adj_sl = round(opt.get("sl_premium", opt.get("premium", 40) * 0.7) * 0.98, 2)
            adj_rr = round((adj_target - opt.get("premium", 40)) / max(opt.get("premium", 40) - adj_sl, 1), 2)
            confidence = min(95, int(score * 0.7 + rr * 10))
            action = f"BUY_{opt.get('option_type', 'CE')}"
            reasoning = (
                f"{opt.get('symbol')} shows strong {opt.get('sector_trend')} trend in {opt.get('sector')}. "
                f"Delivery {opt.get('delivery_pct', 50):.1f}% signals institutional accumulation. "
                f"5-min candle low holding confirms bullish structure — proceed with small capital."
            )
            improvement = "Consider entering on a minor pullback to reduce premium cost. Trail SL to cost once 20% profit achieved."
        else:
            adj_target = opt.get("target_premium", 0)
            adj_sl = opt.get("sl_premium", 0)
            adj_rr = rr
            confidence = 30
            action = "SKIP"
            reasoning = f"Signal weak — score {score}/100, R:R {rr}. Not meeting strategy criteria."
            improvement = "Wait for better sector alignment or higher delivery %."

        return {
            "approved": approved,
            "confidence": confidence,
            "action": action,
            "adjusted_target_premium": adj_target,
            "adjusted_sl_premium": adj_sl,
            "adjusted_risk_reward": adj_rr,
            "max_lots": 1 if confidence < 70 else 2,
            "key_risk": f"Sector reversal or 5-min low breach on {opt.get('symbol')}",
            "reasoning": reasoning,
            "improvement": improvement,
        }
