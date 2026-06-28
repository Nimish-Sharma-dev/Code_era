"""
Celery tasks for notification dispatch.

Triggered by:
  - Sentiment threshold breaches (post FinBERT run)
  - Risk score deterioration
  - Goal milestones
"""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.workers.notification_tasks.dispatch_sentiment_alerts")
def dispatch_sentiment_alerts(self):
    """
    After FinBERT pipeline runs, check if any user holdings have extreme sentiment.
    Fire notifications for holdings with |score| >= threshold.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_sentiment_alerts())
    finally:
        loop.close()


async def _async_sentiment_alerts():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.user import User, UserStatus
    from app.models.postgres.financial import Investment
    from app.graph.graph_service import GraphService
    from app.services.notification_service import NotificationService
    from app.config.settings import get_settings

    settings = get_settings()
    graph = GraphService()
    threshold = settings.ml.sentiment_alert_threshold
    since = (datetime.now(tz=timezone.utc) - timedelta(days=3)).isoformat()
    dispatched = 0

    async with get_db_session() as session:
        result = await session.execute(
            select(Investment.user_id, Investment.symbol)
            .join(User, User.id == Investment.user_id)
            .where(User.status == UserStatus.ACTIVE, Investment.is_active == True)
        )
        holdings = result.all()

        notification_svc = NotificationService(session)

        for user_id, symbol in holdings:
            try:
                sentiment_data = await graph.get_asset_sentiment(symbol, since=since)
                score = sentiment_data.get("avg_sentiment", 0.0)
                news_count = sentiment_data.get("news_count", 0)

                if news_count > 0 and abs(score) >= threshold:
                    label = "positive" if score > 0 else "negative"
                    await notification_svc.notify_sentiment_alert(
                        user_id=user_id, symbol=symbol,
                        sentiment_score=score, label=label,
                    )
                    dispatched += 1
            except Exception as exc:
                logger.warning("Sentiment alert dispatch failed",
                               symbol=symbol, error=str(exc))

    logger.info("Sentiment alerts dispatched", count=dispatched)
    return {"dispatched": dispatched}


@celery_app.task(bind=True, name="app.workers.notification_tasks.check_goal_milestones")
def check_goal_milestones(self):
    """Check all user savings goals for milestone achievements."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_check_milestones())
    finally:
        loop.close()


async def _async_check_milestones():
    from sqlalchemy import select
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.financial import SavingsGoal
    from app.services.notification_service import NotificationService

    notified = 0
    async with get_db_session() as session:
        result = await session.execute(
            select(SavingsGoal).where(SavingsGoal.is_completed == False)
        )
        goals = result.scalars().all()
        svc = NotificationService(session)

        for goal in goals:
            if goal.target_amount > 0:
                pct = (goal.current_amount / goal.target_amount) * 100
                await svc.notify_goal_milestone(goal.user_id, goal.name, pct)
                notified += 1

    return {"checked": len(goals), "notified": notified}
