"""
Jhaveri FIE — Master Instrument Universe Builder
Pulls all active MFs from AMFI, stocks from NSE, and ETFs.
Run this once to seed the database, then daily to update NAVs.

Usage:
    python scripts/build_universe.py          # Full build
    python scripts/build_universe.py --nav    # NAV update only
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import pandas as pd
from datetime import datetime, date
from tqdm import tqdm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Instrument, init_db, get_session
from config.settings import DATABASE_URL, SECTOR_KEYWORDS, AMFI_NAV_URL

# ══════════════════════════════════════════════
# PART 1: MUTUAL FUNDS FROM AMFI
# ══════════════════════════════════════════════

def fetch_amfi_nav_data():
    """
    Fetch all MF NAV data from AMFI's official text file.
    This is THE authoritative source — every active MF scheme in India.
    Returns a list of dicts with scheme details and latest NAV.
    """
    print("📡 Fetching AMFI NAV data (all mutual fund schemes)...")
    
    try:
        response = requests.get(AMFI_NAV_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch AMFI data: {e}")
        return []
    
    lines = response.text.strip().split("\n")
    schemes = []
    current_amc = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        
        parts = line.split(";")
        
        # AMC header lines (no semicolons, or different structure)
        if len(parts) == 1:
            # This is an AMC name header
            current_amc = line.strip()
            continue
        
        if len(parts) >= 6:
            try:
                scheme_code = parts[0].strip()
                # Skip if scheme code is not numeric
                if not scheme_code.isdigit():
                    current_amc = line.strip()
                    continue
                    
                isin_div_payout = parts[1].strip() if len(parts) > 1 else ""
                isin_div_reinvest = parts[2].strip() if len(parts) > 2 else ""
                scheme_name = parts[3].strip() if len(parts) > 3 else ""
                nav_str = parts[4].strip() if len(parts) > 4 else ""
                nav_date_str = parts[5].strip() if len(parts) > 5 else ""
                
                # Parse NAV
                try:
                    nav = float(nav_str) if nav_str and nav_str != "N.A." else None
                except ValueError:
                    nav = None
                
                # Parse date
                try:
                    nav_date = datetime.strptime(nav_date_str, "%d-%b-%Y").date() if nav_date_str else None
                except ValueError:
                    nav_date = None
                
                # Determine scheme type
                scheme_plan = "DIRECT" if "direct" in scheme_name.lower() else "REGULAR"
                
                # Determine scheme category from name
                category = classify_mf_category(scheme_name)
                sector = classify_mf_sector(scheme_name)
                
                schemes.append({
                    "instrument_code": scheme_code,
                    "instrument_name": scheme_name,
                    "instrument_type": "MF",
                    "amc_name": current_amc,
                    "scheme_plan": scheme_plan,
                    "scheme_category": category,
                    "sector_primary": sector,
                    "isin": isin_div_payout or isin_div_reinvest,
                    "latest_nav": nav,
                    "nav_date": nav_date,
                    "is_active": True,
                })
            except Exception as e:
                continue  # Skip malformed lines
    
    print(f"✅ Parsed {len(schemes)} MF schemes from AMFI")
    return schemes


def classify_mf_category(name: str) -> str:
    """Classify MF scheme into category based on name."""
    name_lower = name.lower()
    
    if "liquid" in name_lower or "money market" in name_lower:
        return "LIQUID"
    elif "overnight" in name_lower:
        return "OVERNIGHT"
    elif "gilt" in name_lower:
        return "GILT"
    elif "corporate bond" in name_lower or "credit risk" in name_lower:
        return "CORPORATE_BOND"
    elif "short" in name_lower and ("term" in name_lower or "duration" in name_lower):
        return "SHORT_DURATION"
    elif "medium" in name_lower and ("term" in name_lower or "duration" in name_lower):
        return "MEDIUM_DURATION"
    elif "long" in name_lower and ("term" in name_lower or "duration" in name_lower):
        return "LONG_DURATION"
    elif "dynamic bond" in name_lower:
        return "DYNAMIC_BOND"
    elif "elss" in name_lower or "tax" in name_lower:
        return "ELSS"
    elif "index" in name_lower or "nifty" in name_lower or "sensex" in name_lower:
        if "next 50" in name_lower or "midcap" in name_lower:
            return "INDEX_MIDCAP"
        elif "small" in name_lower:
            return "INDEX_SMALLCAP"
        return "INDEX"
    elif "etf" in name_lower:
        return "ETF"
    elif "large cap" in name_lower or "large-cap" in name_lower or "largecap" in name_lower:
        return "LARGE_CAP"
    elif "mid cap" in name_lower or "mid-cap" in name_lower or "midcap" in name_lower:
        if "small" in name_lower:
            return "MID_SMALL_CAP"
        return "MID_CAP"
    elif "small cap" in name_lower or "small-cap" in name_lower or "smallcap" in name_lower:
        return "SMALL_CAP"
    elif "multi cap" in name_lower or "multicap" in name_lower:
        return "MULTI_CAP"
    elif "flexi cap" in name_lower or "flexicap" in name_lower or "flexi-cap" in name_lower:
        return "FLEXI_CAP"
    elif "focused" in name_lower:
        return "FOCUSED"
    elif "value" in name_lower or "contra" in name_lower:
        return "VALUE"
    elif "dividend yield" in name_lower:
        return "DIVIDEND_YIELD"
    elif "aggressive hybrid" in name_lower or "balanced advantage" in name_lower:
        return "AGGRESSIVE_HYBRID"
    elif "conservative hybrid" in name_lower:
        return "CONSERVATIVE_HYBRID"
    elif "hybrid" in name_lower or "balanced" in name_lower:
        return "HYBRID"
    elif "arbitrage" in name_lower:
        return "ARBITRAGE"
    elif "equity savings" in name_lower:
        return "EQUITY_SAVINGS"
    elif "international" in name_lower or "global" in name_lower or "us " in name_lower:
        return "INTERNATIONAL"
    elif "sectoral" in name_lower or "thematic" in name_lower:
        return "SECTORAL_THEMATIC"
    elif any(kw in name_lower for kw in ["banking", "financial", "pharma", "healthcare", "technology", 
                                          "infrastructure", "consumption", "manufacturing", "energy",
                                          "auto", "metal", "realty", "media", "telecom"]):
        return "SECTORAL_THEMATIC"
    elif "retirement" in name_lower or "pension" in name_lower:
        return "RETIREMENT"
    elif "children" in name_lower:
        return "CHILDREN"
    elif "fund of fund" in name_lower or "fof" in name_lower:
        return "FUND_OF_FUNDS"
    else:
        return "OTHER"


def classify_mf_sector(name: str) -> str:
    """Classify MF into primary sector based on name."""
    name_lower = name.lower()
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw.lower() in name_lower for kw in keywords):
            return sector
    
    # If it's a broad equity fund, mark as DIVERSIFIED
    if any(kw in name_lower for kw in ["large cap", "mid cap", "small cap", "flexi", "multi", "focused", "value"]):
        return "DIVERSIFIED"
    
    return "OTHER"


# ══════════════════════════════════════════════
# PART 2: NSE STOCKS 
# ══════════════════════════════════════════════

def fetch_nse_stock_list():
    """
    Fetch list of all NSE-listed stocks.
    Uses the Nifty Total Market index CSV which covers ~750 stocks,
    and supplements with broader NSE equity list.
    """
    print("📡 Fetching NSE stock list...")
    
    stocks = []
    
    # Method 1: Fetch from NSE indices
    nifty_indices = {
        "NIFTY_50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
        "NIFTY_NEXT_50": "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
        "NIFTY_MIDCAP_150": "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
        "NIFTY_SMALLCAP_250": "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
        "NIFTY_500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/csv",
    }
    
    seen_symbols = set()
    
    for index_name, url in nifty_indices.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # Parse CSV
                from io import StringIO
                df = pd.read_csv(StringIO(response.text))
                
                for _, row in df.iterrows():
                    symbol = str(row.get("Symbol", "")).strip()
                    if not symbol or symbol in seen_symbols:
                        continue
                    
                    seen_symbols.add(symbol)
                    company_name = str(row.get("Company Name", "")).strip()
                    industry = str(row.get("Industry", "")).strip()
                    isin = str(row.get("ISIN Code", "")).strip()
                    
                    # Determine market cap class
                    if index_name in ["NIFTY_50", "NIFTY_NEXT_50"]:
                        mcap = "LARGE"
                    elif index_name == "NIFTY_MIDCAP_150":
                        mcap = "MID"
                    elif index_name == "NIFTY_SMALLCAP_250":
                        mcap = "SMALL"
                    else:
                        mcap = classify_stock_mcap(index_name)
                    
                    sector = classify_stock_sector(industry)
                    
                    stocks.append({
                        "instrument_code": f"NSE:{symbol}",
                        "instrument_name": company_name,
                        "instrument_type": "STOCK",
                        "nse_symbol": symbol,
                        "isin": isin,
                        "sector_primary": sector,
                        "market_cap_class": mcap,
                        "nse_proxy_symbol": f"{symbol}.NS",
                        "is_active": True,
                    })
                    
                print(f"  ✅ {index_name}: {len(df)} stocks")
            else:
                print(f"  ⚠️ {index_name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ⚠️ {index_name}: {e}")
    
    # Fallback: If NSE CSVs fail, use a curated Nifty 500 approach via yfinance
    if len(stocks) < 100:
        print("  ⚠️ NSE CSVs partially failed. Using yfinance as fallback for major stocks...")
        stocks.extend(get_fallback_stock_list(seen_symbols))
    
    print(f"✅ Total stocks: {len(stocks)}")
    return stocks


def get_fallback_stock_list(seen_symbols: set):
    """Fallback list of major NSE stocks if CSV download fails."""
    # Top 100 NSE stocks by market cap — hardcoded fallback
    major_stocks = [
        ("RELIANCE", "Reliance Industries", "ENERGY", "LARGE"),
        ("TCS", "Tata Consultancy Services", "IT", "LARGE"),
        ("HDFCBANK", "HDFC Bank", "BANKING", "LARGE"),
        ("INFY", "Infosys", "IT", "LARGE"),
        ("ICICIBANK", "ICICI Bank", "BANKING", "LARGE"),
        ("HINDUNILVR", "Hindustan Unilever", "FMCG", "LARGE"),
        ("BHARTIARTL", "Bharti Airtel", "TELECOM", "LARGE"),
        ("SBIN", "State Bank of India", "BANKING", "LARGE"),
        ("ITC", "ITC", "FMCG", "LARGE"),
        ("KOTAKBANK", "Kotak Mahindra Bank", "BANKING", "LARGE"),
        ("LT", "Larsen & Toubro", "INFRA", "LARGE"),
        ("AXISBANK", "Axis Bank", "BANKING", "LARGE"),
        ("BAJFINANCE", "Bajaj Finance", "BANKING", "LARGE"),
        ("MARUTI", "Maruti Suzuki", "AUTO", "LARGE"),
        ("HCLTECH", "HCL Technologies", "IT", "LARGE"),
        ("WIPRO", "Wipro", "IT", "LARGE"),
        ("SUNPHARMA", "Sun Pharmaceutical", "PHARMA", "LARGE"),
        ("TITAN", "Titan Company", "FMCG", "LARGE"),
        ("TATAMOTORS", "Tata Motors", "AUTO", "LARGE"),
        ("ASIANPAINT", "Asian Paints", "FMCG", "LARGE"),
        ("ULTRACEMCO", "UltraTech Cement", "INFRA", "LARGE"),
        ("ONGC", "Oil & Natural Gas Corp", "ENERGY", "LARGE"),
        ("NTPC", "NTPC", "ENERGY", "LARGE"),
        ("POWERGRID", "Power Grid Corp", "ENERGY", "LARGE"),
        ("M&M", "Mahindra & Mahindra", "AUTO", "LARGE"),
        ("JSWSTEEL", "JSW Steel", "METAL", "LARGE"),
        ("TATASTEEL", "Tata Steel", "METAL", "LARGE"),
        ("ADANIENT", "Adani Enterprises", "DIVERSIFIED", "LARGE"),
        ("ADANIPORTS", "Adani Ports", "INFRA", "LARGE"),
        ("BAJAJ-AUTO", "Bajaj Auto", "AUTO", "LARGE"),
        ("BAJAJFINSV", "Bajaj Finserv", "BANKING", "LARGE"),
        ("TECHM", "Tech Mahindra", "IT", "LARGE"),
        ("DRREDDY", "Dr Reddy's Laboratories", "PHARMA", "LARGE"),
        ("CIPLA", "Cipla", "PHARMA", "LARGE"),
        ("DIVISLAB", "Divi's Laboratories", "PHARMA", "LARGE"),
        ("BRITANNIA", "Britannia Industries", "FMCG", "LARGE"),
        ("NESTLEIND", "Nestle India", "FMCG", "LARGE"),
        ("COALINDIA", "Coal India", "ENERGY", "LARGE"),
        ("HEROMOTOCO", "Hero MotoCorp", "AUTO", "LARGE"),
        ("EICHERMOT", "Eicher Motors", "AUTO", "LARGE"),
        ("GRASIM", "Grasim Industries", "INFRA", "LARGE"),
        ("INDUSINDBK", "IndusInd Bank", "BANKING", "LARGE"),
        ("APOLLOHOSP", "Apollo Hospitals", "PHARMA", "LARGE"),
        ("HINDALCO", "Hindalco Industries", "METAL", "LARGE"),
        ("TATACONSUM", "Tata Consumer Products", "FMCG", "LARGE"),
        ("BPCL", "Bharat Petroleum", "ENERGY", "LARGE"),
        ("HDFCLIFE", "HDFC Life Insurance", "BANKING", "LARGE"),
        ("SBILIFE", "SBI Life Insurance", "BANKING", "LARGE"),
        ("DABUR", "Dabur India", "FMCG", "MID"),
        ("PIDILITIND", "Pidilite Industries", "FMCG", "MID"),
    ]
    
    stocks = []
    for symbol, name, sector, mcap in major_stocks:
        if symbol not in seen_symbols:
            stocks.append({
                "instrument_code": f"NSE:{symbol}",
                "instrument_name": name,
                "instrument_type": "STOCK",
                "nse_symbol": symbol,
                "sector_primary": sector,
                "market_cap_class": mcap,
                "nse_proxy_symbol": f"{symbol}.NS",
                "is_active": True,
            })
    
    return stocks


def classify_stock_sector(industry: str) -> str:
    """Map NSE industry classification to our sector tags."""
    industry_lower = industry.lower() if industry else ""
    
    mapping = {
        "IT": ["it ", "software", "technology", "computer"],
        "BANKING": ["bank", "financial", "insurance", "nbfc", "housing finance"],
        "PHARMA": ["pharma", "healthcare", "hospital", "drug", "medical"],
        "AUTO": ["auto", "automobile", "tyre", "tractor"],
        "FMCG": ["fmcg", "consumer", "food", "beverage", "personal care", "tobacco"],
        "METAL": ["metal", "steel", "aluminium", "copper", "mining"],
        "ENERGY": ["oil", "gas", "petroleum", "energy", "power", "coal", "refinery"],
        "INFRA": ["infrastructure", "construction", "cement", "engineering", "capital goods"],
        "REALTY": ["real estate", "realty", "housing"],
        "TELECOM": ["telecom", "communication"],
        "MEDIA": ["media", "entertainment", "broadcasting"],
        "CHEMICAL": ["chemical", "fertilizer", "agrochemical"],
        "TEXTILE": ["textile", "garment", "apparel"],
    }
    
    for sector, keywords in mapping.items():
        if any(kw in industry_lower for kw in keywords):
            return sector
    
    return "OTHER"


def classify_stock_mcap(index_name: str) -> str:
    """Infer market cap from index membership."""
    if "50" in index_name or "LARGE" in index_name:
        return "LARGE"
    elif "MID" in index_name:
        return "MID"
    elif "SMALL" in index_name:
        return "SMALL"
    return "MID"


# ══════════════════════════════════════════════
# PART 3: ETFs
# ══════════════════════════════════════════════

def fetch_etf_list():
    """Get list of popular Indian ETFs."""
    print("📡 Fetching ETF list...")
    
    # Major Indian ETFs — curated list (AMFI covers MF ETFs, this adds trading ETFs)
    etfs = [
        ("NIFTYBEES", "Nippon India Nifty 50 BeES", "INDEX", "^NSEI"),
        ("BANKBEES", "Nippon India Bank BeES", "BANKING", "^NSEBANK"),
        ("JUNIORBEES", "Nippon India Nifty Next 50 BeES", "INDEX", "^NSEI"),
        ("ITBEES", "Nippon India Nifty IT ETF", "IT", "^CNXIT"),
        ("PHARMABEES", "Nippon India Nifty Pharma ETF", "PHARMA", "^CNXPHARMA"),
        ("GOLDBEES", "Nippon India Gold BeES", "GOLD", None),
        ("LIQUIDBEES", "Nippon India Liquid BeES", "LIQUID", None),
        ("SETFNIF50", "SBI Nifty 50 ETF", "INDEX", "^NSEI"),
        ("SETFNIFBK", "SBI Nifty Bank ETF", "BANKING", "^NSEBANK"),
        ("HDFCNIFTY", "HDFC Nifty 50 ETF", "INDEX", "^NSEI"),
        ("ICICIB22", "ICICI Pru Bharat 22 ETF", "INDEX", None),
        ("MAFANG", "Mirae Asset NYSE FANG+ ETF", "INTERNATIONAL", None),
        ("MON100", "Motilal Oswal Nasdaq 100 ETF", "INTERNATIONAL", None),
        ("CPSEETF", "Nippon India CPSE ETF", "ENERGY", None),
        ("MOM50", "Motilal Oswal Nifty Midcap 150 Momentum 50 ETF", "MIDCAP", None),
        ("AUTOBEES", "Nippon India Nifty Auto ETF", "AUTO", None),
        ("CONSUMBEES", "Nippon India Nifty Consumption ETF", "FMCG", None),
        ("INFRABEES", "Nippon India Nifty Infra ETF", "INFRA", None),
        ("PSUBNKBEES", "Nippon India Nifty PSU Bank ETF", "BANKING", None),
        ("SILVERBEES", "Nippon India Silver ETF", "COMMODITIES", None),
        ("MOM100", "Motilal Oswal Nifty Midcap 100 ETF", "MIDCAP", None),
        ("MIDCAPETF", "Nippon India Nifty Midcap 150 ETF", "MIDCAP", None),
        ("HDFCSML250", "HDFC Nifty Smallcap 250 ETF", "SMALLCAP", None),
    ]
    
    results = []
    for symbol, name, sector, proxy in etfs:
        results.append({
            "instrument_code": f"ETF:{symbol}",
            "instrument_name": name,
            "instrument_type": "ETF",
            "nse_symbol": symbol,
            "sector_primary": sector,
            "nse_proxy_symbol": f"{symbol}.NS",
            "benchmark_index": proxy,
            "is_active": True,
        })
    
    print(f"✅ {len(results)} ETFs catalogued")
    return results


# ══════════════════════════════════════════════
# PART 4: SAVE TO DATABASE
# ══════════════════════════════════════════════

def save_to_database(mf_schemes, stocks, etfs, filter_regular_only=True):
    """Save all instruments to SQLite database."""
    
    engine = init_db()
    session = get_session(engine)
    
    total_added = 0
    total_updated = 0
    
    # Filter MFs: Regular plans only (as per Nimish's requirement)
    if filter_regular_only:
        mf_before = len(mf_schemes)
        mf_schemes = [s for s in mf_schemes if s.get("scheme_plan") == "REGULAR"]
        print(f"📋 Filtered to REGULAR plans: {mf_before} → {len(mf_schemes)} MF schemes")
    
    all_instruments = []
    
    # Process MFs
    for scheme in mf_schemes:
        all_instruments.append(scheme)
    
    # Process Stocks
    for stock in stocks:
        all_instruments.append(stock)
    
    # Process ETFs
    for etf in etfs:
        all_instruments.append(etf)
    
    print(f"\n💾 Saving {len(all_instruments)} instruments to database...")
    
    for item in tqdm(all_instruments, desc="Saving"):
        existing = session.query(Instrument).filter_by(
            instrument_code=item["instrument_code"]
        ).first()
        
        if existing:
            # Update existing
            for key, value in item.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            total_updated += 1
        else:
            # Insert new
            inst = Instrument(**{k: v for k, v in item.items() if hasattr(Instrument, k)})
            session.add(inst)
            total_added += 1
    
    session.commit()
    session.close()
    
    print(f"\n{'═' * 50}")
    print(f"✅ DATABASE UPDATED SUCCESSFULLY")
    print(f"   New instruments added: {total_added}")
    print(f"   Existing updated: {total_updated}")
    print(f"   Total in database: {total_added + total_updated}")
    print(f"{'═' * 50}")


def print_summary(engine):
    """Print database summary after build."""
    session = get_session(engine)
    
    total = session.query(Instrument).count()
    mf_count = session.query(Instrument).filter_by(instrument_type="MF").count()
    stock_count = session.query(Instrument).filter_by(instrument_type="STOCK").count()
    etf_count = session.query(Instrument).filter_by(instrument_type="ETF").count()
    
    print(f"\n📊 INSTRUMENT UNIVERSE SUMMARY")
    print(f"   {'Mutual Funds (Regular):':<30} {mf_count:>6}")
    print(f"   {'NSE/BSE Stocks:':<30} {stock_count:>6}")
    print(f"   {'ETFs:':<30} {etf_count:>6}")
    print(f"   {'─' * 36}")
    print(f"   {'TOTAL:':<30} {total:>6}")
    
    # Sector distribution for stocks
    print(f"\n📊 STOCK SECTOR DISTRIBUTION")
    from sqlalchemy import func
    sector_counts = (
        session.query(Instrument.sector_primary, func.count())
        .filter_by(instrument_type="STOCK")
        .group_by(Instrument.sector_primary)
        .order_by(func.count().desc())
        .all()
    )
    for sector, count in sector_counts:
        print(f"   {sector or 'UNCLASSIFIED':<25} {count:>5}")
    
    session.close()


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    """Build the complete instrument universe."""
    
    print("═" * 60)
    print("  JHAVERI FIE — MASTER INSTRUMENT UNIVERSE BUILDER")
    print("═" * 60)
    print()
    
    # Step 1: Fetch all data
    mf_schemes = fetch_amfi_nav_data()
    stocks = fetch_nse_stock_list()
    etfs = fetch_etf_list()
    
    # Step 2: Save to database
    save_to_database(mf_schemes, stocks, etfs, filter_regular_only=True)
    
    # Step 3: Print summary
    engine = init_db()
    print_summary(engine)
    
    print("\n🎉 Universe build complete! Database ready at: database/fie.db")


if __name__ == "__main__":
    main()
