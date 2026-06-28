"""Market data, news, predictions, and recommendation repositories."""

from __future__ import annotations

import uuid
from typing import List, Optional, Sequence

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres.market import (
    MarketSnapshot, NewsArticle, Prediction, Recommendation,
    TechnicalIndicator
)
from app.repositories.base import BaseRepository


class MarketSnapshotRepository(BaseRepository[MarketSnapshot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MarketSnapshot, session)

    async def get_latest(self, symbol: str) -> Optional[MarketSnapshot]:
        result = await self._session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol.upper())
            .order_by(desc(MarketSnapshot.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self, symbol: str, limit: int = 90
    ) -> Sequence[MarketSnapshot]:
        result = await self._session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol.upper())
            .order_by(desc(MarketSnapshot.created_at))
            .limit(limit)
        )
        return result.scalars().all()


class NewsArticleRepository(BaseRepository[NewsArticle]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NewsArticle, session)

    async def get_latest(self, limit: int = 50) -> Sequence[NewsArticle]:
        result = await self._session.execute(
            select(NewsArticle)
            .where(NewsArticle.sentiment_label.is_not(None))
            .order_by(desc(NewsArticle.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def url_exists(self, url: str) -> bool:
        result = await self._session.execute(
            select(NewsArticle.id).where(NewsArticle.url == url)
        )
        return result.scalar_one_or_none() is not None

    async def get_unprocessed(self, limit: int = 20) -> Sequence[NewsArticle]:
        """Get articles that haven't been sentiment-scored yet."""
        result = await self._session.execute(
            select(NewsArticle)
            .where(NewsArticle.sentiment_label.is_(None))
            .order_by(NewsArticle.created_at)
            .limit(limit)
        )
        return result.scalars().all()


class PredictionRepository(BaseRepository[Prediction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Prediction, session)

    async def get_latest_for_symbol(self, symbol: str) -> Optional[Prediction]:
        result = await self._session.execute(
            select(Prediction)
            .where(Prediction.symbol == symbol.upper())
            .order_by(desc(Prediction.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_recent_predictions(
        self, symbols: List[str], limit: int = 20
    ) -> Sequence[Prediction]:
        result = await self._session.execute(
            select(Prediction)
            .where(Prediction.symbol.in_([s.upper() for s in symbols]))
            .order_by(desc(Prediction.created_at))
            .limit(limit)
        )
        return result.scalars().all()


class RecommendationRepository(BaseRepository[Recommendation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Recommendation, session)

    async def get_user_recommendations(
        self, user_id: uuid.UUID, limit: int = 10, active_only: bool = True
    ) -> Sequence[Recommendation]:
        query = (
            select(Recommendation)
            .where(Recommendation.user_id == user_id)
        )
        if active_only:
            query = query.where(
                and_(
                    Recommendation.is_dismissed == False,
                    Recommendation.is_acted_upon == False,
                )
            )
        result = await self._session.execute(
            query.order_by(desc(Recommendation.confidence_score)).limit(limit)
        )
        return result.scalars().all()


class TechnicalIndicatorRepository(BaseRepository[TechnicalIndicator]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TechnicalIndicator, session)

    async def get_latest(
        self, symbol: str, timeframe: str = "1D"
    ) -> Optional[TechnicalIndicator]:
        result = await self._session.execute(
            select(TechnicalIndicator)
            .where(
                and_(
                    TechnicalIndicator.symbol == symbol.upper(),
                    TechnicalIndicator.timeframe == timeframe,
                )
            )
            .order_by(desc(TechnicalIndicator.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
