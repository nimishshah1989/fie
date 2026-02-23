"""
Jhaveri FIE — Agent 1: NLP Parser Agent
Converts fund manager natural language market views into structured directives.
Uses Claude API for intelligent parsing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from database.models import FMDirective, init_db, get_session

# ══════════════════════════════════════════════
# SYSTEM PROMPT FOR NLP PARSING
# ══════════════════════════════════════════════

NLP_SYSTEM_PROMPT = """You are a financial directive parser for Jhaveri Securities, an Indian wealth management firm managing ₹3,500 crores in AUM. Your job is to convert the fund manager's natural language market views into structured, machine-readable JSON directives.

CONTEXT:
- The firm manages mutual fund portfolios, ETF allocations, and momentum stock strategies for retail and HNI clients
- Clients have different risk profiles: CONSERVATIVE, MODERATE, AGGRESSIVE
- Strategy types include: MF_ONLY (mutual fund investors), MF_STOCKS (mixed), MOMENTUM (active stock strategy), PMS (portfolio management service)
- Indian market context: NSE/BSE listed stocks, SEBI-registered mutual funds, Nifty sectoral indices

PARSING RULES:
1. Every actionable statement becomes a SEPARATE directive
2. Infer conviction level from language intensity:
   - HIGH: "strong buy", "very bullish", "aggressive", "definitely", "structural story", "long-term positive"
   - MEDIUM: "looks good", "reasonable", "could work", "worth considering"
   - LOW: "might be", "uncertain", "speculative", "small bet"
3. Map all mentions to standard sector classifications: IT, BANKING, PHARMA, AUTO, FMCG, METAL, ENERGY, REALTY, INFRA, TELECOM, MEDIA, CHEMICAL
4. Understand Hinglish (Hindi-English mix) naturally
5. Understand informal market jargon: "book profits" = partial sell, "accumulate" = buy gradually, "avoid" = don't buy, "exit" = sell everything
6. If a directive is ambiguous, include an "ambiguity_flag" field with what needs clarification
7. Timeframes: IMMEDIATE (today/this week), SHORT_TERM (1-4 weeks), MEDIUM_TERM (1-3 months), LONG_TERM (3-12 months), STRATEGIC (1+ year)
8. If the FM mentions specific fund names, map them to their AMFI scheme names where possible
9. If the FM mentions stock names, use NSE ticker symbols

SUPPORTED ACTIONS:
- BUY: New purchase or add to existing position
- SELL: Exit position completely
- REDUCE_EXPOSURE: Decrease allocation by percentage
- INCREASE_EXPOSURE: Increase allocation to a sector/asset
- BOOK_PROFITS: Partial sell, usually triggered by gains threshold
- SWITCH: Move from one fund/sector to another
- HOLD: Maintain current position explicitly
- INCREASE_ALLOCATION: Raise allocation to specific percentage level
- BUY_ON_DIP: Conditional buy at lower levels
- SIP_TO_LUMPSUM: Deploy accumulated SIP pool as lumpsum
- AVOID: Do not enter this sector/stock
- STOP_SIP: Pause SIP in specific fund

SUPPORTED TARGET TYPES:
- SECTOR: IT, BANKING, PHARMA, AUTO, FMCG, METAL, ENERGY, REALTY, INFRA
- STOCK: NSE symbol (e.g., HDFCBANK, RELIANCE, TCS)
- MF_SCHEME: Specific mutual fund name
- ETF: Specific ETF name
- ASSET_CLASS: EQUITY, DEBT, LIQUID, GOLD, HYBRID
- INDEX: NIFTY50, BANKNIFTY, NIFTY_MIDCAP

