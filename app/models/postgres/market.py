"""
Market-related PostgreSQL models: MarketSnapshot, NewsArticle,
TechnicalIndicator, Prediction, Recommendation.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.postgres.base import Base, TimestampMixin, UUIDMixin


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class PredictionDirection(str, enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RecommendationAction(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REDUCE = "reduce"
    INCREASE = "increase"
    AVOID = "avoid"
    REBALANCE = "rebalance"
    PAY_DEBT = "pay_debt"
    BUILD_EMERGENCY_FUND = "build_emergency_fund"


class MarketSnapshot(Base, UUIDMixin, TimestampMixin):
    """OHLCV market data snapshot for an asset."""

    __tablename__ = "market_snapshots"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), default="equity")  # equity/crypto
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # yahoo/binance/coingecko


class NewsArticle(Base, UUIDMixin, TimestampMixin):
    """Financial news article with FinBERT sentiment scores."""

    __tablename__ = "news_articles"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[str] = mapped_column(String(30), nullable=False)
    related_symbols: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    # FinBERT scores
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(
        Enum(SentimentLabel), nullable=True
    )
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    positive_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    neutral_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_stored: Mapped[bool] = mapped_column(Boolean, default=False)


class TechnicalIndicator(Base, UUIDMixin, TimestampMixin):
    """Computed technical indicators for market symbols."""

    __tablename__ = "technical_indicators"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1D")  # 1H/4H/1D/1W

    # Trend
    sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_26: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Momentum
    rsi_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Volatility
    atr_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_lower: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Volume
    volume_sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    obv: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Market context
    fear_greed_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class Prediction(Base, UUIDMixin, TimestampMixin):
    """ML model price direction predictions."""

    __tablename__ = "predictions"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[PredictionDirection] = mapped_column(Enum(PredictionDirection), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0–1.0
    predicted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_horizon_days: Mapped[int] = mapped_column(Integer, default=7)
    features_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    actual_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)  # For backtesting
    was_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Recommendation(Base, UUIDMixin, TimestampMixin):
    """Personalized financial recommendations generated by the recommendation engine."""

    __tablename__ = "recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[RecommendationAction] = mapped_column(Enum(RecommendationAction), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # investment/debt/savings
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    expected_roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    is_acted_upon: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
