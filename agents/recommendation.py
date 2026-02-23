"""
Jhaveri FIE — Agent 4: Recommendation Synthesizer
Combines FM directives + Technical signals + Client portfolio → Specific recommendations.
Uses Claude for reasoning about conflicting signals and generating client-specific actions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, date
from anthropic import Anthropic
from config.settings import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, 
    RISK_LIMITS, CONFIDENCE_MATRIX
)

SYNTHESIS_SYSTEM_PROMPT = """You are a portfolio recommendation engine for Jhaveri Securities, an Indian wealth management firm. 

You will receive:
1. FUND MANAGER DIRECTIVES — Structured rules from the fund manager (the primary human input)
2. TECHNICAL SIGNALS — Automated analysis (RSI, MACD, moving averages, etc.) for relevant instruments and sectors
3. CLIENT PORTFOLIO — A specific client's current holdings, risk profile, and allocation

Your job is to generate SPECIFIC, ACTIONABLE recommendations for this client.

RULES:
1. Every recommendation must have an EXACT action: "Redeem ₹X from [Fund]", "Invest ₹Y in [Fund]", "Switch from [A] to [B]"
2. Respect risk profile limits:
   - CONSERVATIVE: Max 15% per sector, Min 20% in liquid/debt
   - MODERATE: Max 25% per sector, Min 10% in liquid/debt  
   - AGGRESSIVE: Max 35% per sector, Min 5% in liquid/debt
3. When FM directive and technical signal AGREE → HIGH confidence (80-100)
4. When only one has a signal → MEDIUM confidence (40-70)
5. When FM and technical CONFLICT → Flag for review, LOW confidence (10-30)
6. Never make portfolio excessively concentrated
7. Calculate before/after allocations for each recommendation
8. For momentum/PMS portfolios, recommendations can be at stock/ETF level
9. For MF portfolios, recommendations should be at fund level (switch/redeem/invest)
10. Always provide clear reasoning combining both inputs

