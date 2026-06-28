"""
Market intelligence API routes:
  GET /market/sentiment/{symbol}
  GET /market/news
  GET /market/predictions/{symbol}
  GET /market/technical/{symbol}
  POST /predict
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.graph.graph_service import GraphService
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.repositories.market_repository import (
    NewsArticleRepository, PredictionRepository, TechnicalIndicatorRepository,
)
from app.schemas.market import (
    MarketSentimentResponse, NewsArticleResponse,
    PredictionRequest, PredictionResponse, TechnicalIndicatorResponse,
)

router = APIRouter(prefix="/market", tags=["Market Intelligence"], dependencies=[Depends(rate_limit_check)])


@router.get("/sentiment/{symbol}", response_model=MarketSentimentResponse, summary="Get asset sentiment from news")
async def get_asset_sentiment(
    symbol: str,
    days_back: int = Query(default=7, ge=1, le=30),
    current_user: CurrentUser = None,
):
    """
    Aggregate FinBERT-scored news sentiment for a market symbol.
    Returns average sentiment score, article count, and top recent headlines.
    """
    graph = GraphService()
    since = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).isoformat()
    data = await graph.get_asset_sentiment(symbol.upper(), since=since)

    label = "neutral"
    if data["avg_sentiment"] > 0.1:
        label = "positive"
    elif data["avg_sentiment"] < -0.1:
        label = "negative"

    return MarketSentimentResponse(
        symbol=symbol.upper(),
        avg_sentiment=data["avg_sentiment"],
        news_count=data["news_count"],
        sentiment_label=label,
        recent_news=data["recent_news"][:5],
        as_of=datetime.now(tz=timezone.utc),
    )


@router.get("/news", response_model=List[NewsArticleResponse], summary="Get latest financial news")
async def get_news(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent sentiment-scored financial news articles."""
    repo = NewsArticleRepository(db)
    articles = await repo.get_latest(limit=limit)
    return [NewsArticleResponse.model_validate(a) for a in articles]


@router.get("/predictions/{symbol}", response_model=PredictionResponse, summary="Get latest prediction for symbol")
async def get_prediction(
    symbol: str,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent ML price-direction prediction for a symbol."""
    from app.core.exceptions import NotFoundError
    repo = PredictionRepository(db)
    pred = await repo.get_latest_for_symbol(symbol.upper())
    if not pred:
        raise NotFoundError("Prediction", symbol)
    return PredictionResponse.model_validate(pred)


@router.post("/predict", response_model=PredictionResponse, summary="Generate on-demand prediction")
async def generate_prediction(
    request: PredictionRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an on-demand ML prediction for a symbol.
    Uses cached technical indicators if available, otherwise returns last stored prediction.
    """
    from app.ml_services.market_predictor import MarketPredictor, FeatureBuilder
    from app.repositories.market_repository import TechnicalIndicatorRepository, PredictionRepository

    indicator_repo = TechnicalIndicatorRepository(db)
    pred_repo = PredictionRepository(db)

    indicator = await indicator_repo.get_latest(request.symbol.upper())
    if not indicator:
        # Fall back to last stored prediction
        pred = await pred_repo.get_latest_for_symbol(request.symbol.upper())
        if pred:
            return PredictionResponse.model_validate(pred)
        from app.core.exceptions import NotFoundError
        raise NotFoundError("TechnicalIndicator", request.symbol)

    predictor = MarketPredictor()
    feature_builder = FeatureBuilder()
    features = feature_builder.build(
        indicators={col: getattr(indicator, col, None) for col in feature_builder.FEATURE_COLUMNS if hasattr(indicator, col)},
        latest_close=indicator.sma_20 or 100.0,
    )
    direction, confidence = predictor.predict(features)

    saved = await pred_repo.create(
        symbol=request.symbol.upper(),
        model_name="MarketPredictor",
        model_version=predictor._version,
        direction=direction,
        confidence=confidence,
        prediction_horizon_days=request.horizon_days,
    )
    return PredictionResponse.model_validate(saved)


@router.get("/technical/{symbol}", response_model=TechnicalIndicatorResponse, summary="Get technical indicators")
async def get_technical_indicators(
    symbol: str,
    timeframe: str = Query(default="1D"),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the latest computed technical indicators for a symbol."""
    from app.core.exceptions import NotFoundError
    repo = TechnicalIndicatorRepository(db)
    indicator = await repo.get_latest(symbol.upper(), timeframe)
    if not indicator:
        raise NotFoundError("TechnicalIndicator", symbol)
    return TechnicalIndicatorResponse.model_validate(indicator)
