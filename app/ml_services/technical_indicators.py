"""
Technical indicator computation service.

Computes RSI, MACD, Bollinger Bands, SMA/EMA, ATR, OBV from OHLCV data.
All computations use numpy/pandas for speed — no TA-Lib dependency.
Results are stored in PostgreSQL and used as ML features.
"""

from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


class TechnicalIndicatorEngine:
    """
    Pure-Python technical analysis engine.

    All methods accept pandas Series or numpy arrays and return floats.
    Stateless — instantiate once and reuse across symbols.
    """

    @staticmethod
    def compute_rsi(closes: pd.Series, period: int = 14) -> float:
        """
        Relative Strength Index (RSI).
        Overbought >70, Oversold <30.
        """
        if len(closes) < period + 1:
            return 50.0
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.iloc[-1] != rsi.iloc[-1] else 50.0

    @staticmethod
    def compute_macd(
        closes: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict:
        """
        MACD = EMA(fast) - EMA(slow).
        Returns macd_line, signal_line, histogram.
        """
        ema_fast = closes.ewm(span=fast, adjust=False).mean()
        ema_slow = closes.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
        }

    @staticmethod
    def compute_sma(closes: pd.Series, period: int) -> Optional[float]:
        """Simple Moving Average."""
        if len(closes) < period:
            return None
        return float(closes.rolling(period).mean().iloc[-1])

    @staticmethod
    def compute_ema(closes: pd.Series, period: int) -> float:
        """Exponential Moving Average."""
        return float(closes.ewm(span=period, adjust=False).mean().iloc[-1])

    @staticmethod
    def compute_bollinger_bands(
        closes: pd.Series, period: int = 20, num_std: float = 2.0
    ) -> dict:
        """Bollinger Bands: middle ± num_std * rolling_std."""
        if len(closes) < period:
            last = float(closes.iloc[-1])
            return {"upper": last, "middle": last, "lower": last, "width": 0.0}
        sma = closes.rolling(period).mean()
        std = closes.rolling(period).std()
        upper = sma + num_std * std
        lower = sma - num_std * std
        width = float((upper - lower).iloc[-1] / sma.iloc[-1]) if sma.iloc[-1] else 0.0
        return {
            "upper": float(upper.iloc[-1]),
            "middle": float(sma.iloc[-1]),
            "lower": float(lower.iloc[-1]),
            "width": width,
        }

    @staticmethod
    def compute_atr(
        highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14
    ) -> float:
        """Average True Range — measures volatility."""
        high_low = highs - lows
        high_close = (highs - closes.shift()).abs()
        low_close = (lows - closes.shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    @staticmethod
    def compute_obv(closes: pd.Series, volumes: pd.Series) -> float:
        """On-Balance Volume — cumulative volume signal."""
        direction = np.sign(closes.diff().fillna(0))
        obv = (direction * volumes).cumsum()
        return float(obv.iloc[-1])

    @staticmethod
    def compute_stochastic(
        highs: pd.Series,
        lows: pd.Series,
        closes: pd.Series,
        k_period: int = 14,
        d_period: int = 3,
    ) -> dict:
        """Stochastic Oscillator %K and %D."""
        lowest_low = lows.rolling(k_period).min()
        highest_high = highs.rolling(k_period).max()
        denom = highest_high - lowest_low
        k = 100 * (closes - lowest_low) / denom.replace(0, np.nan)
        d = k.rolling(d_period).mean()
        return {"k": float(k.iloc[-1]) if not pd.isna(k.iloc[-1]) else 50.0,
                "d": float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else 50.0}

    def compute_all(
        self,
        df: pd.DataFrame,
        avg_sentiment: float = 0.0,
        fear_greed: float = 50.0,
    ) -> dict:
        """
        Compute the full indicator set from an OHLCV DataFrame.

        DataFrame must have columns: open, high, low, close, volume.
        Returns a flat dict ready for DB insertion or ML feature extraction.
        """
        closes = df["close"]
        highs = df["high"]
        lows = df["low"]
        volumes = df["volume"]

        macd = self.compute_macd(closes)
        bb = self.compute_bollinger_bands(closes)
        stoch = self.compute_stochastic(highs, lows, closes)

        return {
            # Trend
            "sma_20": self.compute_sma(closes, 20),
            "sma_50": self.compute_sma(closes, 50),
            "sma_200": self.compute_sma(closes, 200),
            "ema_12": self.compute_ema(closes, 12),
            "ema_26": self.compute_ema(closes, 26),
            # Momentum
            "rsi_14": self.compute_rsi(closes),
            "macd": macd["macd"],
            "macd_signal": macd["signal"],
            "macd_histogram": macd["histogram"],
            "stoch_k": stoch["k"],
            "stoch_d": stoch["d"],
            # Volatility
            "atr_14": self.compute_atr(highs, lows, closes),
            "bollinger_upper": bb["upper"],
            "bollinger_lower": bb["lower"],
            "bollinger_width": bb["width"],
            # Volume
            "volume_sma_20": self.compute_sma(volumes, 20),
            "obv": self.compute_obv(closes, volumes),
            # Context
            "avg_sentiment_score": avg_sentiment,
            "fear_greed_index": fear_greed,
        }