OUTPUT FORMAT — Return ONLY valid JSON:
{
  "client_summary": {
    "client_id": "...",
    "name": "...",
    "risk_profile": "...",
    "total_aum": 0,
    "portfolio_health": "GOOD|NEEDS_REBALANCING|AT_RISK"
  },
  "recommendations": [
    {
      "rec_id": "REC-001",
      "priority": "HIGH|MEDIUM|LOW",
      "action": "REDEEM|INVEST|SWITCH|HOLD|BOOK_PROFITS|STOP_SIP",
      "instrument": "Fund/Stock name",
      "instrument_code": "...",
      "sector": "...",
      "amount": 0,
      "target_instrument": "If switching, the destination fund",
      "reasoning": "Combined FM + Technical reasoning",
      "fm_directive_ref": "DIR-xxx or null",
      "technical_score": 0,
      "technical_signal": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
      "confidence": 0,
      "allocation_before_pct": 0,
      "allocation_after_pct": 0,
      "expected_impact": "Brief description of portfolio impact"
    }
  ],
  "portfolio_impact": {
    "sector_allocation_after": {"IT": 10, "BANKING": 15, ...},
    "equity_pct_after": 0,
    "liquid_pct_after": 0,
    "risk_assessment": "Brief assessment"
  },
  "alerts": ["Any important warnings or flags"]
}"""


class RecommendationAgent:
    """Agent 4: Generates client-specific recommendations."""
    
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        if not mock_mode:
            if not ANTHROPIC_API_KEY:
                self.mock_mode = True
            else:
                try:
                    self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
                    self.model = CLAUDE_MODEL
                except Exception:
                    self.mock_mode = True
    
    def generate_recommendations(
        self,
        fm_directives: list,
        technical_signals: dict,
        sector_signals: list,
        client: dict,
        holdings: list
    ) -> dict:
        """
        Generate recommendations for a single client.
        
        Args:
            fm_directives: List of parsed FM directive dicts
            technical_signals: Dict of {symbol: analysis_dict} for relevant instruments
            sector_signals: List of sector strength dicts
            client: Client info dict
            holdings: List of holding dicts for this client
        """
        
        if self.mock_mode:
            from agents.mock_engine import mock_generate_recommendations
            return mock_generate_recommendations(
                fm_directives, technical_signals, sector_signals, client, holdings
            )
        
        # Build the context for Claude
        context = self._build_context(fm_directives, technical_signals, sector_signals, client, holdings)
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user", 
                    "content": context
                }
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean and parse JSON
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "client_summary": {"client_id": client["client_id"], "name": client["name"]},
                    "recommendations": [],
                    "alerts": [f"Failed to parse response: {response_text[:200]}"]
                }
        
        # Add metadata
        result["generated_at"] = datetime.now().isoformat()
        result["generated_date"] = str(date.today())
        
        return result
    
    def _build_context(self, fm_directives, tech_signals, sector_signals, client, holdings):
        """Build the prompt context with all inputs."""
        
        # Format FM directives
        fm_text = "FUND MANAGER DIRECTIVES:\n"
        if fm_directives:
            for d in fm_directives:
                fm_text += f"  - {d.get('id', 'N/A')}: {d.get('action')} {d.get('target_type')} {d.get('target')}"
                fm_text += f" | Magnitude: {d.get('magnitude', 'N/A')} | Conviction: {d.get('conviction', 'N/A')}"
                fm_text += f" | Applies to: {d.get('applies_to', 'ALL')} | Rationale: {d.get('rationale', '')}\n"
        else:
            fm_text += "  No active FM directives today. Generate recommendations based on technical signals only.\n"
        
        # Format sector signals
        sector_text = "\nSECTOR RELATIVE STRENGTH (vs Nifty 50):\n"
        if sector_signals:
            for s in sector_signals:
                sector_text += f"  {s.get('sector', 'N/A'):<15} RS(1m): {s.get('rs_1m', 0):>6.1f}%  "
                sector_text += f"RSI: {s.get('rsi', 'N/A'):>5}  Score: {s.get('composite_score', 0):>6.1f}  "
                sector_text += f"Signal: {s.get('signal', 'N/A')}\n"
        else:
            sector_text += "  No sector data available.\n"
        
        # Format technical signals for holdings
        tech_text = "\nTECHNICAL SIGNALS FOR CLIENT HOLDINGS:\n"
        for h in holdings:
            symbol = h.get("instrument_code", "")
            sig = tech_signals.get(symbol, {})
            if sig and "error" not in sig:
                tech_text += f"  {h.get('instrument_name', symbol):<40} "
                tech_text += f"RSI: {sig.get('rsi_14', 'N/A'):>5}  "
                tech_text += f"MACD: {sig.get('macd_crossover', 'N/A'):<10}  "
                tech_text += f"vs200DMA: {sig.get('price_vs_200dma', 'N/A'):<8}  "
                tech_text += f"Score: {sig.get('composite_score', 0):>6.1f}  "
                tech_text += f"Signal: {sig.get('signal', 'N/A')}\n"
            else:
                tech_text += f"  {h.get('instrument_name', symbol):<40} No technical data (MF - use sector proxy)\n"
        
        # Format client portfolio
        client_text = f"\nCLIENT PORTFOLIO:\n"
        client_text += f"  Name: {client.get('name')} | ID: {client.get('client_id')}\n"
        client_text += f"  Risk Profile: {client.get('risk_profile')} | Strategy: {client.get('strategy_type')}\n"
        client_text += f"  Total AUM: ₹{client.get('total_aum', 0):,.0f}\n\n"
        
        client_text += f"  {'Instrument':<40} {'Type':<6} {'Sector':<12} {'Value':>12} {'Cost':>12} {'P&L%':>8} {'Alloc%':>7} {'SIP':>8}\n"
        client_text += f"  {'-'*105}\n"
        
        for h in holdings:
            value = h.get("current_value", 0)
            cost = h.get("cost_basis", 0)
            pnl_pct = ((value - cost) / cost * 100) if cost > 0 else 0
            sip_info = f"₹{h.get('sip_amount', 0):,.0f}" if h.get("sip_active") == "TRUE" or h.get("sip_active") == True else "No"
            
            client_text += f"  {h.get('instrument_name', '')[:40]:<40} "
            client_text += f"{h.get('instrument_type', ''):<6} "
            client_text += f"{h.get('sector_tag', ''):<12} "
            client_text += f"₹{value:>10,.0f} "
            client_text += f"₹{cost:>10,.0f} "
            client_text += f"{pnl_pct:>7.1f}% "
            client_text += f"{h.get('allocation_pct', 0):>6.1f}% "
            client_text += f"{sip_info:>8}\n"
        
        # Sector concentration
        sector_alloc = {}
        for h in holdings:
            sector = h.get("sector_tag", "OTHER")
            sector_alloc[sector] = sector_alloc.get(sector, 0) + h.get("allocation_pct", 0)
        
        client_text += f"\n  SECTOR CONCENTRATION:\n"
        for sector, pct in sorted(sector_alloc.items(), key=lambda x: -x[1]):
            client_text += f"    {sector:<15} {pct:>6.1f}%\n"
        
        # Risk limits
        risk = client.get("risk_profile", "MODERATE")
        limits = RISK_LIMITS
        client_text += f"\n  RISK LIMITS ({risk}):\n"
        client_text += f"    Max sector concentration: {limits['max_sector_concentration'].get(risk, 0.25)*100:.0f}%\n"
        client_text += f"    Min liquid/debt buffer: {limits['min_liquid_buffer'].get(risk, 0.10)*100:.0f}%\n"
        
        return f"{fm_text}\n{sector_text}\n{tech_text}\n{client_text}"
    
    def generate_recommendations_batch(
        self,
        fm_directives: list,
        technical_signals: dict,
        sector_signals: list,
        clients_with_holdings: list
    ) -> list:
        """Generate recommendations for all clients."""
        
        all_results = []
        
        for client_data in clients_with_holdings:
            client = client_data["client"]
            holdings = client_data["holdings"]
            
            print(f"  ⚗️  Processing {client['name']} ({client['client_id']})...")
            
            try:
                result = self.generate_recommendations(
                    fm_directives, technical_signals, sector_signals,
                    client, holdings
                )
                all_results.append(result)
                
                rec_count = len(result.get("recommendations", []))
                print(f"     ✅ {rec_count} recommendations generated")
                
            except Exception as e:
                print(f"     ❌ Error: {e}")
                all_results.append({
                    "client_summary": {"client_id": client["client_id"], "name": client["name"]},
                    "recommendations": [],
                    "alerts": [f"Error generating recommendations: {str(e)}"]
                })
        
        return all_results


# ══════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════

def test_recommendation_agent():
    """Test with sample data."""
    
    print("═" * 60)
    print("  RECOMMENDATION AGENT — TEST MODE")
    print("═" * 60)
    
    if not ANTHROPIC_API_KEY:
        print("\n⚠️  No ANTHROPIC_API_KEY. Set it in .env to test.")
        return
    
    # Sample FM directives
    sample_directives = [
        {
            "id": "DIR-001",
            "action": "INCREASE_EXPOSURE",
            "target_type": "SECTOR",
            "target": "ENERGY",
            "magnitude": None,
            "conviction": "HIGH",
            "rationale": "Energy sector in structural uptrend, PSU re-rating",
            "applies_to": "ALL_CLIENTS",
        },
        {
            "id": "DIR-002",
            "action": "REDUCE_EXPOSURE",
            "target_type": "SECTOR",
            "target": "IT",
            "magnitude": "50%",
            "conviction": "HIGH",
            "rationale": "IT entering long-term lull, structural challenges",
            "applies_to": "ALL_CLIENTS",
        },
        {
            "id": "DIR-003",
            "action": "INCREASE_ALLOCATION",
            "target_type": "ASSET_CLASS",
            "target": "GOLD",
            "magnitude": "TO_20%",
            "conviction": "HIGH",
            "rationale": "Gold entering upward long-term trend, reallocate 50% portfolio to gold-heavy indices",
            "applies_to": "ALL_CLIENTS",
        }
    ]
    
    # Sample technical signals
    sample_tech = {
        "NSE:NTPC": {"rsi_14": 55, "macd_crossover": "BULLISH", "price_vs_200dma": "ABOVE", "composite_score": 42, "signal": "BUY"},
        "NSE:ONGC": {"rsi_14": 48, "macd_crossover": "NEUTRAL", "price_vs_200dma": "ABOVE", "composite_score": 25, "signal": "BUY"},
    }
    
    sample_sectors = [
        {"sector": "ENERGY", "rs_1m": 3.2, "rsi": 58, "composite_score": 45, "signal": "BUY"},
        {"sector": "BANKING", "rs_1m": 0.8, "rsi": 62, "composite_score": 20, "signal": "HOLD"},
        {"sector": "IT", "rs_1m": -4.5, "rsi": 38, "composite_score": -35, "signal": "SELL"},
        {"sector": "PHARMA", "rs_1m": 1.5, "rsi": 45, "composite_score": 15, "signal": "HOLD"},
    ]
    
    # Sample client
    sample_client = {
        "client_id": "JHV-001",
        "name": "Arjun Kapoor",
        "risk_profile": "MODERATE",
        "strategy_type": "MF_ONLY",
        "total_aum": 5000000,
    }
    
    sample_holdings = [
        {"instrument_code": "120503", "instrument_name": "ICICI Prudential Bluechip Fund", "instrument_type": "MF", "sector_tag": "LARGECAP", "current_value": 1000000, "cost_basis": 880000, "allocation_pct": 20.0, "sip_active": "TRUE", "sip_amount": 15000},
        {"instrument_code": "112227", "instrument_name": "HDFC Flexi Cap Fund", "instrument_type": "MF", "sector_tag": "DIVERSIFIED", "current_value": 1000000, "cost_basis": 850000, "allocation_pct": 20.0, "sip_active": "TRUE", "sip_amount": 20000},
        {"instrument_code": "106098", "instrument_name": "ICICI Pru Technology Fund", "instrument_type": "MF", "sector_tag": "IT", "current_value": 500000, "cost_basis": 550000, "allocation_pct": 10.0, "sip_active": "TRUE", "sip_amount": 10000},
        {"instrument_code": "106100", "instrument_name": "ICICI Pru Banking Fund", "instrument_type": "MF", "sector_tag": "BANKING", "current_value": 750000, "cost_basis": 650000, "allocation_pct": 15.0, "sip_active": "TRUE", "sip_amount": 10000},
        {"instrument_code": "119364", "instrument_name": "SBI Liquid Fund", "instrument_type": "MF", "sector_tag": "LIQUID", "current_value": 750000, "cost_basis": 750000, "allocation_pct": 15.0, "sip_active": "FALSE", "sip_amount": 0},
    ]
    
    agent = RecommendationAgent()
    result = agent.generate_recommendations(
        sample_directives, sample_tech, sample_sectors,
        sample_client, sample_holdings
    )
    
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    test_recommendation_agent()
