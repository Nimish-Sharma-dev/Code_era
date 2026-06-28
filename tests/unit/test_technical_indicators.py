"""Unit tests for the technical indicator computation engine."""

import pytest
import pandas as pd
import numpy as np
from app.ml_services.technical_indicators import TechnicalIndicatorEngine


@pytest.fixture
def engine():
    return TechnicalIndicatorEngine()


@pytest.fixture
def sample_df():
    """50 days of mock OHLCV data."""
    np.random.seed(42)
    n = 50
    prices = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        "open":   prices * (1 - 0.005),
        "high":   prices * (1 + 0.01),
        "low":    prices * (1 - 0.01),
        "close":  prices,
        "volume": np.random.uniform(1e6, 5e6, n),
    })


def test_rsi_bounded(engine, sample_df):
    rsi = engine.compute_rsi(sample_df["close"])
    assert 0 <= rsi <= 100


def test_rsi_insufficient_data(engine):
    short_series = pd.Series([100, 101, 99])
    rsi = engine.compute_rsi(short_series)
    assert rsi == 50.0  # Default neutral


def test_macd_returns_three_values(engine, sample_df):
    result = engine.compute_macd(sample_df["close"])
    assert set(result.keys()) == {"macd", "signal", "histogram"}
    assert isinstance(result["macd"], float)


def test_bollinger_bands_ordering(engine, sample_df):
    result = engine.compute_bollinger_bands(sample_df["close"])
    assert result["upper"] >= result["middle"] >= result["lower"]


def test_sma_correct_window(engine, sample_df):
    sma = engine.compute_sma(sample_df["close"], 20)
    expected = float(sample_df["close"].rolling(20).mean().iloc[-1])
    assert abs(sma - expected) < 0.001


def test_compute_all_returns_expected_keys(engine, sample_df):
    result = engine.compute_all(sample_df)
    required = ["rsi_14", "macd", "sma_20", "bollinger_upper", "atr_14", "obv"]
    for key in required:
        assert key in result, f"Missing key: {key}"


def test_obv_is_float(engine, sample_df):
    obv = engine.compute_obv(sample_df["close"], sample_df["volume"])
    assert isinstance(obv, float)
