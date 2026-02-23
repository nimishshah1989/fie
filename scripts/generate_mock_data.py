"""
Jhaveri FIE — Generate Realistic Mock Client Data
Based on actual Jhaveri portfolio patterns (BJ53 momentum + JR100PASS strategies).
Creates 10 clients with MF SIP portfolios + 2 momentum portfolios.
"""

import csv
import os
import random

# ═══════════════════════════════════════════════
# REAL MOMENTUM PORTFOLIOS (from uploaded files)
# ═══════════════════════════════════════════════

MOMENTUM_BJ53 = {
    "client_id": "PMS-BJ53",
    "name": "Bhaderesh J Jhaveri",
    "risk_profile": "AGGRESSIVE",
    "strategy_type": "MOMENTUM",
    "total_aum": 5069246,
    "contact_email": "bj@jhaveri.com",
    "relationship_manager": "Internal",
    "holdings": [
        ("NSE:CPSEETF", "CPSE ETF", "ETF", "ENERGY", 414650, 403614, 8.18),
        ("NSE:GOLDBEES", "Nippon India Gold BeES", "ETF", "GOLD", 459909, 322699, 9.07),
        ("NSE:LIQUIDCASE", "ICICI Pru Liquid ETF", "ETF", "LIQUID", 941086, 934422, 18.56),
        ("NSE:LUPIN", "Lupin Ltd", "STOCK", "PHARMA", 199746, 203052, 3.94),
        ("NSE:NTPC", "NTPC Ltd", "STOCK", "ENERGY", 431130, 402606, 8.50),
        ("NSE:OIL", "Oil India Ltd", "STOCK", "ENERGY", 416582, 420690, 8.22),
        ("NSE:ONGC", "ONGC Ltd", "STOCK", "ENERGY", 415746, 409088, 8.20),
        ("NSE:PFC", "Power Finance Corp", "STOCK", "ENERGY", 433066, 432594, 8.54),
        ("NSE:PSUBNKBEES", "Nippon India PSU Bank ETF", "ETF", "BANKING", 210847, 196982, 4.16),
        ("NSE:SILVERBEES", "Nippon India Silver ETF", "ETF", "COMMODITIES", 122333, 127306, 2.41),
        ("NSE:SUNDARMFIN", "Sundaram Finance", "STOCK", "BANKING", 186408, 191938, 3.68),
        ("NSE:TATASTEEL", "Tata Steel", "STOCK", "METAL", 408802, 409880, 8.06),
        ("NSE:UNIONBANK", "Union Bank of India", "STOCK", "BANKING", 432381, 402150, 8.53),
    ]
}

MOMENTUM_JR100 = {
    "client_id": "PMS-JR100",
    "name": "Jhaveri Rohan (Passive Strategy)",
    "risk_profile": "AGGRESSIVE",
    "strategy_type": "MOMENTUM",
    "total_aum": 50565000,
    "contact_email": "jr@jhaveri.com",
    "relationship_manager": "Internal",
    "holdings": [
        ("NSE:BANKBEES", "Nippon India Bank BeES", "ETF", "BANKING", 2613251, 2548903, 5.17),
        ("NSE:CPSEETF", "CPSE ETF", "ETF", "ENERGY", 4141727, 3990726, 8.19),
        ("NSE:FMCGIETF", "FMCG ETF", "ETF", "FMCG", 916869, 988356, 1.81),
        ("NSE:GOLDBEES", "Nippon India Gold BeES", "ETF", "GOLD", 9731812, 5331184, 19.26),
        ("NSE:GROWWDEFNC", "Groww Defence ETF", "ETF", "DEFENCE", 1274440, 1302436, 2.52),
        ("NSE:HNGSNGEBEES", "Hang Seng BeES", "ETF", "INTERNATIONAL", 805485, 636263, 1.59),
        ("NSE:ICICIBSESENSEXETF", "ICICI Pru Sensex ETF", "ETF", "INDEX", 843061, 819859, 1.67),
        ("NSE:JUNIORBEES", "Nippon India Nifty Next 50", "ETF", "INDEX", 1661826, 1511418, 3.29),
        ("NSE:LIQUIDCASE", "ICICI Pru Liquid ETF", "ETF", "LIQUID", 6345332, 6294790, 12.55),
        ("NSE:METALETF", "Metal ETF", "ETF", "METAL", 2937946, 2415239, 5.81),
        ("NSE:NIFTYBEES", "Nippon India Nifty 50 BeES", "ETF", "INDEX", 4608880, 4692886, 9.12),
        ("NSE:MIDCAPETF", "Nippon India Midcap 150 ETF", "ETF", "MIDCAP", 1329832, 1362487, 2.63),
        ("NSE:PSUBNKBEES", "Nippon India PSU Bank ETF", "ETF", "BANKING", 2612628, 2062418, 5.17),
        ("NSE:SILVERBEES", "Nippon India Silver ETF", "ETF", "COMMODITIES", 1456633, 1436084, 2.88),
    ]
}

