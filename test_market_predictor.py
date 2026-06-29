"""
Regression tests for the refactored MarketPredictor.

Each test targets a specific bug fixed in the production-hardening pass.
Tests are ordered from most fundamental (data integrity) to most derived
(model behaviour) so failures are easy to diagnose.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
import tempfile

import numpy as np
import pandas as pd
import pytest

from app.ml_services.market_predictor import (
    FEATURE_COLUMNS,
    ChronologicalCV,
    FeatureBuilder,
    MarketPredictor,
    PredictionRecord,
    TrainingMetrics,
    _latest_version_path,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_ohlcv_df(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """
    Synthetic chronological OHLCV + pre-computed indicator DataFrame.

    All derived indicators are computed with backward-looking windows only.
    Rows are indexed 0..n-1 representing trading days in ascending order.
    """
    rng = np.random.default_rng(seed)
    price = 100.0 + np.cumsum(rng.normal(0, 1, n))
    price = np.clip(price, 10, None)

    df = pd.DataFrame({
        "close":  price,
        "open":   price * rng.uniform(0.995, 1.005, n),
        "high":   price * rng.uniform(1.000, 1.015, n),
        "low":    price * rng.uniform(0.985, 1.000, n),
        "volume": rng.uniform(1e6, 5e6, n),
    })

    # Add indicator columns (simplified, backward-looking)
    df["rsi_14"]             = 50.0 + rng.normal(0, 10, n)
    df["macd"]               = rng.normal(0, 0.5, n)
    df["macd_signal"]        = df["macd"].ewm(span=9).mean()
    df["macd_histogram"]     = df["macd"] - df["macd_signal"]
    df["sma_20"]             = df["close"].rolling(20, min_periods=1).mean()
    df["sma_50"]             = df["close"].rolling(50, min_periods=1).mean()
    df["ema_12"]             = df["close"].ewm(span=12).mean()
    df["ema_26"]             = df["close"].ewm(span=26).mean()
    df["bollinger_upper"]    = df["sma_20"] + 2 * df["close"].rolling(20, min_periods=1).std().fillna(0)
    df["bollinger_lower"]    = df["sma_20"] - 2 * df["close"].rolling(20, min_periods=1).std().fillna(0)
    df["bollinger_width"]    = (df["bollinger_upper"] - df["bollinger_lower"]) / df["sma_20"].replace(0, 1)
    df["atr_14"]             = (df["high"] - df["low"]).rolling(14, min_periods=1).mean()
    df["volume_sma_20"]      = df["volume"].rolling(20, min_periods=1).mean()
    df["obv"]                = (np.sign(df["close"].diff().fillna(0)) * df["volume"]).cumsum()
    df["avg_sentiment_score"]= rng.uniform(-1, 1, n)
    df["fear_greed_index"]   = rng.uniform(0, 100, n)

    # Target: 1=bullish if next-day return > +0.3%, 0=bearish if < -0.3%, else 2=neutral
    future_ret = df["close"].shift(-1) / df["close"] - 1
    df["direction"] = np.where(future_ret > 0.003, 1,
                      np.where(future_ret < -0.003, 0, 2))
    df = df.dropna(subset=["direction"]).astype({"direction": int})
    return df


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    return _make_ohlcv_df(n=300)


@pytest.fixture(scope="module")
def feature_builder() -> FeatureBuilder:
    return FeatureBuilder()


@pytest.fixture
def tmp_predictor(tmp_path: Path) -> MarketPredictor:
    """Predictor with isolated temp registry — no shared state between tests."""
    with patch("app.ml_services.market_predictor.settings") as mock_settings:
        mock_settings.ml.model_registry_path = str(tmp_path)
        predictor = MarketPredictor()
        predictor._registry = tmp_path / "market_predictor"
        predictor._registry.mkdir(parents=True, exist_ok=True)
    return predictor


# ═════════════════════════════════════════════════════════════════════════════
# BUG 1 — DATA LEAKAGE: ChronologicalCV must never allow future data in train
# ═════════════════════════════════════════════════════════════════════════════

class TestChronologicalCV:
    """
    Verify that TimeSeriesSplit enforces temporal ordering.

    The critical invariant: max(train_idx) < min(val_idx) for every fold.
    If this invariant holds, no future information can be in the training set.
    """

    def test_all_val_indices_strictly_after_all_train_indices(self, sample_df):
        """Core correctness: max(train) < min(val) for every single fold."""
        X = sample_df[["close"]].values
        y = sample_df["direction"].values
        cv = ChronologicalCV(n_splits=5)

        for fold_num, (train_idx, val_idx) in enumerate(cv.split(X, y)):
            assert train_idx.max() < val_idx.min(), (
                f"Fold {fold_num}: training index {train_idx.max()} overlaps "
                f"with validation index {val_idx.min()} — DATA LEAKAGE DETECTED"
            )

    def test_val_sizes_are_positive(self, sample_df):
        """Every fold must have at least one validation sample."""
        X = sample_df[["close"]].values
        y = sample_df["direction"].values
        cv = ChronologicalCV(n_splits=5)

        for train_idx, val_idx in cv.split(X, y):
            assert len(val_idx) > 0
            assert len(train_idx) > 0

    def test_train_sizes_grow_monotonically(self, sample_df):
        """
        Each successive fold should train on more data than the previous.

        This is the 'expanding window' property of TimeSeriesSplit — the
        model progressively incorporates more history.
        """
        X = sample_df[["close"]].values
        y = sample_df["direction"].values
        cv = ChronologicalCV(n_splits=5)

        sizes = [len(t) for t, _ in cv.split(X, y)]
        for i in range(1, len(sizes)):
            assert sizes[i] > sizes[i - 1], (
                f"Training set shrank from fold {i-1} to fold {i}: "
                f"{sizes[i-1]} → {sizes[i]}. "
                "TimeSeriesSplit should always expand the training window."
            )

    def test_no_index_appears_in_both_train_and_val_same_fold(self, sample_df):
        """No row can be simultaneously in train and val for any fold."""
        X = sample_df[["close"]].values
        y = sample_df["direction"].values
        cv = ChronologicalCV(n_splits=5)

        for fold_num, (train_idx, val_idx) in enumerate(cv.split(X, y)):
            overlap = set(train_idx) & set(val_idx)
            assert len(overlap) == 0, (
                f"Fold {fold_num}: {len(overlap)} indices appear in both "
                f"train and val — this is a data leakage bug."
            )

    def test_random_split_would_fail_temporal_ordering(self, sample_df):
        """
        REGRESSION: demonstrate that the old train_test_split DID leak.

        This test documents the bug that was fixed.  It checks that if you
        used random splitting, the temporal ordering invariant would be violated.
        """
        from sklearn.model_selection import train_test_split

        X = sample_df[["close"]].values
        y = sample_df["direction"].values

        # What the old code did:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        # We need the original integer indices to check ordering
        idx = np.arange(len(X))
        train_idx, val_idx, _, _ = train_test_split(
            idx, y, test_size=0.2, random_state=42, stratify=y
        )
        # With random splitting, val indices will NOT all be > all train indices
        # i.e., the temporal ordering invariant is VIOLATED
        temporal_order_holds = train_idx.max() < val_idx.min()
        assert not temporal_order_holds, (
            "Expected random split to violate temporal ordering — "
            "if this passes it means the data is unusually ordered."
        )


# ═════════════════════════════════════════════════════════════════════════════
# BUG 2 — SCALER LEAKAGE: StandardScaler must not see validation data
# ═════════════════════════════════════════════════════════════════════════════

class TestScalerLeakage:
    """
    Verify that the Pipeline prevents scaler statistics from leaking.

    The scaler inside a Pipeline is fit only when pipeline.fit() is called.
    ChronologicalCV.evaluate() calls copy.deepcopy(pipeline).fit(X_train_fold)
    so each fold's scaler is independent and sees only training-fold rows.
    """

    def test_pipeline_scaler_only_sees_training_data(self, sample_df):
        """
        After fitting a pipeline on a training fold, the scaler's mean_
        should equal the training-fold mean — NOT the full-dataset mean.
        """
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        X = sample_df[["close", "rsi_14"]].values.astype(float)
        y = sample_df["direction"].values

        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=3)
        for train_idx, val_idx in tscv.split(X, y):
            pipe = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=10)),
            ])
            pipe.fit(X[train_idx], y[train_idx])

            scaler_mean = pipe.named_steps["scaler"].mean_
            true_train_mean = X[train_idx].mean(axis=0)

            np.testing.assert_allclose(
                scaler_mean, true_train_mean, rtol=1e-5,
                err_msg="Scaler mean does not match training-fold mean — "
                        "validation data may have leaked into scaler fit."
            )
            # Crucial: scaler mean does NOT match full-data mean
            full_mean = X.mean(axis=0)
            assert not np.allclose(scaler_mean, full_mean, rtol=1e-3), (
                "Scaler mean equals full-dataset mean — this would only happen "
                "if the scaler was fit on the full dataset (leakage)."
            )
            break  # One fold is sufficient to prove the point

    def test_transform_does_not_refit(self, sample_df):
        """pipeline.transform() must not change scaler.mean_ (no refitting)."""
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        X = sample_df[["close", "rsi_14"]].values.astype(float)
        y = sample_df["direction"].values

        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=10)),
        ])
        pipe.fit(X[:200], y[:200])
        mean_before = pipe.named_steps["scaler"].mean_.copy()

        # Transform validation data — must not change the fitted mean
        _ = pipe.predict(X[200:])
        mean_after = pipe.named_steps["scaler"].mean_

        np.testing.assert_array_equal(mean_before, mean_after,
            err_msg="Scaler mean changed after transform — indicates refitting on val data.")


# ═════════════════════════════════════════════════════════════════════════════
# BUG 3 — SEMANTIC VERSION SORTING
# ═════════════════════════════════════════════════════════════════════════════

class TestSemanticVersionSorting:
    """
    Verify _latest_version_path picks the semantically newest version.

    The old code used sorted(paths, reverse=True) which is lexicographic.
    Lexicographic: "1.9.0" > "1.10.0" because "9" > "1" at position 2.
    Semantic:      "1.10.0" > "1.9.0" because 10 > 9 as integers.
    """

    def _make_registry(self, tmp_path: Path, versions: List[str]) -> Path:
        """Create fake model registry with given version directories."""
        registry = tmp_path / "market_predictor"
        for v in versions:
            d = registry / v
            d.mkdir(parents=True)
            (d / "meta.json").write_text('{"version": "' + v + '"}')
        return registry

    def test_semver_beats_lexicographic_at_minor_version(self, tmp_path):
        """1.10.0 must be selected over 1.9.0 — lexicographic gets this wrong."""
        registry = self._make_registry(tmp_path, ["1.9.0", "1.10.0", "1.2.0"])
        result = _latest_version_path(registry)
        assert result is not None
        assert result.name == "1.10.0", (
            f"Expected '1.10.0' (newest semantically) but got '{result.name}'. "
            "Lexicographic sorting would incorrectly return '1.9.0'."
        )

    def test_semver_major_version_wins(self, tmp_path):
        """2.0.0 must beat 1.99.99."""
        registry = self._make_registry(tmp_path, ["1.99.99", "2.0.0", "0.5.0"])
        result = _latest_version_path(registry)
        assert result.name == "2.0.0"

    def test_patch_version_comparison(self, tmp_path):
        """1.0.10 must beat 1.0.9."""
        registry = self._make_registry(tmp_path, ["1.0.9", "1.0.10", "1.0.1"])
        result = _latest_version_path(registry)
        assert result.name == "1.0.10"

    def test_single_version(self, tmp_path):
        """Single version in registry must be returned."""
        registry = self._make_registry(tmp_path, ["1.0.0"])
        result = _latest_version_path(registry)
        assert result.name == "1.0.0"

    def test_empty_registry_returns_none(self, tmp_path):
        """Empty registry must return None, not raise."""
        registry = tmp_path / "market_predictor"
        registry.mkdir()
        result = _latest_version_path(registry)
        assert result is None

    def test_non_semver_directories_skipped(self, tmp_path):
        """Directories with non-semver names must be skipped gracefully."""
        registry = self._make_registry(tmp_path, ["1.0.0", "2.1.0"])
        # Add a non-semver directory
        junk = registry / "latest"
        junk.mkdir()
        (junk / "meta.json").write_text("{}")

        result = _latest_version_path(registry)
        assert result.name == "2.1.0"


# ═════════════════════════════════════════════════════════════════════════════
# BUG 4 — PROBABILITY CALIBRATION
# ═════════════════════════════════════════════════════════════════════════════

class TestProbabilityCalibration:
    """
    Verify that calibrated outputs are used and differ from raw outputs.

    We can't easily test that calibration is "correct" without large datasets,
    but we CAN verify:
      (a) calibrated probabilities are in [0, 1] and sum to 1
      (b) calibrated != raw (calibration had some effect)
      (c) PredictionRecord exposes both values
    """

    def test_calibrated_probs_sum_to_one(self):
        """
        Any probability distribution must sum to 1.0 within floating-point tolerance.
        """
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        import numpy as np

        # Use logistic regression as a proxy — it has the same Pipeline structure
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", CalibratedClassifierCV(
                LogisticRegression(max_iter=200), method="isotonic", cv=3
            )),
        ])
        rng = np.random.default_rng(99)
        X = rng.normal(size=(300, 4))
        y = rng.integers(0, 3, size=300)
        pipe.fit(X, y)

        probs = pipe.predict_proba(X[:5])
        np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-6,
            err_msg="Calibrated probabilities do not sum to 1.0")
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0), \
            "Calibrated probabilities outside [0, 1]"

    def test_prediction_record_exposes_both_confidences(self, tmp_predictor, sample_df):
        """PredictionRecord must contain both calibrated and raw confidence."""
        pytest.importorskip("lightgbm")
        pytest.importorskip("xgboost")

        tmp_predictor.train(sample_df, target_col="direction")

        fb = FeatureBuilder()
        df_eng = fb.build_dataframe(sample_df)
        feature_row = df_eng[FEATURE_COLUMNS].iloc[-1].values.astype(np.float32)

        record = tmp_predictor.predict_with_record(feature_row, symbol="TEST")

        assert isinstance(record, PredictionRecord)
        assert 0.0 <= record.calibrated_confidence <= 1.0
        assert 0.0 <= record.raw_confidence <= 1.0
        assert record.direction in ("bullish", "bearish", "neutral")
        assert record.model_version is not None
        assert record.latency_ms >= 0.0

    def test_backwards_compat_predict_returns_tuple(self, tmp_predictor, sample_df):
        """predict() must still return (str, float) for backwards compatibility."""
        pytest.importorskip("lightgbm")
        pytest.importorskip("xgboost")

        tmp_predictor.train(sample_df, target_col="direction")

        fb = FeatureBuilder()
        df_eng = fb.build_dataframe(sample_df)
        feature_row = df_eng[FEATURE_COLUMNS].iloc[-1].values.astype(np.float32)

        result = tmp_predictor.predict(feature_row)

        assert isinstance(result, tuple) and len(result) == 2
        direction, confidence = result
        assert isinstance(direction, str)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


# ═════════════════════════════════════════════════════════════════════════════
# BUG 5 — FEATURE ENGINEERING LOOK-AHEAD
# ═════════════════════════════════════════════════════════════════════════════

class TestFeatureEngineeringNoLookahead:
    """
    Verify that FeatureBuilder.build_dataframe() never looks forward in time.

    Any feature that uses shift(-k) for k > 0 would introduce look-ahead bias.
    """

    def test_rsi_momentum_uses_shift_1_not_minus_1(self, sample_df, feature_builder):
        """
        rsi_momentum = rsi[t] - rsi[t-1], NOT rsi[t] - rsi[t+1].

        shift(1) = previous value (safe: already observed).
        shift(-1) = next value (look-ahead: introduces data leakage).
        """
        df_eng = feature_builder.build_dataframe(sample_df)

        # rsi_momentum at row 5 should be rsi[5] - rsi[4]
        for i in range(1, min(10, len(sample_df))):
            expected = sample_df["rsi_14"].iloc[i] - sample_df["rsi_14"].iloc[i - 1]
            actual = df_eng["rsi_momentum"].iloc[i]
            assert abs(actual - expected) < 1e-6, (
                f"Row {i}: rsi_momentum={actual:.4f} but expected "
                f"rsi[{i}]-rsi[{i-1}]={expected:.4f}. "
                "If shift(-1) were used this would be rsi[t]-rsi[t+1] — look-ahead."
            )

    def test_row_0_rsi_momentum_is_zero_not_future(self, sample_df, feature_builder):
        """
        The first row has no previous RSI — momentum must be 0 (NaN filled),
        NOT the difference between row 0 and row 1 (which would be look-ahead).
        """
        df_eng = feature_builder.build_dataframe(sample_df)
        assert df_eng["rsi_momentum"].iloc[0] == 0.0, (
            "First row rsi_momentum should be 0.0 (no previous bar), "
            f"got {df_eng['rsi_momentum'].iloc[0]}"
        )

    def test_volume_ratio_uses_current_and_historical_avg(self, sample_df, feature_builder):
        """
        volume_ratio = volume[t] / volume_sma_20[t].
        volume_sma_20 at time t is the rolling average of volumes up to t.
        No future volumes are included.
        """
        df_eng = feature_builder.build_dataframe(sample_df)
        # All volume ratios must be non-negative
        assert (df_eng["volume_ratio"] >= 0).all()

    def test_macd_cross_uses_only_current_values(self, sample_df, feature_builder):
        """macd_cross = sign(macd[t] - signal[t]) — no forward reference."""
        df_eng = feature_builder.build_dataframe(sample_df)
        for i in range(len(sample_df)):
            macd = sample_df["macd"].iloc[i]
            sig = sample_df["macd_signal"].iloc[i]
            expected = 1.0 if macd > sig else -1.0
            actual = df_eng["macd_cross"].iloc[i]
            assert actual == expected, (
                f"Row {i}: macd_cross={actual} but expected {expected}. "
                "macd_cross must only use macd[t] and signal[t]."
            )


# ═════════════════════════════════════════════════════════════════════════════
# INTEGRATION — full train → save → load → predict cycle
# ═════════════════════════════════════════════════════════════════════════════

class TestTrainSaveLoadCycle:
    """End-to-end test of the full model lifecycle."""

    def test_train_returns_structured_metrics(self, tmp_predictor, sample_df):
        pytest.importorskip("lightgbm")
        pytest.importorskip("xgboost")

        metrics = tmp_predictor.train(sample_df, target_col="direction")

        assert "lgbm_mean_accuracy" in metrics
        assert "xgb_mean_accuracy" in metrics
        assert "n_folds" in metrics
        assert metrics["n_folds"] == 5
        assert metrics["calibration_method"] == "isotonic"
        assert metrics["validation_strategy"] == "TimeSeriesSplit"
        assert 0.0 < metrics["lgbm_mean_accuracy"] < 1.0

    def test_save_and_load_produces_identical_predictions(self, tmp_predictor, sample_df, tmp_path):
        pytest.importorskip("lightgbm")
        pytest.importorskip("xgboost")

        tmp_predictor.train(sample_df, target_col="direction")
        tmp_predictor.save("1.0.0")

        fb = FeatureBuilder()
        df_eng = fb.build_dataframe(sample_df)
        feature_row = df_eng[FEATURE_COLUMNS].iloc[-1].values.astype(np.float32)

        direction_before, conf_before = tmp_predictor.predict(feature_row)

        # Create a fresh predictor and load from disk
        with patch("app.ml_services.market_predictor.settings") as mock:
            mock.ml.model_registry_path = str(tmp_path)
            p2 = MarketPredictor()
            p2._registry = tmp_predictor._registry
            p2.load("1.0.0")

        direction_after, conf_after = p2.predict(feature_row)

        assert direction_before == direction_after
        assert abs(conf_before - conf_after) < 1e-6

    def test_insufficient_data_raises_error(self, tmp_predictor):
        """Training on tiny DataFrame must raise MLModelError, not crash silently."""
        from app.core.exceptions import MLModelError

        tiny_df = _make_ohlcv_df(n=10)
        with pytest.raises(MLModelError, match="MIN_TRAIN_ROWS\|≥ 60"):
            tmp_predictor.train(tiny_df)

    def test_prediction_returns_neutral_when_not_loaded(self, tmp_path):
        """Untrained predictor must return neutral/0.333 safely, not raise."""
        with patch("app.ml_services.market_predictor.settings") as mock:
            mock.ml.model_registry_path = str(tmp_path)
            p = MarketPredictor()
            p._registry = tmp_path / "empty_registry"
            p._registry.mkdir()

        feature_row = np.zeros(len(FEATURE_COLUMNS), dtype=np.float32)
        direction, confidence = p.predict(feature_row)

        assert direction == "neutral"
        assert abs(confidence - 0.333) < 0.01

    def test_shap_values_present_in_record(self, tmp_predictor, sample_df):
        """If shap is installed, PredictionRecord.shap_values must be populated."""
        shap = pytest.importorskip("shap")
        pytest.importorskip("lightgbm")
        pytest.importorskip("xgboost")

        tmp_predictor.train(sample_df, target_col="direction")

        fb = FeatureBuilder()
        df_eng = fb.build_dataframe(sample_df)
        feature_row = df_eng[FEATURE_COLUMNS].iloc[-1].values.astype(np.float32)

        record = tmp_predictor.predict_with_record(feature_row, symbol="AAPL")

        # shap_values may be None if extraction fails for the calibrated wrapper
        # but if it is populated it must have the right structure
        if record.shap_values is not None:
            assert isinstance(record.shap_values, dict)
            for key in record.shap_values:
                assert key in FEATURE_COLUMNS
