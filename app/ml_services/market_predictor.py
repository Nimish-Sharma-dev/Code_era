"""
Market direction prediction engine using LightGBM / XGBoost ensemble.

Pipeline:
  1. Fetch historical OHLCV + technical indicators from PostgreSQL.
  2. Build feature matrix including sentiment, macro signals.
  3. Train / load LightGBM and XGBoost models.
  4. Ensemble via soft voting weighted by validation accuracy.
  5. Store prediction + confidence in PostgreSQL and Neo4j.

Model versioning: each trained model is saved to MODEL_REGISTRY_PATH
with a semver tag. The active model version is tracked in Redis.
"""

from __future__ import annotations

import asyncio
import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.core.exceptions import MLModelError
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class FeatureBuilder:
    """
    Constructs the feature matrix for price direction prediction.

    Feature engineering is the single biggest lever for model performance.
    We use a mix of technical, sentiment, and derived features.
    """

    FEATURE_COLUMNS = [
        "rsi_14", "macd", "macd_signal", "macd_histogram",
        "sma_20", "sma_50", "ema_12", "ema_26",
        "bollinger_upper", "bollinger_lower", "bollinger_width",
        "atr_14", "volume_sma_20", "obv",
        "avg_sentiment_score", "fear_greed_index",
        # Derived
        "price_vs_sma20", "price_vs_sma50",
        "rsi_momentum", "volume_ratio",
        "macd_cross",  # 1 if macd > signal else -1
        "bb_position",  # Price position within bands [0,1]
    ]

    def build(self, indicators: dict, latest_close: float, prev_indicators: Optional[dict] = None) -> np.ndarray:
        """
        Build a 1D feature vector from indicators dict.

        Args:
            indicators: Latest TechnicalIndicator values.
            latest_close: Most recent close price.
            prev_indicators: Previous period's indicators (for momentum).

        Returns:
            np.ndarray of shape (n_features,)
        """
        sma20 = indicators.get("sma_20") or latest_close
        sma50 = indicators.get("sma_50") or latest_close
        bb_upper = indicators.get("bollinger_upper") or latest_close
        bb_lower = indicators.get("bollinger_lower") or latest_close
        macd = indicators.get("macd") or 0.0
        macd_signal = indicators.get("macd_signal") or 0.0
        prev_rsi = prev_indicators.get("rsi_14", 50.0) if prev_indicators else 50.0

        bb_range = bb_upper - bb_lower
        bb_position = (latest_close - bb_lower) / bb_range if bb_range > 0 else 0.5

        features = {
            "rsi_14": indicators.get("rsi_14", 50.0),
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_histogram": indicators.get("macd_histogram", 0.0),
            "sma_20": sma20,
            "sma_50": sma50,
            "ema_12": indicators.get("ema_12", latest_close),
            "ema_26": indicators.get("ema_26", latest_close),
            "bollinger_upper": bb_upper,
            "bollinger_lower": bb_lower,
            "bollinger_width": indicators.get("bollinger_width", 0.0),
            "atr_14": indicators.get("atr_14", 0.0),
            "volume_sma_20": indicators.get("volume_sma_20", 0.0),
            "obv": indicators.get("obv", 0.0),
            "avg_sentiment_score": indicators.get("avg_sentiment_score", 0.0),
            "fear_greed_index": indicators.get("fear_greed_index", 50.0),
            # Derived features
            "price_vs_sma20": (latest_close - sma20) / sma20 if sma20 else 0.0,
            "price_vs_sma50": (latest_close - sma50) / sma50 if sma50 else 0.0,
            "rsi_momentum": indicators.get("rsi_14", 50.0) - prev_rsi,
            "volume_ratio": 1.0,  # Placeholder — requires real volume
            "macd_cross": 1.0 if macd > macd_signal else -1.0,
            "bb_position": bb_position,
        }
        return np.array([features[col] for col in self.FEATURE_COLUMNS], dtype=np.float32)