# ═══════════════════════════════════════════════
# REALISTIC MF UNIVERSE FOR MOCK CLIENTS
# ═══════════════════════════════════════════════

# Popular regular plan MF schemes that Jhaveri clients would hold
MF_UNIVERSE = {
    # Large Cap
    "LARGECAP": [
        ("120503", "ICICI Prudential Bluechip Fund - Regular Growth", "LARGECAP"),
        ("100356", "SBI Blue Chip Fund - Regular Growth", "LARGECAP"),
        ("118834", "Axis Bluechip Fund - Regular Growth", "LARGECAP"),
        ("100520", "Mirae Asset Large Cap Fund - Regular Growth", "LARGECAP"),
        ("105070", "Nippon India Large Cap Fund - Regular Growth", "LARGECAP"),
    ],
    # Flexi/Multi Cap
    "FLEXICAP": [
        ("112227", "HDFC Flexi Cap Fund - Regular Growth", "DIVERSIFIED"),
        ("100474", "Parag Parikh Flexi Cap Fund - Regular Growth", "DIVERSIFIED"),
        ("105078", "Kotak Flexicap Fund - Regular Growth", "DIVERSIFIED"),
        ("100381", "SBI Flexi Cap Fund - Regular Growth", "DIVERSIFIED"),
    ],
    # Mid Cap
    "MIDCAP": [
        ("118837", "Axis Midcap Fund - Regular Growth", "MIDCAP"),
        ("104480", "HDFC Mid-Cap Opportunities Fund - Regular Growth", "MIDCAP"),
        ("100497", "Kotak Emerging Equity Fund - Regular Growth", "MIDCAP"),
    ],
    # Small Cap
    "SMALLCAP": [
        ("120586", "SBI Small Cap Fund - Regular Growth", "SMALLCAP"),
        ("105085", "Nippon India Small Cap Fund - Regular Growth", "SMALLCAP"),
        ("103504", "Axis Small Cap Fund - Regular Growth", "SMALLCAP"),
    ],
    # Sectoral - IT
    "IT": [
        ("106098", "ICICI Prudential Technology Fund - Regular Growth", "IT"),
        ("100104", "SBI Technology Opportunities Fund - Regular Growth", "IT"),
    ],
    # Sectoral - Pharma
    "PHARMA": [
        ("106099", "ICICI Prudential Pharma Healthcare Fund - Regular Growth", "PHARMA"),
        ("120841", "Nippon India Pharma Fund - Regular Growth", "PHARMA"),
    ],
    # Sectoral - Banking
    "BANKING": [
        ("106100", "ICICI Prudential Banking & Financial Fund - Regular Growth", "BANKING"),
        ("100118", "SBI Banking & Financial Services Fund - Regular Growth", "BANKING"),
    ],
    # Gold
    "GOLD": [
        ("119780", "SBI Gold Fund - Regular Growth", "GOLD"),
        ("116277", "HDFC Gold Fund - Regular Growth", "GOLD"),
        ("120417", "Kotak Gold Fund - Regular Growth", "GOLD"),
    ],
    # Infrastructure / Energy
    "INFRA_ENERGY": [
        ("112228", "HDFC Infrastructure Fund - Regular Growth", "INFRA"),
        ("100116", "SBI Energy Opportunities Fund - Regular Growth", "ENERGY"),
        ("105042", "DSP Natural Resources Fund - Regular Growth", "ENERGY"),
    ],
    # Liquid
    "LIQUID": [
        ("119364", "SBI Liquid Fund - Regular Growth", "LIQUID"),
        ("118808", "HDFC Liquid Fund - Regular Growth", "LIQUID"),
        ("100524", "ICICI Prudential Liquid Fund - Regular Growth", "LIQUID"),
    ],
    # ELSS
    "ELSS": [
        ("100474", "Axis Long Term Equity Fund - Regular Growth", "ELSS"),
        ("100519", "Mirae Asset Tax Saver Fund - Regular Growth", "ELSS"),
    ],
}


