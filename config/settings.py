"""
Jhaveri FIE — Central Configuration
All constants, paths, and settings in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "database"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_DIR = BASE_DIR / "templates"

# Create directories if they don't exist
for d in [DATA_DIR, DB_DIR, OUTPUT_DIR, TEMPLATE_DIR]:
    d.mkdir(exist_ok=True)

# ── API Keys ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# ── Database ──
DATABASE_URL = f"sqlite:///{DB_DIR / 'fie.db'}"

# ── Data Files ──
CLIENT_DATA_PATH = DATA_DIR / os.getenv("CLIENT_DATA_PATH", "data/clients.csv").replace("data/", "")
HOLDINGS_DATA_PATH = DATA_DIR / os.getenv("HOLDINGS_DATA_PATH", "data/holdings.csv").replace("data/", "")

# ── NSE Sector Index Mapping ──
# These are the yfinance symbols for Nifty sectoral indices
SECTOR_INDICES = {
    "NIFTY_50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_AUTO": "NIFTY_AUTO.NS",
    "NIFTY_FMCG": "^CNXFMCG",
    "NIFTY_METAL": "^CNXMETAL",
    "NIFTY_REALTY": "^CNXREALTY",
    "NIFTY_ENERGY": "^CNXENERGY",
    "NIFTY_INFRA": "^CNXINFRA",
    "NIFTY_PSE": "^CNXPSE",
    "NIFTY_MIDCAP_150": "NIFTY_MID_SELECT.NS",
    "NIFTY_SMALLCAP_250": "^CNXSC",
    "NIFTY_FINANCIAL": "NIFTY_FIN_SERVICE.NS",
    "NIFTY_MEDIA": "^CNXMEDIA",
    "NIFTY_CONSUMPTION": "^CNXCONSUM",
}

# ── Sector Classification for MF Schemes ──
SECTOR_KEYWORDS = {
    "IT": ["technology", "tech", "digital", "IT", "software", "information"],
    "BANKING": ["banking", "bank", "financial", "PSU bank"],
    "PHARMA": ["pharma", "healthcare", "health care", "medical"],
    "AUTO": ["auto", "automobile", "automotive"],
    "FMCG": ["FMCG", "consumer", "consumption"],
    "METAL": ["metal", "mining", "commodities", "commodity"],
    "ENERGY": ["energy", "power", "oil", "gas", "petroleum"],
    "REALTY": ["real estate", "realty", "housing", "infrastructure"],
    "INFRA": ["infrastructure", "infra", "construction"],
    "TELECOM": ["telecom", "communication"],
    "MEDIA": ["media", "entertainment"],
    "LARGECAP": ["large cap", "largecap", "large-cap", "bluechip", "nifty 50", "sensex"],
    "MIDCAP": ["mid cap", "midcap", "mid-cap", "nifty midcap"],
    "SMALLCAP": ["small cap", "smallcap", "small-cap"],
    "MULTICAP": ["multi cap", "multicap", "multi-cap", "flexi cap", "flexicap"],
    "HYBRID": ["hybrid", "balanced", "aggressive hybrid", "conservative hybrid"],
    "DEBT": ["debt", "bond", "gilt", "liquid", "money market", "credit risk", "corporate bond"],
    "ELSS": ["ELSS", "tax saver", "tax saving"],
    "INDEX": ["index", "passive", "nifty", "sensex"],
    "THEMATIC": ["thematic", "ESG", "international", "global", "MNC"],
}

# ── Technical Analysis Parameters ──
TECHNICAL_CONFIG = {
    # RSI
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    
    # Moving Averages
    "sma_short": 50,
    "sma_long": 200,
    
    # MACD
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    
    # Bollinger Bands
    "bb_period": 20,
    "bb_std": 2,
    
    # Volume
    "volume_avg_period": 20,
    "volume_surge_threshold": 2.0,  # 2x average
    
    # ADX
    "adx_period": 14,
    "adx_trending": 25,
    
    # ATR
    "atr_period": 14,
    
    # Stochastic RSI
    "stoch_rsi_period": 14,
    "stoch_rsi_oversold": 20,
    "stoch_rsi_overbought": 80,
    
    # Composite Score Weights
    "weight_trend": 0.30,
    "weight_momentum": 0.30,
    "weight_volume": 0.20,
    "weight_volatility": 0.10,
    "weight_relative_strength": 0.10,
}

# ── Score Thresholds ──
SIGNAL_THRESHOLDS = {
    "STRONG_BUY": 60,
    "BUY": 20,
    "HOLD_UPPER": 20,
    "HOLD_LOWER": -20,
    "SELL": -60,
    "STRONG_SELL": -100,
}

# ── Risk Guardrails ──
RISK_LIMITS = {
    "max_sector_concentration": {
        "CONSERVATIVE": 0.15,
        "MODERATE": 0.25,
        "AGGRESSIVE": 0.35,
    },
    "min_liquid_buffer": {
        "CONSERVATIVE": 0.20,
        "MODERATE": 0.10,
        "AGGRESSIVE": 0.05,
    },
    "max_single_stock": {
        "CONSERVATIVE": 0.05,
        "MODERATE": 0.08,
        "AGGRESSIVE": 0.12,
    },
}

# ── Confidence Scoring ──
CONFIDENCE_MATRIX = {
    "FM_AND_TECH_AGREE": (80, 100),
    "FM_ONLY_STRONG": (60, 80),
    "TECH_ONLY_STRONG": (40, 65),
    "FM_AND_TECH_NEUTRAL": (30, 50),
    "FM_AND_TECH_CONFLICT": (10, 30),
}

# ── AMFI API ──
AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_SCHEME_URL = "https://api.mfapi.in/mf"
