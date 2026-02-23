"""
Jhaveri FIE — Mock Engine
Simulates Claude API responses for testing without API credits.
Provides realistic NLP parsing and recommendation outputs.
"""

import re
import json
from datetime import datetime


def mock_parse_fm_input(fm_input: str, fm_name: str = "Fund Manager") -> dict:
    """
    Rule-based parser that extracts directives from FM text.
    Not as sophisticated as Claude, but works for testing the full pipeline.
    """
    
    text = fm_input.lower()
    directives = []
    dir_count = 0
    
    # Pattern matching for common FM directive patterns
    patterns = [
        # Energy/sector increase
        (r'(?:increase|add|overweight|bullish on|structural uptrend).{0,50}(energy|pharma|banking|auto|fmcg|metal|infra|realty)',
         "INCREASE_EXPOSURE", "SECTOR", None, "HIGH"),
        
        # IT/sector decrease  
        (r'(?:reduce|decrease|underweight|cut|lull|decline|bearish).{0,50}(it|technology|pharma|banking|auto|fmcg|metal)',
         "REDUCE_EXPOSURE", "SECTOR", None, "HIGH"),
        
        # Move from X to Y
        (r'(?:move|shift|switch|reallocate).{0,30}(?:from\s+)?(it|technology|banking|pharma|auto).{0,30}(?:to\s+)(energy|pharma|banking|gold|metal)',
         "SWITCH", "SECTOR", None, "HIGH"),
        
        # Gold allocation
        (r'(?:gold|gold.heavy|overindex on gold).{0,80}(?:reallocate|allocate|move).{0,30}(\d+)%',
         "INCREASE_ALLOCATION", "ASSET_CLASS", "GOLD", "HIGH"),
        
        # Book profits
        (r'book\s+profits?.{0,30}([\w\s]+?)(?:\s+if|\s+above|\s+when)',
         "BOOK_PROFITS", "STOCK", None, "MEDIUM"),
        
        # Hold pattern
        (r'(?:hold|maintain|keep).{0,30}(banking|pharma|energy|it|gold|current)',
         "HOLD", "SECTOR", None, "MEDIUM"),
        
        # Stop loss / tighten
        (r'(?:stop.?loss|tighten).{0,30}(\d+)%',
         "HOLD", "PORTFOLIO", None, "HIGH"),
        
        # Dont add / avoid
        (r"(?:don.?t add|avoid|stay away).{0,30}(banking|pharma|it|energy|auto|metal|midcap|smallcap)",
         "AVOID", "SECTOR", None, "MEDIUM"),
        
        # If exposure > X%, reduce
        (r'(?:if\s+)?exposure\s+(?:to\s+)?(it|technology|banking|pharma|auto)\s*(?:>|exceeds?|above)\s*(\d+)%',
         "REDUCE_EXPOSURE", "SECTOR", None, "HIGH"),
    ]
    
    for pattern, action, target_type, fixed_target, conviction in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            dir_count += 1
            groups = match.groups()
            
            target = fixed_target or (groups[0].upper() if groups else "UNKNOWN")
            target = target.replace("TECHNOLOGY", "IT")
            
            magnitude = None
            # Check for percentage in the matched text
            pct_match = re.search(r'(\d+)%', match.group())
            if pct_match:
                magnitude = f"{pct_match.group(1)}%"
            
            # Determine timeframe from context
            context = fm_input[max(0, match.start()-50):match.end()+50].lower()
            if any(w in context for w in ["3-6 months", "long term", "structural"]):
                timeframe = "LONG_TERM"
            elif any(w in context for w in ["next quarter", "2-3 months"]):
                timeframe = "MEDIUM_TERM"
            else:
                timeframe = "SHORT_TERM"
            
            # Determine applicability
            applies_to = "ALL_CLIENTS"
            if "momentum" in context:
                applies_to = "MOMENTUM_STRATEGY"
            elif "conservative" in context:
                applies_to = "CONSERVATIVE_CLIENTS"
            elif "without gold" in context:
                applies_to = "CLIENTS_WITHOUT_GOLD"
            elif "already holding gold" in context:
                applies_to = "CLIENTS_WITH_GOLD"
            
            # Extract rationale from surrounding text
            sentence = fm_input[max(0, match.start()-100):match.end()+100].strip()
            
            directives.append({
                "id": f"DIR-{dir_count:03d}",
                "action": action,
                "target_type": target_type,
                "target": target,
                "magnitude": magnitude,
                "condition": "IMMEDIATE",
                "timeframe": timeframe,
                "conviction": conviction,
                "rationale": sentence[:200],
                "applies_to": applies_to,
                "ambiguity_flag": None,
            })
    
    # If no patterns matched, create a generic directive
    if not directives:
        directives.append({
            "id": "DIR-001",
            "action": "REVIEW",
            "target_type": "PORTFOLIO",
            "target": "ALL",
            "magnitude": None,
            "condition": "IMMEDIATE",
            "timeframe": "SHORT_TERM",
            "conviction": "MEDIUM",
            "rationale": fm_input[:200],
            "applies_to": "ALL_CLIENTS",
            "ambiguity_flag": "Could not parse specific directives. Please review manually.",
        })
    
    result = {
        "directives": directives,
        "market_context": f"FM views parsed (mock mode): {len(directives)} directives extracted",
        "risk_stance": "NEUTRAL",
        "unprocessable_statements": [],
        "fm_name": fm_name,
        "parsed_at": datetime.now().isoformat(),
        "raw_input": fm_input,
        "directive_count": len(directives),
        "mode": "MOCK",
    }
    
    return result


