"""Market intelligence, prediction, and recommendation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MarketSentimentResponse(BaseModel):
    symbol: str
    avg_sentiment: float = Field(..., ge=-1.0, le=1.0)
    news_count: int
    sentiment_label: str
    recent_news: List[dict]
    as_of: datetime


class NewsArticleResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    title: str
    summary: Optional[str]
    url: str
    source: str
    published_at: str
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    related_symbols: Optional[str]
    created_at: datetime


class PredictionRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    horizon_days: int = Field(default=7, ge=1, le=90)


class PredictionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    symbol: str
    direction: str
    confidence: float
    predicted_price: Optional[float]
    prediction_horizon_days: int
    model_name: str
    model_version: str
    created_at: datetime


class RecommendationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    action: str
    symbol: Optional[str]
    category: str
    title: str
    explanation: str
    confidence_score: float
    expected_roi: Optional[float]
    risk_level: str
    created_at: datetime


class TechnicalIndicatorResponse(BaseModel):
    model_config = {"from_attributes": True}
    symbol: str
    timeframe: str
    rsi_14: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    sma_20: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    bollinger_upper: Optional[float]
    bollinger_lower: Optional[float]
    fear_greed_index: Optional[float]
    avg_sentiment_score: Optional[float]
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    include_portfolio_context: bool = True


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []
    context_used: List[str] = []


class DashboardResponse(BaseModel):
    user_id: uuid.UUID
    financial_health_score: float
    net_worth: float
    total_assets: float
    total_liabilities: float
    monthly_income: float
    monthly_expenses: float
    monthly_savings: float
    savings_rate: float
    debt_to_income_ratio: float
    emergency_fund_months: float
    investment_value: float
    crypto_value: float
    top_recommendations: List[RecommendationResponse]
    recent_predictions: List[PredictionResponse]
    portfolio_sentiment: dict


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: dict[str, dict]
    timestamp: datetime
