"""Admin panel routes — requires ADMIN role."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
from app.db.postgres.connection import get_db
from app.db.postgres.redis_client import check_redis_health
from app.db.postgres.connection import check_database_health
from app.db.neo4j.connection import check_neo4j_health
from app.middleware.auth_middleware import require_role
from app.models.postgres.user import User, UserStatus
from app.models.postgres.market import NewsArticle, Prediction
from app.schemas.market import HealthCheckResponse
from app.config.settings import get_settings

settings = get_settings()
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/health", response_model=HealthCheckResponse, summary="Full system health check")
async def health_check():
    """
    Check connectivity of all dependent services.
    Requires ADMIN role.
    """
    pg_health = await check_database_health()
    redis_health = await check_redis_health()
    neo4j_health = await check_neo4j_health()

    all_healthy = all(
        s.get("status") == "healthy"
        for s in [pg_health, redis_health, neo4j_health]
    )

    return HealthCheckResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.app_version,
        environment=settings.app_env,
        services={
            "postgresql": pg_health,
            "redis": redis_health,
            "neo4j": neo4j_health,
        },
        timestamp=datetime.now(tz=timezone.utc),
    )


@router.get("/stats", summary="Platform statistics")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return aggregate platform metrics."""
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
    )
    total_articles = await db.scalar(select(func.count(NewsArticle.id)))
    total_predictions = await db.scalar(select(func.count(Prediction.id)))

    return {
        "users": {"total": total_users, "active": active_users},
        "content": {"news_articles": total_articles, "predictions": total_predictions},
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/users", summary="List all users (paginated)")
async def list_users(
    offset: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of all platform users."""
    result = await db.execute(
        select(User).where(User.deleted_at.is_(None))
        .offset(offset).limit(limit)
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id), "email": u.email, "username": u.username,
            "status": str(u.status.value if hasattr(u.status, 'value') else u.status),
            "role": u.role, "created_at": u.created_at.isoformat(),
            "financial_health_score": u.financial_health_score,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/suspend", status_code=204, summary="Suspend a user account")
async def suspend_user(user_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update
    import uuid
    await db.execute(
        update(User).where(User.id == uuid.UUID(user_id))
        .values(status=UserStatus.SUSPENDED)
    )
    await db.commit()


@router.post("/workers/trigger/{task_name}", summary="Manually trigger a Celery task")
async def trigger_task(task_name: str):
    """Manually fire a background task for debugging/operations."""
    from app.workers.market_tasks import fetch_and_store_news, fetch_all_market_prices
    from app.workers.ml_tasks import run_sentiment_pipeline, run_prediction_pipeline

    task_map = {
        "fetch_news": fetch_and_store_news,
        "fetch_prices": fetch_all_market_prices,
        "run_sentiment": run_sentiment_pipeline,
        "run_predictions": run_prediction_pipeline,
    }
    task_fn = task_map.get(task_name)
    if not task_fn:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found. Available: {list(task_map.keys())}")

    result = task_fn.delay()
    return {"task_id": result.id, "task_name": task_name, "status": "queued"}