class MarketPredictor:
    """
    Ensemble market direction predictor.

    Uses LightGBM and XGBoost trained on historical technical features.
    Ensemble weight: 60% LightGBM + 40% XGBoost (tunable).

    Model lifecycle:
      - train(): Train from scratch on historical data.
      - save(version): Persist to MODEL_REGISTRY_PATH.
      - load(version): Load a specific version.
      - predict(): Run inference.
    """

    MODEL_NAME = "MarketPredictor"
    LGBM_WEIGHT = 0.6
    XGB_WEIGHT = 0.4

    def __init__(self) -> None:
        self._registry = Path(settings.ml.model_registry_path) / "market_predictor"
        self._registry.mkdir(parents=True, exist_ok=True)
        self._lgbm_model = None
        self._xgb_model = None
        self._feature_builder = FeatureBuilder()
        self._version = "0.0.0"
        self._is_loaded = False

    def train(self, df: pd.DataFrame, target_col: str = "direction") -> Dict:
        """
        Train both models on labelled OHLCV+indicator data.

        Args:
            df: DataFrame with feature columns + target column.
                target: 1=bullish, 0=bearish, 2=neutral
            target_col: Column name for the label.

        Returns:
            dict with train/val accuracy metrics.
        """
        try:
            import lightgbm as lgb
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
        except ImportError as exc:
            raise MLModelError(self.MODEL_NAME, f"ML packages not installed: {exc}")

        feature_cols = [c for c in FeatureBuilder.FEATURE_COLUMNS if c in df.columns]
        X = df[feature_cols].values.astype(np.float32)
        y = df[target_col].values

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # ── LightGBM ─────────────────────────────────────────────────────────
        lgbm_params = {
            "objective": "multiclass",
            "num_class": 3,
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 63,
            "min_child_samples": 20,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 0.1,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        self._lgbm_model = lgb.LGBMClassifier(**lgbm_params)
        self._lgbm_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        # ── XGBoost ──────────────────────────────────────────────────────────
        xgb_params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "n_estimators": 300,
            "learning_rate": 0.05,
            "max_depth": 6,
            "min_child_weight": 3,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0,
            "eval_metric": "mlogloss",
        }
        self._xgb_model = xgb.XGBClassifier(**xgb_params)
        self._xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=50,
            verbose=False,
        )

        # ── Metrics ───────────────────────────────────────────────────────────
        lgbm_pred = self._lgbm_model.predict(X_val)
        xgb_pred = self._xgb_model.predict(X_val)
        ensemble_probs = self._ensemble_probs(X_val)
        ensemble_pred = np.argmax(ensemble_probs, axis=1)

        metrics = {
            "lgbm_val_accuracy": float(accuracy_score(y_val, lgbm_pred)),
            "xgb_val_accuracy": float(accuracy_score(y_val, xgb_pred)),
            "ensemble_val_accuracy": float(accuracy_score(y_val, ensemble_pred)),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "features": feature_cols,
        }
        self._is_loaded = True
        logger.info("MarketPredictor trained", **metrics)
        return metrics

    def _ensemble_probs(self, X: np.ndarray) -> np.ndarray:
        """Weighted probability average from both models."""
        lgbm_probs = self._lgbm_model.predict_proba(X)
        xgb_probs = self._xgb_model.predict_proba(X)
        return self.LGBM_WEIGHT * lgbm_probs + self.XGB_WEIGHT * xgb_probs

    def predict(self, features: np.ndarray) -> Tuple[str, float]:
        """
        Run ensemble prediction on a feature vector.

        Returns:
            (direction, confidence) where direction in {bullish, bearish, neutral}
            and confidence in [0, 1].
        """
        if not self._is_loaded:
            self._try_load_latest()

        if not self._is_loaded:
            logger.warning("MarketPredictor not trained — returning neutral")
            return "neutral", 0.5

        X = features.reshape(1, -1)
        probs = self._ensemble_probs(X)[0]
        label_map = {0: "bearish", 1: "bullish", 2: "neutral"}
        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])
        direction = label_map[predicted_class]

        return direction, confidence

    def save(self, version: str) -> Path:
        """Persist both models to the registry."""
        path = self._registry / version
        path.mkdir(parents=True, exist_ok=True)

        with open(path / "lgbm.pkl", "wb") as f:
            pickle.dump(self._lgbm_model, f)
        with open(path / "xgb.pkl", "wb") as f:
            pickle.dump(self._xgb_model, f)

        meta = {"version": version, "trained_at": datetime.now(tz=timezone.utc).isoformat()}
        (path / "meta.json").write_text(json.dumps(meta))
        self._version = version
        logger.info("MarketPredictor saved", version=version, path=str(path))
        return path

    def load(self, version: str) -> None:
        """Load a specific model version from the registry."""
        path = self._registry / version
        try:
            with open(path / "lgbm.pkl", "rb") as f:
                self._lgbm_model = pickle.load(f)
            with open(path / "xgb.pkl", "rb") as f:
                self._xgb_model = pickle.load(f)
            self._version = version
            self._is_loaded = True
            logger.info("MarketPredictor loaded", version=version)
        except FileNotFoundError as exc:
            raise MLModelError(self.MODEL_NAME, f"Version '{version}' not found: {exc}")

    def _try_load_latest(self) -> None:
        """Attempt to load the most recent saved version."""
        versions = sorted(self._registry.glob("*/meta.json"), reverse=True)
        if versions:
            version = versions[0].parent.name
            try:
                self.load(version)
            except Exception:
                pass

    @property
    def feature_columns(self) -> List[str]:
        return FeatureBuilder.FEATURE_COLUMNS