def mock_generate_recommendations(fm_directives, technical_signals, sector_signals, client, holdings):
    """
    Generate recommendations using rule-based logic (no Claude API needed).
    """
    
    recommendations = []
    rec_count = 0
    
    aum = client.get("total_aum", 0)
    risk = client.get("risk_profile", "MODERATE")
    
    # Build sector allocation map
    sector_alloc = {}
    for h in holdings:
        sector = h.get("sector_tag", "OTHER")
        sector_alloc[sector] = sector_alloc.get(sector, 0) + h.get("allocation_pct", 0)
    
    # Process each FM directive against this client's portfolio
    for directive in fm_directives:
        action = directive.get("action", "")
        target = directive.get("target", "")
        target_type = directive.get("target_type", "")
        applies_to = directive.get("applies_to", "ALL_CLIENTS")
        magnitude = directive.get("magnitude", "")
        
        # Check if directive applies to this client
        if applies_to == "MOMENTUM_STRATEGY" and client.get("strategy_type") != "MOMENTUM":
            continue
        if applies_to == "CONSERVATIVE_CLIENTS" and risk != "CONSERVATIVE":
            continue
        if applies_to == "AGGRESSIVE_CLIENTS" and risk != "AGGRESSIVE":
            continue
        if applies_to == "CLIENTS_WITHOUT_GOLD" and "GOLD" in sector_alloc:
            continue
        if applies_to == "CLIENTS_WITH_GOLD" and "GOLD" not in sector_alloc:
            continue
        
        # Find matching holdings
        matching_holdings = []
        for h in holdings:
            if target_type == "SECTOR" and h.get("sector_tag", "").upper() == target.upper():
                matching_holdings.append(h)
            elif target_type == "STOCK" and target.upper() in h.get("instrument_code", "").upper():
                matching_holdings.append(h)
            elif target_type == "ASSET_CLASS" and h.get("sector_tag", "").upper() == target.upper():
                matching_holdings.append(h)
        
        # Generate specific recommendation based on action
        if action == "REDUCE_EXPOSURE" and matching_holdings:
            for h in matching_holdings:
                rec_count += 1
                pct = 50  # default
                if magnitude:
                    try:
                        pct = int(magnitude.replace("%", ""))
                    except:
                        pct = 50
                
                amount = round(h.get("current_value", 0) * pct / 100)
                
                # Get technical signal
                tech = technical_signals.get(h.get("instrument_code", ""), {})
                tech_score = tech.get("composite_score", 0)
                tech_signal = tech.get("signal", "N/A")
                
                # Confidence: FM says reduce + Tech confirms = HIGH
                if tech_score < -20:
                    confidence = 85
                elif tech_score < 0:
                    confidence = 70
                else:
                    confidence = 50  # FM says reduce but tech is neutral/positive
                
                alloc_before = h.get("allocation_pct", 0)
                alloc_after = round(alloc_before * (1 - pct/100), 1)
                
                recommendations.append({
                    "rec_id": f"REC-{rec_count:03d}",
                    "priority": "HIGH" if confidence > 70 else "MEDIUM",
                    "action": "REDEEM",
                    "instrument": h.get("instrument_name", ""),
                    "instrument_code": h.get("instrument_code", ""),
                    "sector": h.get("sector_tag", ""),
                    "amount": amount,
                    "target_instrument": None,
                    "reasoning": f"FM directive to reduce {target} by {pct}%. {directive.get('rationale', '')}",
                    "fm_directive_ref": directive.get("id"),
                    "technical_score": tech_score,
                    "technical_signal": tech_signal,
                    "confidence": confidence,
                    "allocation_before_pct": alloc_before,
                    "allocation_after_pct": alloc_after,
                    "expected_impact": f"Reduces {target} exposure from {alloc_before}% to {alloc_after}%"
                })
        
        elif action == "INCREASE_EXPOSURE" and target_type == "SECTOR":
            # Check if client already has exposure, if low, recommend adding
            current_exposure = sector_alloc.get(target.upper(), 0)
            if current_exposure < 15:  # Room to add
                rec_count += 1
                amount = round(aum * 0.05)  # Add 5% of AUM
                
                sector_tech = next((s for s in sector_signals if s.get("sector", "").upper() == target.upper()), {})
                tech_score = sector_tech.get("composite_score", 0)
                
                confidence = 75 if tech_score > 20 else 55
                
                recommendations.append({
                    "rec_id": f"REC-{rec_count:03d}",
                    "priority": "HIGH" if confidence > 70 else "MEDIUM",
                    "action": "INVEST",
                    "instrument": f"Recommended {target} sector fund",
                    "instrument_code": "",
                    "sector": target.upper(),
                    "amount": amount,
                    "target_instrument": None,
                    "reasoning": f"FM bullish on {target}. Current exposure only {current_exposure:.1f}%. {directive.get('rationale', '')}",
                    "fm_directive_ref": directive.get("id"),
                    "technical_score": tech_score,
                    "technical_signal": sector_tech.get("signal", "N/A"),
                    "confidence": confidence,
                    "allocation_before_pct": current_exposure,
                    "allocation_after_pct": round(current_exposure + 5, 1),
                    "expected_impact": f"Increases {target} from {current_exposure:.1f}% to ~{current_exposure+5:.1f}%"
                })
        
        elif action == "INCREASE_ALLOCATION" and target == "GOLD":
            if "GOLD" not in sector_alloc or sector_alloc.get("GOLD", 0) < 15:
                rec_count += 1
                target_pct = 20
                if magnitude:
                    try:
                        target_pct = int(magnitude.replace("%", "").replace("TO_", ""))
                    except:
                        target_pct = 20
                
                current_gold = sector_alloc.get("GOLD", 0)
                add_pct = target_pct - current_gold
                amount = round(aum * add_pct / 100)
                
                recommendations.append({
                    "rec_id": f"REC-{rec_count:03d}",
                    "priority": "HIGH",
                    "action": "INVEST",
                    "instrument": "Gold ETF / Gold Fund",
                    "instrument_code": "NSE:GOLDBEES",
                    "sector": "GOLD",
                    "amount": amount,
                    "target_instrument": "Nippon India Gold BeES / SBI Gold Fund",
                    "reasoning": f"FM directive: Gold entering long-term uptrend. Client has {current_gold:.1f}% gold, target {target_pct}%. {directive.get('rationale', '')}",
                    "fm_directive_ref": directive.get("id"),
                    "technical_score": 0,
                    "technical_signal": "N/A",
                    "confidence": 70,
                    "allocation_before_pct": current_gold,
                    "allocation_after_pct": target_pct,
                    "expected_impact": f"Adds gold from {current_gold:.1f}% to {target_pct}%"
                })
        
        elif action == "HOLD":
            for h in matching_holdings:
                rec_count += 1
                recommendations.append({
                    "rec_id": f"REC-{rec_count:03d}",
                    "priority": "LOW",
                    "action": "HOLD",
                    "instrument": h.get("instrument_name", ""),
                    "instrument_code": h.get("instrument_code", ""),
                    "sector": h.get("sector_tag", ""),
                    "amount": 0,
                    "target_instrument": None,
                    "reasoning": f"FM directive: Hold position. {directive.get('rationale', '')}",
                    "fm_directive_ref": directive.get("id"),
                    "technical_score": technical_signals.get(h.get("instrument_code", ""), {}).get("composite_score", 0),
                    "technical_signal": technical_signals.get(h.get("instrument_code", ""), {}).get("signal", "N/A"),
                    "confidence": 60,
                    "allocation_before_pct": h.get("allocation_pct", 0),
                    "allocation_after_pct": h.get("allocation_pct", 0),
                    "expected_impact": "No change — maintain position"
                })
    
    # Check for pure technical alerts (no FM directive but strong signal)
    for h in holdings:
        code = h.get("instrument_code", "")
        tech = technical_signals.get(code, {})
        if tech.get("signal") in ["STRONG_SELL", "STRONG_BUY"]:
            # Check if already covered by a directive
            covered = any(r.get("instrument_code") == code for r in recommendations)
            if not covered:
                rec_count += 1
                recommendations.append({
                    "rec_id": f"REC-{rec_count:03d}",
                    "priority": "MEDIUM",
                    "action": "REVIEW" if tech["signal"] == "STRONG_SELL" else "ACCUMULATE",
                    "instrument": h.get("instrument_name", ""),
                    "instrument_code": code,
                    "sector": h.get("sector_tag", ""),
                    "amount": 0,
                    "target_instrument": None,
                    "reasoning": f"TECHNICAL ALERT: {tech['signal']} signal (score: {tech.get('composite_score', 0)}). No FM directive — flagging for review.",
                    "fm_directive_ref": None,
                    "technical_score": tech.get("composite_score", 0),
                    "technical_signal": tech.get("signal"),
                    "confidence": 45,
                    "allocation_before_pct": h.get("allocation_pct", 0),
                    "allocation_after_pct": h.get("allocation_pct", 0),
                    "expected_impact": "FM review needed"
                })
    
    return {
        "client_summary": {
            "client_id": client.get("client_id"),
            "name": client.get("name"),
            "risk_profile": client.get("risk_profile"),
            "total_aum": client.get("total_aum", 0),
            "portfolio_health": "NEEDS_REBALANCING" if recommendations else "GOOD"
        },
        "recommendations": sorted(recommendations, key=lambda x: -x.get("confidence", 0)),
        "portfolio_impact": {
            "sector_allocation_after": sector_alloc,
            "risk_assessment": f"{len(recommendations)} actions recommended for {client.get('name')}"
        },
        "alerts": [],
        "generated_at": datetime.now().isoformat(),
        "mode": "MOCK"
    }