def generate_mock_clients():
    """Generate 10 realistic MF clients + 2 momentum portfolios."""
    
    clients = []
    holdings = []
    
    # ── Client profiles with specific characteristics ──
    client_specs = [
        # (name, risk, aum, num_sips, has_gold, gold_pct)
        ("Arjun Kapoor", "MODERATE", 5000000, 5, False, 0),
        ("Meera Sharma", "CONSERVATIVE", 3500000, 4, True, 20),
        ("Vikram Reddy", "AGGRESSIVE", 15000000, 8, False, 0),
        ("Nandini Patel", "MODERATE", 7500000, 6, False, 0),
        ("Rajesh Gupta", "CONSERVATIVE", 2500000, 3, True, 18),
        ("Sunita Iyer", "MODERATE", 8500000, 5, False, 0),
        ("Deepak Malhotra", "AGGRESSIVE", 50000000, 7, True, 22),
        ("Priya Nair", "MODERATE", 4500000, 4, False, 0),
        ("Karthik Rao", "AGGRESSIVE", 12000000, 6, False, 0),
        ("Ananya Joshi", "CONSERVATIVE", 3000000, 3, False, 0),
    ]
    
    for idx, (name, risk, aum, num_sips, has_gold, gold_pct) in enumerate(client_specs):
        client_id = f"JHV-{idx+1:03d}"
        
        clients.append({
            "client_id": client_id,
            "name": name,
            "risk_profile": risk,
            "strategy_type": "MF_ONLY",
            "total_aum": aum,
            "contact_email": f"{name.split()[0].lower()}@email.com",
            "relationship_manager": "Amit Jhaveri" if idx % 2 == 0 else "Rohan Jhaveri",
        })
        
        # Build portfolio for this client
        portfolio = build_mf_portfolio(client_id, risk, aum, num_sips, has_gold, gold_pct)
        holdings.extend(portfolio)
    
    # Add the 2 real momentum portfolios
    for pf in [MOMENTUM_BJ53, MOMENTUM_JR100]:
        clients.append({
            "client_id": pf["client_id"],
            "name": pf["name"],
            "risk_profile": pf["risk_profile"],
            "strategy_type": pf["strategy_type"],
            "total_aum": pf["total_aum"],
            "contact_email": pf["contact_email"],
            "relationship_manager": pf["relationship_manager"],
        })
        
        for code, name, inst_type, sector, value, cost, hold_pct in pf["holdings"]:
            holdings.append({
                "client_id": pf["client_id"],
                "instrument_code": code,
                "instrument_name": name,
                "instrument_type": inst_type,
                "sector_tag": sector,
                "current_value": round(value),
                "cost_basis": round(cost),
                "allocation_pct": round(hold_pct, 1),
                "purchase_date": "2024-06-15",
                "sip_active": "FALSE",
                "sip_amount": 0,
            })
    
    return clients, holdings