CLIENT APPLICABILITY:
- ALL_CLIENTS: Universal recommendation
- CONSERVATIVE_CLIENTS: Low risk tolerance
- MODERATE_CLIENTS: Balanced approach
- AGGRESSIVE_CLIENTS: High risk tolerance
- MOMENTUM_STRATEGY: Stock momentum strategy clients only
- MF_ONLY: Mutual fund only clients
- HIGH_AUM: Clients above ₹50L AUM
- PMS_CLIENTS: Portfolio management clients

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{
  "directives": [
    {
      "id": "DIR-001",
      "action": "BUY",
      "target_type": "SECTOR",
      "target": "PHARMA",
      "magnitude": null,
      "condition": "IMMEDIATE",
      "timeframe": "MEDIUM_TERM",
      "conviction": "HIGH",
      "rationale": "Rural recovery + patent cliff beneficiaries",
      "applies_to": "ALL_CLIENTS",
      "ambiguity_flag": null
    }
  ],
  "market_context": "Brief summary of overall market view expressed by FM",
  "risk_stance": "DEFENSIVE|NEUTRAL|AGGRESSIVE",
  "unprocessable_statements": ["Any statement that couldn't be parsed into a directive"]
}"""


# ══════════════════════════════════════════════
# NLP PARSER CLASS
# ══════════════════════════════════════════════

class NLPParserAgent:
    """Agent 1: Converts FM natural language to structured directives."""
    
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        if not mock_mode:
            if not ANTHROPIC_API_KEY:
                print("⚠️  No API key — switching to mock mode")
                self.mock_mode = True
            else:
                try:
                    self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
                    self.model = CLAUDE_MODEL
                except Exception:
                    self.mock_mode = True
    
    def parse(self, fm_input: str, fm_name: str = "Fund Manager") -> dict:
        """
        Parse fund manager's natural language input into structured directives.
        """
        if self.mock_mode:
            return self._mock_parse(fm_input, fm_name)
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=NLP_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Parse the following fund manager market views into structured directives:\n\n\"{fm_input}\""
                    }
                ]
            )
        except Exception as api_err:
            # If API call fails, fall back to mock
            print(f"⚠️  API call failed ({api_err}), using mock parser")
            return self._mock_parse(fm_input, fm_name)
        
        # Extract JSON from response
        response_text = message.content[0].text.strip()
        
        # Clean up any markdown formatting
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse Claude's response as JSON: {response_text[:200]}")
        
        # Add metadata
        parsed["fm_name"] = fm_name
        parsed["parsed_at"] = datetime.now().isoformat()
        parsed["raw_input"] = fm_input
        parsed["directive_count"] = len(parsed.get("directives", []))
        
        # Validate and enrich directives
        for i, directive in enumerate(parsed.get("directives", [])):
            if "id" not in directive:
                directive["id"] = f"DIR-{i+1:03d}"
            directive["fm_name"] = fm_name
        
        return parsed
    
    def _mock_parse(self, fm_input: str, fm_name: str) -> dict:
        """Mock parsing using rule-based extraction."""
        from agents.mock_engine import mock_parse_fm_input
        return mock_parse_fm_input(fm_input, fm_name)
    
    def save_directives(self, parsed_output: dict) -> list:
        """Save parsed directives to database."""
        engine = init_db()
        session = get_session(engine)
        
        saved = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for directive in parsed_output.get("directives", []):
            directive_id = f"{timestamp}_{directive['id']}"
            
            fm_dir = FMDirective(
                directive_id=directive_id,
                raw_input=parsed_output.get("raw_input", ""),
                action=directive.get("action", ""),
                target_type=directive.get("target_type", ""),
                target=json.dumps(directive.get("target")) if isinstance(directive.get("target"), list) else directive.get("target", ""),
                magnitude=directive.get("magnitude"),
                condition=directive.get("condition"),
                timeframe=directive.get("timeframe"),
                conviction=directive.get("conviction", "MEDIUM"),
                rationale=directive.get("rationale", ""),
                applies_to=directive.get("applies_to", "ALL_CLIENTS"),
                fm_name=directive.get("fm_name", ""),
                status="ACTIVE",
            )
            
            session.add(fm_dir)
            saved.append(directive_id)
        
        session.commit()
        session.close()
        
        return saved
    
    def get_active_directives(self) -> list:
        """Get all active FM directives from database."""
        engine = init_db()
        session = get_session(engine)
        
        directives = session.query(FMDirective).filter_by(status="ACTIVE").all()
        
        result = []
        for d in directives:
            result.append({
                "directive_id": d.directive_id,
                "action": d.action,
                "target_type": d.target_type,
                "target": d.target,
                "magnitude": d.magnitude,
                "condition": d.condition,
                "timeframe": d.timeframe,
                "conviction": d.conviction,
                "rationale": d.rationale,
                "applies_to": d.applies_to,
                "fm_name": d.fm_name,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })
        
        session.close()
        return result


# ══════════════════════════════════════════════
# INTERACTIVE TEST
# ══════════════════════════════════════════════

def test_parser():
    """Test the NLP parser with sample inputs."""
    
    sample_inputs = [
        """Pharma sector looking strong for next 2 quarters based on rural recovery 
        and patent cliff beneficiaries. Reduce IT exposure by 15% - sector in structural 
        decline for 3-4 quarters. Book partial profits in any banking fund above 8% recent gains. 
        For conservative clients, increase liquid fund allocation to 20%.""",
        
        """Market mein bahut volatility hai. Nifty 22000 ke neeche aaya toh aggressive 
        buying karo large caps mein. Midcap se thoda door raho abhi. HDFC Bank aur ICICI Bank 
        accumulate karo on any 5% correction. IT sector avoid karo completely.""",
        
        """Switch all clients from ICICI Pru Tech Fund to SBI Healthcare Fund. 
        For momentum strategy, add Reliance and L&T on breakout above their 200 DMA. 
        Stop SIPs in all IT sector funds for next 3 months. 
        Deploy accumulated SIP amounts into pharma and banking funds as lumpsum.""",
    ]
    
    print("═" * 60)
    print("  NLP PARSER AGENT — TEST MODE")
    print("═" * 60)
    
    # Check if API key is available
    if not ANTHROPIC_API_KEY:
        print("\n⚠️  No ANTHROPIC_API_KEY found. Showing sample output structure instead.\n")
        print("Sample parsed output:")
        sample_output = {
            "directives": [
                {
                    "id": "DIR-001",
                    "action": "INCREASE_EXPOSURE",
                    "target_type": "SECTOR",
                    "target": "PHARMA",
                    "magnitude": None,
                    "condition": "IMMEDIATE",
                    "timeframe": "MEDIUM_TERM",
                    "conviction": "HIGH",
                    "rationale": "Rural recovery + patent cliff beneficiaries",
                    "applies_to": "ALL_CLIENTS",
                },
                {
                    "id": "DIR-002",
                    "action": "REDUCE_EXPOSURE",
                    "target_type": "SECTOR",
                    "target": "IT",
                    "magnitude": "15%",
                    "condition": "IMMEDIATE",
                    "timeframe": "LONG_TERM",
                    "conviction": "HIGH",
                    "rationale": "Structural decline in IT sector",
                    "applies_to": "ALL_CLIENTS",
                }
            ],
            "market_context": "Selective approach - bullish pharma, bearish IT, tactical in banking",
            "risk_stance": "NEUTRAL",
        }
        print(json.dumps(sample_output, indent=2))
        return
    
    parser = NLPParserAgent()
    
    for i, input_text in enumerate(sample_inputs):
        print(f"\n{'─' * 60}")
        print(f"TEST {i+1}: FM Input")
        print(f"{'─' * 60}")
        print(f'"{input_text[:100]}..."')
        print()
        
        try:
            result = parser.parse(input_text, fm_name="Test FM")
            print(f"✅ Parsed {result['directive_count']} directives:")
            print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_parser()
