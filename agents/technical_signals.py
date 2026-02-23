"""
Jhaveri FIE — Agent 3: Technical Signals Agent
Runs 12+ technical indicators on every instrument and generates composite scores.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from config.settings import TECHNICAL_CONFIG as TC, SECTOR_INDICES, SIGNAL_THRESHOLDS
from database.models import (
    PriceData, TechnicalSignal, SectorStrength, 
    init_db, get_session
)

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    print("⚠️  pandas_ta not installed. Using manual indicator calculations.")

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️  yfinance not installed.")


class TechnicalSignalsAgent:
    """Agent 3: Computes technical indicators and composite scores."""
    
    def __init__(self):
        self.engine = init_db()
    
    # ══════════════════════════════════════════════
    # DATA FETCHING
    # ══════════════════════════════════════════════
    
    def fetch_price_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol. First checks local cache, then yfinance.
        """
        if not HAS_YFINANCE:
            return pd.DataFrame()
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df.empty:
                return df
            
            df = df.reset_index()
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            
            # Ensure we have the columns we need
            required = ["date", "open", "high", "low", "close", "volume"]
            if not all(c in df.columns for c in required):
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            print(f"  ⚠️ Failed to fetch {symbol}: {e}")
            return pd.DataFrame()
    
    def cache_price_data(self, symbol: str, df: pd.DataFrame):
        """Save price data to local database cache."""
        session = get_session(self.engine)
        
        for _, row in df.iterrows():
            try:
                price_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]
                
                existing = session.query(PriceData).filter_by(
                    symbol=symbol, date=price_date
                ).first()
                
                if not existing:
                    pd_record = PriceData(
                        symbol=symbol,
                        date=price_date,
                        open=row.get("open"),
                        high=row.get("high"),
                        low=row.get("low"),
                        close=row.get("close"),
                        volume=row.get("volume"),
                        adj_close=row.get("adj_close", row.get("close")),
                    )
                    session.add(pd_record)
            except Exception:
                continue
        
        session.commit()
        session.close()
    
    # ══════════════════════════════════════════════
    # TECHNICAL INDICATORS
    # ══════════════════════════════════════════════
    
    def compute_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all technical indicators on a price DataFrame."""
        
        if df.empty or len(df) < 50:
            return df
        
        df = df.copy()
        df = df.sort_values("date").reset_index(drop=True)
        
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        
        # ── RSI (14) ──
        df["rsi_14"] = self._compute_rsi(close, TC["rsi_period"])
        
        # ── MACD (12, 26, 9) ──
        macd_line, signal_line, histogram = self._compute_macd(
            close, TC["macd_fast"], TC["macd_slow"], TC["macd_signal"]
        )
        df["macd_line"] = macd_line
        df["macd_signal_line"] = signal_line
        df["macd_histogram"] = histogram
        df["macd_crossover"] = self._macd_crossover(macd_line, signal_line)
        
        # ── Moving Averages ──
        df["sma_50"] = close.rolling(window=TC["sma_short"]).mean()
        df["sma_200"] = close.rolling(window=TC["sma_long"]).mean()
        df["price_vs_200dma"] = np.where(close > df["sma_200"], "ABOVE", "BELOW")
        df["dma_cross"] = self._dma_cross(df["sma_50"], df["sma_200"])
        
        # ── Bollinger Bands (20, 2) ──
        bb_mid = close.rolling(window=TC["bb_period"]).mean()
        bb_std = close.rolling(window=TC["bb_period"]).std()
        df["bb_upper"] = bb_mid + (TC["bb_std"] * bb_std)
        df["bb_middle"] = bb_mid
        df["bb_lower"] = bb_mid - (TC["bb_std"] * bb_std)
        df["bb_position"] = self._bb_position(close, df["bb_upper"], df["bb_lower"])
        
        # ── ADX (14) ──
        df["adx"] = self._compute_adx(high, low, close, TC["adx_period"])
        df["adx_trend"] = np.where(
            df["adx"] > TC["adx_trending"], "STRONG_TREND",
            np.where(df["adx"] > 20, "WEAK_TREND", "NO_TREND")
        )
        
        # ── ATR (14) ──
        df["atr"] = self._compute_atr(high, low, close, TC["atr_period"])
        
        # ── OBV ──
        df["obv"] = self._compute_obv(close, volume)
        obv_sma = df["obv"].rolling(window=20).mean()
        df["obv_trend"] = np.where(
            df["obv"] > obv_sma, "RISING",
            np.where(df["obv"] < obv_sma, "FALLING", "FLAT")
        )
        
        # ── Volume Analysis ──
        vol_avg = volume.rolling(window=TC["volume_avg_period"]).mean()
        df["volume_ratio"] = volume / vol_avg
        df["volume_signal"] = np.where(
            df["volume_ratio"] > TC["volume_surge_threshold"], "SURGE",
            np.where(df["volume_ratio"] > 1.3, "HIGH",
            np.where(df["volume_ratio"] < 0.5, "LOW", "NORMAL"))
        )
        
        # ── Stochastic RSI ──
        df["stoch_rsi"] = self._compute_stoch_rsi(close, TC["stoch_rsi_period"])
        
        # ── 52-Week Metrics ──
        if len(df) >= 252:
            df["high_52w"] = high.rolling(window=252).max()
            df["low_52w"] = low.rolling(window=252).min()
        else:
            df["high_52w"] = high.rolling(window=len(df)).max()
            df["low_52w"] = low.rolling(window=len(df)).min()
        
        df["pct_from_52w_high"] = ((close - df["high_52w"]) / df["high_52w"]) * 100
        df["pct_from_52w_low"] = ((close - df["low_52w"]) / df["low_52w"]) * 100
        
        return df
    
    # ── Individual Indicator Computations ──
    
    def _compute_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Compute RSI (Relative Strength Index)."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        # Use exponential moving average after initial SMA
        for i in range(period, len(series)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _compute_macd(self, series, fast, slow, signal):
        """Compute MACD, Signal Line, and Histogram."""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _macd_crossover(self, macd_line, signal_line):
        """Detect MACD crossovers."""
        result = pd.Series("NEUTRAL", index=macd_line.index)
        
        prev_diff = (macd_line - signal_line).shift(1)
        curr_diff = macd_line - signal_line
        
        result[(prev_diff < 0) & (curr_diff > 0)] = "BULLISH"
        result[(prev_diff > 0) & (curr_diff < 0)] = "BEARISH"
        
        return result
    
    def _dma_cross(self, sma_short, sma_long):
        """Detect Golden Cross / Death Cross."""
        result = pd.Series("NONE", index=sma_short.index)
        
        prev_diff = (sma_short - sma_long).shift(1)
        curr_diff = sma_short - sma_long
        
        result[(prev_diff < 0) & (curr_diff > 0)] = "GOLDEN_CROSS"
        result[(prev_diff > 0) & (curr_diff < 0)] = "DEATH_CROSS"
        
        return result
    
    def _bb_position(self, close, upper, lower):
        """Determine position within Bollinger Bands."""
        result = pd.Series("MIDDLE", index=close.index)
        result[close >= upper] = "UPPER"
        result[close <= lower] = "LOWER"
        return result
    
    def _compute_adx(self, high, low, close, period):
        """Compute Average Directional Index."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[(plus_dm < minus_dm)] = 0
        minus_dm[(minus_dm < plus_dm)] = 0
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def _compute_atr(self, high, low, close, period):
        """Compute Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def _compute_obv(self, close, volume):
        """Compute On-Balance Volume."""
        obv = pd.Series(0.0, index=close.index)
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        return obv
    
    def _compute_stoch_rsi(self, close, period):
        """Compute Stochastic RSI."""
        rsi = self._compute_rsi(close, period)
        rsi_min = rsi.rolling(window=period).min()
        rsi_max = rsi.rolling(window=period).max()
        stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
        return stoch_rsi
    
    # ══════════════════════════════════════════════
    # COMPOSITE SCORING
    # ══════════════════════════════════════════════
    
    def compute_composite_score(self, row: pd.Series) -> dict:
        """
        Compute composite score from individual indicators.
        Returns dict with component scores and final composite.
        Score range: -100 (extreme sell) to +100 (extreme buy)
        """
        
        scores = {}
        
        # ── TREND SCORE (30% weight) ──
        trend = 0
        
        # Price vs 200 DMA: +30 above, -30 below
        if row.get("price_vs_200dma") == "ABOVE":
            trend += 30
        else:
            trend -= 30
        
        # Golden Cross / Death Cross: +40 / -40
        if row.get("dma_cross") == "GOLDEN_CROSS":
            trend += 40
        elif row.get("dma_cross") == "DEATH_CROSS":
            trend -= 40
        
        # ADX trending strength
        adx = row.get("adx", 0)
        if adx and not np.isnan(adx):
            if adx > 30:
                # Strong trend — amplify existing direction
                if trend > 0:
                    trend += 20
                else:
                    trend -= 20
            elif adx < 15:
                trend *= 0.5  # Weak trend, dampen signal
        
        trend = max(-100, min(100, trend))
        scores["trend_score"] = trend
        
        # ── MOMENTUM SCORE (30% weight) ──
        momentum = 0
        
        # RSI
        rsi = row.get("rsi_14", 50)
        if rsi and not np.isnan(rsi):
            if rsi < TC["rsi_oversold"]:
                momentum += 40  # Oversold = buy signal
            elif rsi > TC["rsi_overbought"]:
                momentum -= 40  # Overbought = sell signal
            elif rsi < 45:
                momentum += 15
            elif rsi > 55:
                momentum -= 15
        
        # MACD crossover
        macd_cross = row.get("macd_crossover", "NEUTRAL")
        if macd_cross == "BULLISH":
            momentum += 35
        elif macd_cross == "BEARISH":
            momentum -= 35
        
        # Stochastic RSI
        stoch = row.get("stoch_rsi", 50)
        if stoch and not np.isnan(stoch):
            if stoch < TC["stoch_rsi_oversold"]:
                momentum += 25
            elif stoch > TC["stoch_rsi_overbought"]:
                momentum -= 25
        
        momentum = max(-100, min(100, momentum))
        scores["momentum_score"] = momentum
        
        # ── VOLUME SCORE (20% weight) ──
        vol_score = 0
        
        vol_signal = row.get("volume_signal", "NORMAL")
        obv_trend = row.get("obv_trend", "FLAT")
        
        # High volume + rising OBV = strong confirmation
        if vol_signal in ["SURGE", "HIGH"] and obv_trend == "RISING":
            vol_score += 60
        elif vol_signal in ["SURGE", "HIGH"] and obv_trend == "FALLING":
            vol_score -= 40  # Distribution
        elif obv_trend == "RISING":
            vol_score += 25
        elif obv_trend == "FALLING":
            vol_score -= 25
        
        vol_score = max(-100, min(100, vol_score))
        scores["volume_score"] = vol_score
        
        # ── VOLATILITY SCORE (10% weight) ──
        vol_score_v = 0
        
        bb_pos = row.get("bb_position", "MIDDLE")
        if bb_pos == "LOWER":
            vol_score_v += 40  # Near lower band = potential buy
        elif bb_pos == "UPPER":
            vol_score_v -= 40  # Near upper band = potential sell
        
        vol_score_v = max(-100, min(100, vol_score_v))
        scores["volatility_score"] = vol_score_v
        
        # ── RELATIVE STRENGTH SCORE (10% weight) ──
        rs_score = 0
        
        pct_52h = row.get("pct_from_52w_high", 0)
        pct_52l = row.get("pct_from_52w_low", 0)
        
        if pct_52h and not np.isnan(pct_52h):
            if pct_52h > -5:  # Within 5% of 52-week high
                rs_score += 40  # Strong momentum
            elif pct_52h < -30:  # More than 30% from high
                rs_score -= 30  # Significant weakness
        
        if pct_52l and not np.isnan(pct_52l):
            if pct_52l < 5:  # Within 5% of 52-week low
                rs_score -= 20  # Near bottom
        
        rs_score = max(-100, min(100, rs_score))
        scores["relative_strength_score"] = rs_score
        
        # ── COMPOSITE ──
        composite = (
            scores["trend_score"] * TC["weight_trend"] +
            scores["momentum_score"] * TC["weight_momentum"] +
            scores["volume_score"] * TC["weight_volume"] +
            scores["volatility_score"] * TC["weight_volatility"] +
            scores["relative_strength_score"] * TC["weight_relative_strength"]
        )
        
        scores["composite_score"] = round(composite, 1)
        
        # ── SIGNAL ──
        if composite >= SIGNAL_THRESHOLDS["STRONG_BUY"]:
            scores["signal"] = "STRONG_BUY"
        elif composite >= SIGNAL_THRESHOLDS["BUY"]:
            scores["signal"] = "BUY"
        elif composite >= SIGNAL_THRESHOLDS["HOLD_LOWER"]:
            scores["signal"] = "HOLD"
        elif composite >= SIGNAL_THRESHOLDS["SELL"]:
            scores["signal"] = "SELL"
        else:
            scores["signal"] = "STRONG_SELL"
        
        return scores
    
    # ══════════════════════════════════════════════
    # FULL ANALYSIS PIPELINE
    # ══════════════════════════════════════════════
    
    def analyze_instrument(self, symbol: str) -> dict:
        """
        Full technical analysis pipeline for a single instrument.
        Returns the latest day's complete technical snapshot.
        """
        df = self.fetch_price_data(symbol)
        
        if df.empty:
            return {"symbol": symbol, "error": "No data available"}
        
        # Cache the data
        self.cache_price_data(symbol, df)
        
        # Compute indicators
        df = self.compute_all_indicators(df)
        
        # Get latest row
        latest = df.iloc[-1]
        
        # Compute composite score
        scores = self.compute_composite_score(latest)
        
        # Build result
        result = {
            "symbol": symbol,
            "date": str(latest.get("date", "")),
            "close": round(latest.get("close", 0), 2),
            "rsi_14": round(latest.get("rsi_14", 0), 1) if not np.isnan(latest.get("rsi_14", 0)) else None,
            "macd_crossover": latest.get("macd_crossover", "NEUTRAL"),
            "price_vs_200dma": latest.get("price_vs_200dma", ""),
            "dma_cross": latest.get("dma_cross", "NONE"),
            "bb_position": latest.get("bb_position", "MIDDLE"),
            "adx": round(latest.get("adx", 0), 1) if not np.isnan(latest.get("adx", 0)) else None,
            "adx_trend": latest.get("adx_trend", ""),
            "obv_trend": latest.get("obv_trend", "FLAT"),
            "volume_signal": latest.get("volume_signal", "NORMAL"),
            "volume_ratio": round(latest.get("volume_ratio", 1), 2) if not np.isnan(latest.get("volume_ratio", 1)) else None,
            "stoch_rsi": round(latest.get("stoch_rsi", 0), 1) if not np.isnan(latest.get("stoch_rsi", 0)) else None,
            "pct_from_52w_high": round(latest.get("pct_from_52w_high", 0), 1) if not np.isnan(latest.get("pct_from_52w_high", 0)) else None,
            "pct_from_52w_low": round(latest.get("pct_from_52w_low", 0), 1) if not np.isnan(latest.get("pct_from_52w_low", 0)) else None,
            **scores,
        }
        
        return result
    
    def analyze_sector_indices(self) -> list:
        """Analyze all Nifty sector indices for relative strength."""
        
        results = []
        nifty_data = self.fetch_price_data("^NSEI")  # Nifty 50 benchmark
        
        if nifty_data.empty:
            return results
        
        nifty_returns = {
            "1w": self._period_return(nifty_data, 5),
            "1m": self._period_return(nifty_data, 22),
            "3m": self._period_return(nifty_data, 66),
        }
        
        for sector, symbol in SECTOR_INDICES.items():
            if sector == "NIFTY_50":
                continue
            
            try:
                df = self.fetch_price_data(symbol)
                if df.empty:
                    continue
                
                sector_returns = {
                    "1w": self._period_return(df, 5),
                    "1m": self._period_return(df, 22),
                    "3m": self._period_return(df, 66),
                }
                
                # Relative strength = sector return - nifty return
                rs = {
                    "rs_1w": round(sector_returns["1w"] - nifty_returns["1w"], 2),
                    "rs_1m": round(sector_returns["1m"] - nifty_returns["1m"], 2),
                    "rs_3m": round(sector_returns["3m"] - nifty_returns["3m"], 2),
                }
                
                # Get sector technical analysis
                df = self.compute_all_indicators(df)
                latest = df.iloc[-1]
                scores = self.compute_composite_score(latest)
                
                results.append({
                    "sector": sector.replace("NIFTY_", ""),
                    "symbol": symbol,
                    **rs,
                    "rsi": round(latest.get("rsi_14", 0), 1) if not np.isnan(latest.get("rsi_14", 0)) else None,
                    "trend": latest.get("price_vs_200dma", ""),
                    **scores,
                })
                
            except Exception as e:
                print(f"  ⚠️ {sector}: {e}")
        
        # Sort by composite score
        results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
        return results
    
    def _period_return(self, df: pd.DataFrame, periods: int) -> float:
        """Calculate return over N periods."""
        if len(df) < periods + 1:
            return 0.0
        current = df["close"].iloc[-1]
        past = df["close"].iloc[-periods - 1]
        return ((current - past) / past) * 100
    
    def save_signals(self, analysis: dict):
        """Save technical signals to database."""
        session = get_session(self.engine)
        
        try:
            signal = TechnicalSignal(
                symbol=analysis.get("symbol", ""),
                date=date.today(),
                rsi_14=analysis.get("rsi_14"),
                macd_line=analysis.get("macd_line"),
                macd_signal_line=analysis.get("macd_signal_line"),
                macd_histogram=analysis.get("macd_histogram"),
                macd_crossover=analysis.get("macd_crossover"),
                sma_50=analysis.get("sma_50"),
                sma_200=analysis.get("sma_200"),
                price_vs_200dma=analysis.get("price_vs_200dma"),
                dma_cross=analysis.get("dma_cross"),
                bb_upper=analysis.get("bb_upper"),
                bb_middle=analysis.get("bb_middle"),
                bb_lower=analysis.get("bb_lower"),
                bb_position=analysis.get("bb_position"),
                adx=analysis.get("adx"),
                adx_trend=analysis.get("adx_trend"),
                atr=analysis.get("atr"),
                obv=analysis.get("obv"),
                obv_trend=analysis.get("obv_trend"),
                volume_ratio=analysis.get("volume_ratio"),
                volume_signal=analysis.get("volume_signal"),
                stoch_rsi=analysis.get("stoch_rsi"),
                high_52w=analysis.get("high_52w"),
                low_52w=analysis.get("low_52w"),
                pct_from_52w_high=analysis.get("pct_from_52w_high"),
                pct_from_52w_low=analysis.get("pct_from_52w_low"),
                trend_score=analysis.get("trend_score"),
                momentum_score=analysis.get("momentum_score"),
                volume_score=analysis.get("volume_score"),
                volatility_score=analysis.get("volatility_score"),
                relative_strength_score=analysis.get("relative_strength_score"),
                composite_score=analysis.get("composite_score"),
                signal=analysis.get("signal"),
            )
            session.add(signal)
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()


# ══════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════

def test_technical_agent():
    """Test technical analysis on a few instruments."""
    
    print("═" * 60)
    print("  TECHNICAL SIGNALS AGENT — TEST MODE")
    print("═" * 60)
    
    agent = TechnicalSignalsAgent()
    
    # Test with some major stocks
    test_symbols = [
        ("RELIANCE.NS", "Reliance Industries"),
        ("HDFCBANK.NS", "HDFC Bank"),
        ("TCS.NS", "TCS"),
        ("SUNPHARMA.NS", "Sun Pharma"),
    ]
    
    for symbol, name in test_symbols:
        print(f"\n{'─' * 50}")
        print(f"📊 {name} ({symbol})")
        print(f"{'─' * 50}")
        
        result = agent.analyze_instrument(symbol)
        
        if "error" in result:
            print(f"  ❌ {result['error']}")
            continue
        
        print(f"  Close:          ₹{result.get('close', 'N/A')}")
        print(f"  RSI(14):        {result.get('rsi_14', 'N/A')}")
        print(f"  MACD:           {result.get('macd_crossover', 'N/A')}")
        print(f"  vs 200 DMA:     {result.get('price_vs_200dma', 'N/A')}")
        print(f"  DMA Cross:      {result.get('dma_cross', 'N/A')}")
        print(f"  Bollinger:      {result.get('bb_position', 'N/A')}")
        print(f"  ADX:            {result.get('adx', 'N/A')} ({result.get('adx_trend', 'N/A')})")
        print(f"  OBV Trend:      {result.get('obv_trend', 'N/A')}")
        print(f"  Volume:         {result.get('volume_signal', 'N/A')} ({result.get('volume_ratio', 'N/A')}x avg)")
        print(f"  From 52W High:  {result.get('pct_from_52w_high', 'N/A')}%")
        print(f"  ────────────────────────────────")
        print(f"  Trend Score:    {result.get('trend_score', 'N/A')}")
        print(f"  Momentum Score: {result.get('momentum_score', 'N/A')}")
        print(f"  Volume Score:   {result.get('volume_score', 'N/A')}")
        print(f"  COMPOSITE:      {result.get('composite_score', 'N/A')}")
        print(f"  ═══ SIGNAL:     {result.get('signal', 'N/A')} ═══")
    
    # Test sector analysis
    print(f"\n\n{'═' * 60}")
    print("📊 SECTOR RELATIVE STRENGTH")
    print(f"{'═' * 60}")
    
    sectors = agent.analyze_sector_indices()
    for s in sectors:
        print(f"  {s['sector']:<15} RS(1m): {s.get('rs_1m', 'N/A'):>6}%  "
              f"RSI: {s.get('rsi', 'N/A'):>5}  "
              f"Score: {s.get('composite_score', 'N/A'):>6}  "
              f"Signal: {s.get('signal', 'N/A')}")


if __name__ == "__main__":
    test_technical_agent()
