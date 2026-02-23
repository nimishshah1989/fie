"""
Jhaveri FIE — Database Models
All tables for the Financial Intelligence Engine.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Date, Text, Enum, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Instrument(Base):
    """Master universe of all tradeable instruments — MFs, ETFs, Stocks."""
    __tablename__ = "instruments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_code = Column(String(50), unique=True, nullable=False, index=True)  # AMFI code or NSE symbol
    instrument_name = Column(String(300), nullable=False)
    instrument_type = Column(String(20), nullable=False)  # MF, ETF, STOCK
    
    # For Mutual Funds
    amc_name = Column(String(200))
    scheme_type = Column(String(50))   # Open Ended, Close Ended, Interval
    scheme_category = Column(String(100))  # Large Cap, Mid Cap, Sectoral, etc.
    scheme_plan = Column(String(20))   # Regular, Direct
    
    # For Stocks & ETFs
    nse_symbol = Column(String(50), index=True)
    bse_code = Column(String(20))
    isin = Column(String(20))
    
    # Classification
    sector_primary = Column(String(50))
    sector_secondary = Column(String(50))
    market_cap_class = Column(String(20))  # LARGE, MID, SMALL
    
    # Current Data
    latest_nav = Column(Float)
    latest_price = Column(Float)
    nav_date = Column(Date)
    
    # Metadata
    benchmark_index = Column(String(100))
    nse_proxy_symbol = Column(String(50))  # yfinance symbol for technical analysis
    expense_ratio = Column(Float)
    aum_cr = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceData(Base):
    """Daily OHLCV price data for stocks, ETFs, and sector indices."""
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(Float)
    
    __table_args__ = (
        Index("ix_price_symbol_date", "symbol", "date", unique=True),
    )


class NAVData(Base):
    """Daily NAV data for mutual fund schemes."""
    __tablename__ = "nav_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_code = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    nav = Column(Float, nullable=False)
    
    __table_args__ = (
        Index("ix_nav_scheme_date", "scheme_code", "date", unique=True),
    )


class TechnicalSignal(Base):
    """Computed technical signals per instrument per day."""
    __tablename__ = "technical_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Individual Indicators
    rsi_14 = Column(Float)
    macd_line = Column(Float)
    macd_signal_line = Column(Float)
    macd_histogram = Column(Float)
    macd_crossover = Column(String(20))  # BULLISH, BEARISH, NEUTRAL
    
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    price_vs_200dma = Column(String(20))  # ABOVE, BELOW
    dma_cross = Column(String(20))  # GOLDEN_CROSS, DEATH_CROSS, NONE
    
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_position = Column(String(20))  # UPPER, MIDDLE, LOWER
    
    adx = Column(Float)
    adx_trend = Column(String(20))  # STRONG_TREND, WEAK_TREND, NO_TREND
    
    atr = Column(Float)
    
    obv = Column(Float)
    obv_trend = Column(String(20))  # RISING, FALLING, FLAT
    
    volume_ratio = Column(Float)  # current vol / 20-day avg
    volume_signal = Column(String(20))  # SURGE, HIGH, NORMAL, LOW
    
    stoch_rsi = Column(Float)
    
    # 52-week metrics
    high_52w = Column(Float)
    low_52w = Column(Float)
    pct_from_52w_high = Column(Float)
    pct_from_52w_low = Column(Float)
    
    # Composite Scores
    trend_score = Column(Float)  # -100 to +100
    momentum_score = Column(Float)
    volume_score = Column(Float)
    volatility_score = Column(Float)
    relative_strength_score = Column(Float)
    composite_score = Column(Float)  # Weighted average
    
    signal = Column(String(20))  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    
    __table_args__ = (
        Index("ix_tech_symbol_date", "symbol", "date", unique=True),
    )


class SectorStrength(Base):
    """Daily sector relative strength vs Nifty 50."""
    __tablename__ = "sector_strength"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sector = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False)
    
    # Relative performance
    rs_vs_nifty_1w = Column(Float)
    rs_vs_nifty_1m = Column(Float)
    rs_vs_nifty_3m = Column(Float)
    
    # Sector's own technicals
    rsi = Column(Float)
    trend = Column(String(20))  # UP, DOWN, FLAT
    composite_score = Column(Float)
    signal = Column(String(20))
    
    __table_args__ = (
        Index("ix_sector_date", "sector", "date", unique=True),
    )


class Client(Base):
    """Client master data."""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    risk_profile = Column(String(20), nullable=False)  # CONSERVATIVE, MODERATE, AGGRESSIVE
    strategy_type = Column(String(30))  # MF_ONLY, MF_STOCKS, MOMENTUM, PMS
    total_aum = Column(Float)
    contact_email = Column(String(200))
    relationship_manager = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    holdings = relationship("Holding", back_populates="client")


class Holding(Base):
    """Client portfolio holdings."""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(50), ForeignKey("clients.client_id"), nullable=False, index=True)
    instrument_code = Column(String(50), nullable=False)  # Links to instruments table
    instrument_name = Column(String(300))
    instrument_type = Column(String(20))  # MF, ETF, STOCK
    sector_tag = Column(String(50))
    
    current_value = Column(Float)
    cost_basis = Column(Float)
    units = Column(Float)
    allocation_pct = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_pct = Column(Float)
    
    purchase_date = Column(Date)
    sip_active = Column(Boolean, default=False)
    sip_amount = Column(Float)
    
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    client = relationship("Client", back_populates="holdings")


class FMDirective(Base):
    """Fund manager parsed directives from NLP input."""
    __tablename__ = "fm_directives"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    directive_id = Column(String(50), unique=True, nullable=False)
    
    raw_input = Column(Text)  # Original FM text
    
    action = Column(String(30), nullable=False)  # BUY, SELL, REDUCE_EXPOSURE, etc.
    target_type = Column(String(20))  # SECTOR, STOCK, MF, ETF, ASSET_CLASS
    target = Column(String(200))
    magnitude = Column(String(50))  # "15%", "PARTIAL", "TO_20%"
    condition = Column(String(200))  # "IMMEDIATE", "3%_DIP_FROM_CURRENT"
    timeframe = Column(String(50))
    conviction = Column(String(20))  # HIGH, MEDIUM, LOW
    rationale = Column(Text)
    applies_to = Column(String(50))  # ALL_CLIENTS, CONSERVATIVE_CLIENTS, etc.
    
    fm_name = Column(String(100))
    status = Column(String(20), default="ACTIVE")  # ACTIVE, EXPIRED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class Recommendation(Base):
    """Generated recommendations per client, pending FM approval."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rec_id = Column(String(50), unique=True, nullable=False)
    
    client_id = Column(String(50), ForeignKey("clients.client_id"), nullable=False, index=True)
    client_name = Column(String(200))
    
    action = Column(String(30), nullable=False)  # BUY, SELL, SWITCH, REDUCE, etc.
    instrument_code = Column(String(50))
    instrument_name = Column(String(300))
    instrument_type = Column(String(20))
    sector = Column(String(50))
    
    # Amounts
    current_value = Column(Float)
    recommended_amount = Column(Float)  # Amount to buy/sell/switch
    target_instrument = Column(String(300))  # For SWITCH recommendations
    
    # Reasoning
    fm_directive_id = Column(String(50))
    technical_score = Column(Float)
    technical_signal = Column(String(20))
    confidence = Column(Float)  # 0-100
    reasoning = Column(Text)
    
    # Portfolio Impact
    allocation_before = Column(Float)
    allocation_after = Column(Float)
    sector_allocation_before = Column(Float)
    sector_allocation_after = Column(Float)
    
    # Approval Workflow
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED, MODIFIED
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_date = Column(Date)


# ── Database Setup ──

def init_db(database_url: str = None):
    """Initialize database and create all tables."""
    from config.settings import DATABASE_URL
    url = database_url or DATABASE_URL
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session."""
    Session = sessionmaker(bind=engine)
    return Session()
