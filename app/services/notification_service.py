"""
Notification service: creates in-app notifications and optionally sends emails.

Triggered by:
  - Sentiment threshold breaches (FinBERT pipeline)
  - High-risk predictions
  - Savings goal milestones
  - Debt reminders
  - System recommendations
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.postgres.financial import Notification, NotificationType
from app.repositories.base import BaseRepository
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def get_user_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
    ):
        from sqlalchemy import select, and_, desc
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        result = await self._session.execute(
            query.order_by(desc(Notification.created_at)).limit(limit)
        )
        return result.scalars().all()

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        from sqlalchemy import update
        await self._session.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True)
        )


class NotificationService:
    """
    Creates notifications for users based on platform events.

    Stored in PostgreSQL for persistence; future versions can push via
    WebSocket, FCM (mobile), or email.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = NotificationRepository(session)

    async def notify_sentiment_alert(
        self, user_id: uuid.UUID, symbol: str,
        sentiment_score: float, label: str,
    ) -> None:
        """Fire when FinBERT detects extreme sentiment for a held asset."""
        direction = "positive 📈" if label == "positive" else "negative 📉"
        await self._repo.create(
            user_id=user_id,
            notification_type=NotificationType.SENTIMENT_ALERT,
            title=f"Sentiment Alert: {symbol}",
            message=(
                f"Strong {direction} news sentiment detected for {symbol} "
                f"(score: {sentiment_score:+.2f}). Review your position."
            ),
            metadata=json.dumps({"symbol": symbol, "score": sentiment_score, "label": label}),
        )
        logger.info("Sentiment alert created", user_id=str(user_id), symbol=symbol)

    async def notify_recommendation(
        self, user_id: uuid.UUID, title: str, message: str, metadata: Optional[Dict] = None
    ) -> None:
        """New personalised recommendation available."""
        await self._repo.create(
            user_id=user_id,
            notification_type=NotificationType.RECOMMENDATION,
            title=title,
            message=message,
            metadata=json.dumps(metadata) if metadata else None,
        )

    async def notify_goal_milestone(
        self, user_id: uuid.UUID, goal_name: str, progress_pct: float
    ) -> None:
        """Fire at 25%, 50%, 75%, and 100% goal completion."""
        milestones = [25, 50, 75, 100]
        for milestone in milestones:
            if abs(progress_pct - milestone) < 1.0:
                emoji = "🎉" if milestone == 100 else "🎯"
                await self._repo.create(
                    user_id=user_id,
                    notification_type=NotificationType.GOAL_MILESTONE,
                    title=f"{emoji} Goal Milestone: {goal_name}",
                    message=f"You've reached {milestone}% of your '{goal_name}' goal!",
                    metadata=json.dumps({"goal_name": goal_name, "progress": progress_pct}),
                )
                break

    async def notify_risk_warning(
        self, user_id: uuid.UUID, risk_score: float, risk_level: str, explanation: str
    ) -> None:
        """Alert when risk score worsens significantly."""
        if risk_level in ("high", "critical"):
            await self._repo.create(
                user_id=user_id,
                notification_type=NotificationType.RISK_WARNING,
                title=f"⚠️ Risk Alert: {risk_level.upper()} Financial Risk",
                message=explanation,
                metadata=json.dumps({"risk_score": risk_score, "risk_level": risk_level}),
            )

    async def notify_market_event(
        self, user_id: uuid.UUID, event_type: str, message: str
    ) -> None:
        """Market-related event notifications."""
        await self._repo.create(
            user_id=user_id,
            notification_type=NotificationType.MARKET_EVENT,
            title=f"Market Event: {event_type}",
            message=message,
        )

    async def get_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False
    ):
        return await self._repo.get_user_notifications(user_id, unread_only=unread_only)

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        await self._repo.mark_read(notification_id)
