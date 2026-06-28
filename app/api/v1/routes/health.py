"""Public health check endpoint (no auth required)."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.config.settings import get_settings

settings = get_settings()
router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def liveness():
    """Simple liveness check — returns 200 if the process is running."""
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@router.get("/ready", summary="Readiness probe")
async def readiness():
    """Readiness check — verifies DB + Redis connectivity."""
    from app.db.postgres.connection import check_database_health
    from app.db.postgres.redis_client import check_redis_health
    pg = await check_database_health()
    rd = await check_redis_health()
    healthy = pg["status"] == "healthy" and rd["status"] == "healthy"
    return {
        "status": "ready" if healthy else "not_ready",
        "postgresql": pg["status"],
        "redis": rd["status"],
        "version": settings.app_version,
    }
