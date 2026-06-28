"""
Neo4j async driver management.

Uses the official neo4j Python driver with an async session factory.
The driver maintains a connection pool internally; we expose a thin
async context manager for use in repositories.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_driver: Optional[AsyncDriver] = None


def get_driver() -> AsyncDriver:
    """Return the singleton async Neo4j driver, creating it if needed."""
    global _driver
    if _driver is None:
        neo4j_cfg = settings.neo4j
        _driver = AsyncGraphDatabase.driver(
            neo4j_cfg.uri,
            auth=(neo4j_cfg.user, neo4j_cfg.password),
            max_connection_pool_size=neo4j_cfg.max_connection_pool_size,
            connection_timeout=neo4j_cfg.connection_timeout,
            max_transaction_retry_time=neo4j_cfg.max_transaction_retry_time,
        )
        logger.info("Neo4j driver initialised", uri=neo4j_cfg.uri)
    return _driver


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager providing a Neo4j session.

    Automatically manages session lifecycle including cleanup on error.
    """
    driver = get_driver()
    async with driver.session(database=settings.neo4j.database) as session:
        yield session


async def close_driver() -> None:
    """Close the Neo4j driver gracefully on application shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        logger.info("Neo4j driver closed")
        _driver = None


async def check_neo4j_health() -> dict:
    """Verify Neo4j connectivity for health check endpoints."""
    try:
        async with get_neo4j_session() as session:
            result = await session.run("RETURN 1 AS health")
            await result.single()
        return {"status": "healthy"}
    except ServiceUnavailable as exc:
        logger.error("Neo4j health check failed", error=str(exc))
        return {"status": "unhealthy", "error": str(exc)}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def create_constraints_and_indexes() -> None:
    """
    Create Neo4j constraints and indexes on startup.

    Idempotent — safe to run multiple times.
    These are critical for graph query performance.
    """
    constraints = [
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT wallet_id_unique IF NOT EXISTS FOR (w:Wallet) REQUIRE w.id IS UNIQUE",
        "CREATE CONSTRAINT asset_symbol_unique IF NOT EXISTS FOR (a:Asset) REQUIRE a.symbol IS UNIQUE",
        "CREATE CONSTRAINT news_url_unique IF NOT EXISTS FOR (n:News) REQUIRE n.url IS UNIQUE",
        "CREATE INDEX user_email_index IF NOT EXISTS FOR (u:User) ON (u.email)",
        "CREATE INDEX asset_type_index IF NOT EXISTS FOR (a:Asset) ON (a.asset_type)",
        "CREATE INDEX news_published_index IF NOT EXISTS FOR (n:News) ON (n.published_at)",
        "CREATE INDEX prediction_symbol_index IF NOT EXISTS FOR (p:Prediction) ON (p.symbol)",
    ]

    async with get_neo4j_session() as session:
        for query in constraints:
            try:
                await session.run(query)
            except Exception as exc:
                logger.warning("Constraint/index creation skipped", query=query, error=str(exc))

    logger.info("Neo4j constraints and indexes initialised")
