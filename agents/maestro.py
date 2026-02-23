"""
Jhaveri FIE — Maestro Orchestrator
Coordinates all agents in the correct sequence.
Can be run manually or scheduled via cron/APScheduler.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import csv
from datetime import datetime, date
from pathlib import Path
from config.settings import DATA_DIR, OUTPUT_DIR

class Maestro:
    """Master orchestrator that runs the full daily pipeline."""
    
    def __init__(self):
        self.results = {}
    
    def load_clients_and_holdings(self):
        """Load client data from CSV files."""
        clients = []
        holdings = []
        
        clients_path = DATA_DIR / "clients.csv"
        holdings_path = DATA_DIR / "holdings.csv"
        
        if not clients_path.exists():
            print("❌ clients.csv not found in data/")
            return [], []
        
        with open(clients_path, 'r') as f:
            reader = csv.DictReader(f)
            clients = list(reader)
        
        with open(holdings_path, 'r') as f:
            reader = csv.DictReader(f)
            holdings = list(reader)
        
        # Convert numeric fields
        for c in clients:
            c["total_aum"] = float(c.get("total_aum", 0))
        
        for h in holdings:
            h["current_value"] = float(h.get("current_value", 0))
            h["cost_basis"] = float(h.get("cost_basis", 0))
            h["allocation_pct"] = float(h.get("allocation_pct", 0))
            h["sip_amount"] = float(h.get("sip_amount", 0))
        
        print(f"✅ Loaded {len(clients)} clients, {len(holdings)} holdings")
        return clients, holdings
    
    def group_holdings_by_client(self, clients, holdings):
        """Group holdings by client for processing."""
        grouped = []
        for client in clients:
            client_holdings = [h for h in holdings if h["client_id"] == client["client_id"]]
            grouped.append({
                "client": client,
                "holdings": client_holdings,
            })
        return grouped
    
    def get_unique_instruments(self, holdings):
        """Extract unique instruments that need technical analysis."""
        instruments = set()
        for h in holdings:
            code = h.get("instrument_code", "")
            if code.startswith("NSE:"):
                # Stock or ETF — can get direct technical data
                symbol = code.replace("NSE:", "") + ".NS"
                instruments.add(symbol)
        return list(instruments)
    
    def run_pipeline(self, fm_input: str = None, fm_name: str = "Fund Manager"):
        """
        Run the complete daily pipeline.
        
        Args:
            fm_input: Optional FM natural language input. If None, runs on technical signals only.
            fm_name: Name of the fund manager.
        
        Returns:
            dict with all results
        """
        from agents.nlp_parser import NLPParserAgent
        from agents.technical_signals import TechnicalSignalsAgent
        from agents.recommendation import RecommendationAgent
        
        # Detect if API is available by testing
        mock_mode = True
        try:
            from anthropic import Anthropic
            test_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", 
                                    open(os.path.join(os.path.dirname(__file__), '..', '.env')).read().split('ANTHROPIC_API_KEY=')[1].split('\n')[0].strip() if os.path.exists(os.path.join(os.path.dirname(__file__), '..', '.env')) else ""))
            # Try a minimal API call
            test_client.messages.create(model="claude-sonnet-4-20250514", max_tokens=5, messages=[{"role": "user", "content": "hi"}])
            mock_mode = False
            print("✅ Claude API connected (live mode)")
        except Exception as e:
            mock_mode = True
            print(f"⚠️  Running in MOCK MODE — {str(e)[:80]}")
            print("   Add API credits at console.anthropic.com for live Claude parsing.")
        
        print("═" * 60)
        print(f"  JHAVERI FIE — DAILY PIPELINE RUN")
        print(f"  {datetime.now().strftime('%d-%b-%Y %H:%M IST')}")
        print("═" * 60)
        
        # Step 1: Load client data
        print("\n📋 STEP 1: Loading client portfolios...")
        clients, holdings = self.load_clients_and_holdings()
        if not clients:
            return {"error": "No client data found"}
        
        grouped = self.group_holdings_by_client(clients, holdings)
        
        # Step 2: Parse FM input (if provided)
        print("\n💬 STEP 2: Processing FM directives...")
        fm_directives = []
        fm_parsed = None
        
        if fm_input:
            try:
                nlp_agent = NLPParserAgent(mock_mode=mock_mode)
                fm_parsed = nlp_agent.parse(fm_input, fm_name)
                fm_directives = fm_parsed.get("directives", [])
                print(f"   ✅ Parsed {len(fm_directives)} directives")
                for d in fm_directives:
                    print(f"      {d.get('id')}: {d.get('action')} {d.get('target')} ({d.get('conviction')})")
            except Exception as e:
                print(f"   ❌ NLP parsing failed: {e}")
                fm_directives = []
        else:
            print("   ⏭️  No FM input — running on technical signals only")
        
        # Step 3: Fetch market data & run technical analysis
        print("\n📊 STEP 3: Running technical analysis...")
        tech_agent = TechnicalSignalsAgent()
        
        # Get unique instruments from portfolios
        unique_instruments = self.get_unique_instruments(holdings)
        print(f"   Analyzing {len(unique_instruments)} unique instruments...")
        
        technical_signals = {}
        for symbol in unique_instruments:
            try:
                result = tech_agent.analyze_instrument(symbol)
                # Map back to NSE:XXX format
                nse_code = "NSE:" + symbol.replace(".NS", "")
                technical_signals[nse_code] = result
                signal = result.get("signal", "N/A")
                score = result.get("composite_score", 0)
                print(f"   📈 {symbol:<20} Score: {score:>6.1f}  Signal: {signal}")
            except Exception as e:
                print(f"   ⚠️  {symbol}: {e}")
        
        # Sector analysis
        print("\n   🏭 Analyzing sector strength...")
        try:
            sector_signals = tech_agent.analyze_sector_indices()
            for s in sector_signals[:5]:
                print(f"   {s.get('sector', ''):<15} Score: {s.get('composite_score', 0):>6.1f}  Signal: {s.get('signal', '')}")
        except Exception as e:
            print(f"   ⚠️  Sector analysis failed: {e}")
            sector_signals = []
        
        # Step 4: Generate recommendations
        print("\n⚗️  STEP 4: Generating client recommendations...")
        rec_agent = RecommendationAgent(mock_mode=mock_mode)
        
        all_recommendations = rec_agent.generate_recommendations_batch(
            fm_directives, technical_signals, sector_signals, grouped
        )
        
        # Step 5: Compile results
        pipeline_result = {
            "run_timestamp": datetime.now().isoformat(),
            "run_date": str(date.today()),
            "fm_input": fm_input,
            "fm_parsed": fm_parsed,
            "fm_directives": fm_directives,
            "technical_signals_count": len(technical_signals),
            "sector_signals": sector_signals,
            "client_count": len(clients),
            "recommendations": all_recommendations,
            "total_recommendations": sum(
                len(r.get("recommendations", [])) for r in all_recommendations
            ),
        }
        
        # Save to outputs
        output_path = OUTPUT_DIR / f"pipeline_run_{date.today().isoformat()}.json"
        with open(output_path, 'w') as f:
            json.dump(pipeline_result, f, indent=2, default=str)
        
        print(f"\n{'═' * 60}")
        print(f"  ✅ PIPELINE COMPLETE")
        print(f"  Clients processed: {len(clients)}")
        print(f"  Total recommendations: {pipeline_result['total_recommendations']}")
        print(f"  Results saved: {output_path}")
        print(f"{'═' * 60}")
        
        self.results = pipeline_result
        return pipeline_result


if __name__ == "__main__":
    maestro = Maestro()
    
    # Sample FM input for testing
    sample_fm = """
    Energy sector is in a structural uptrend with PSU re-rating story intact. 
    Increase energy exposure across all portfolios. IT is entering a long-term lull - 
    reduce IT allocation by 50% wherever exposure exceeds 10%.
    Gold/Sensex ratio is entering an upward long-term trend - for clients without gold exposure,
    reallocate at least 20% to gold-heavy instruments over the next 3-6 months.
    For momentum portfolios, hold current positions but tighten stop-losses to 5%.
    Banking looks range-bound - hold existing, don't add fresh positions.
    """
    
    result = maestro.run_pipeline(fm_input=sample_fm, fm_name="Amit Jhaveri")