def build_mf_portfolio(client_id, risk, aum, num_sips, has_gold, gold_pct):
    """Build a realistic MF SIP portfolio for a client."""
    
    holdings = []
    remaining_aum = aum
    
    # Define allocation templates by risk profile
    if risk == "CONSERVATIVE":
        # Heavy on large cap, some debt, low equity risk
        allocation_plan = [
            ("LARGECAP", 0.30),
            ("FLEXICAP", 0.20),
            ("LIQUID", 0.15),
            ("ELSS", 0.10),
            ("BANKING", 0.10),
            ("MIDCAP", 0.08),
            ("PHARMA", 0.07),
        ]
    elif risk == "MODERATE":
        allocation_plan = [
            ("LARGECAP", 0.20),
            ("FLEXICAP", 0.20),
            ("MIDCAP", 0.15),
            ("BANKING", 0.12),
            ("IT", 0.10),
            ("PHARMA", 0.08),
            ("INFRA_ENERGY", 0.08),
            ("SMALLCAP", 0.07),
        ]
    else:  # AGGRESSIVE
        allocation_plan = [
            ("MIDCAP", 0.18),
            ("SMALLCAP", 0.15),
            ("FLEXICAP", 0.15),
            ("BANKING", 0.12),
            ("IT", 0.10),
            ("INFRA_ENERGY", 0.10),
            ("PHARMA", 0.08),
            ("LARGECAP", 0.07),
            ("ELSS", 0.05),
        ]
    
    # If gold allocation, adjust
    if has_gold and gold_pct > 0:
        gold_alloc = gold_pct / 100
        # Proportionally reduce other allocations
        scale = 1 - gold_alloc
        allocation_plan = [(cat, alloc * scale) for cat, alloc in allocation_plan]
        allocation_plan.append(("GOLD", gold_alloc))
    
    # Take only num_sips allocations
    allocation_plan = allocation_plan[:num_sips]
    
    # Normalize to sum to ~100%
    total_alloc = sum(a for _, a in allocation_plan)
    allocation_plan = [(cat, alloc / total_alloc) for cat, alloc in allocation_plan]
    
    for category, alloc_pct in allocation_plan:
        funds = MF_UNIVERSE.get(category, MF_UNIVERSE["FLEXICAP"])
        fund = random.choice(funds)
        code, name, sector = fund
        
        value = round(aum * alloc_pct)
        # Random P&L between -8% and +25%
        pnl_pct = random.uniform(-0.08, 0.25)
        cost = round(value / (1 + pnl_pct))
        
        sip_amount = round(value * 0.02 / 1000) * 1000  # ~2% of value, rounded to nearest 1000
        sip_amount = max(5000, min(sip_amount, 100000))  # Between 5K and 1L
        
        purchase_months_ago = random.randint(6, 36)
        
        holdings.append({
            "client_id": client_id,
            "instrument_code": code,
            "instrument_name": name,
            "instrument_type": "MF",
            "sector_tag": sector,
            "current_value": value,
            "cost_basis": cost,
            "allocation_pct": round(alloc_pct * 100, 1),
            "purchase_date": f"202{random.choice([3,4])}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "sip_active": "TRUE",
            "sip_amount": sip_amount,
        })
    
    return holdings


def save_to_csv(clients, holdings, output_dir):
    """Save to CSV files."""
    
    clients_path = os.path.join(output_dir, "clients.csv")
    holdings_path = os.path.join(output_dir, "holdings.csv")
    
    # Save clients
    with open(clients_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "client_id", "name", "risk_profile", "strategy_type",
            "total_aum", "contact_email", "relationship_manager"
        ])
        writer.writeheader()
        writer.writerows(clients)
    
    # Save holdings
    with open(holdings_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "client_id", "instrument_code", "instrument_name", "instrument_type",
            "sector_tag", "current_value", "cost_basis", "allocation_pct",
            "purchase_date", "sip_active", "sip_amount"
        ])
        writer.writeheader()
        writer.writerows(holdings)
    
    print(f"✅ Saved {len(clients)} clients to {clients_path}")
    print(f"✅ Saved {len(holdings)} holdings to {holdings_path}")
    
    # Print summary
    print(f"\n{'═'*60}")
    print("CLIENT SUMMARY")
    print(f"{'═'*60}")
    for c in clients:
        h_count = len([h for h in holdings if h['client_id'] == c['client_id']])
        gold = any(h['sector_tag'] == 'GOLD' for h in holdings if h['client_id'] == c['client_id'])
        print(f"  {c['client_id']:<12} {c['name']:<30} {c['risk_profile']:<15} "
              f"₹{c['total_aum']:>12,.0f}  {h_count} holdings  {'🥇' if gold else '  '}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    clients, holdings = generate_mock_clients()
    save_to_csv(clients, holdings, output_dir)
