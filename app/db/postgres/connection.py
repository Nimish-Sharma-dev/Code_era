"""
Async PostgreSQL connection management using SQLAlchemy 2.0.

Uses asyncpg driver under the hood for maximum throughput.
Connection pooling is tuned for concurrent fintech workloads.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Singleton engine — shared across the application lifetime
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the singleton async SQLAlchemy engine, creating it if needed."""
    global _engine
    if _engine is None:
        db = settings.database
        _engine = create_async_engine(
            db.async_url,
            pool_size=db.pool_size,
            max_overflow=db.max_overflow,
            pool_timeout=db.pool_timeout,
            pool_pre_ping=db.pool_pre_ping,
            echo=db.echo and settings.is_development,
            pool_recycle=3600,  # Recycle connections every hour
            connect_args={
                "server_settings": {
                    "application_name": settings.app_name,
                    "jit": "off",  # Disable JIT for predictable latency
                },
                "command_timeout": 30,
            },
        )
        logger.info("PostgreSQL engine created", url=db.async_url.split("@")[-1])
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager providing a database session with automatic
    commit/rollback and connection release.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency providing a scoped database session.

    Usage in route:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_db_session() as session:
        yield session


async def dispose_engine() -> None:
    """Gracefully close all pooled connections. Called on application shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("PostgreSQL connection pool disposed")
        _engine = None


async def check_database_health() -> dict:
    """
    Verify database connectivity for health-check endpoints.

    Returns:
        dict with 'status' and optionally 'error'.
    """
    try:
        async with get_db_session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as exc:
        logger.error("Database health check failed", error=str(exc))
        return {"status": "unhealthy", "error": str(exc)}
