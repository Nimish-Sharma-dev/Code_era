"""
Redis cache client with async support.

Provides typed cache operations with automatic serialization/deserialization.
Used for:
  - Session/refresh token storage
  - Market data caching (TTL-based)
  - Rate limiting counters
  - Celery result backend
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional, Type, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

T = TypeVar("T")

_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """Return singleton async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis.max_connections,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
        logger.info("Redis client initialised")
    return _redis_client


async def close_redis() -> None:
    """Close Redis connections on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        logger.info("Redis connection closed")
        _redis_client = None


class CacheManager:
    """
    High-level typed cache operations.

    All values are JSON-serialized for compatibility and portability.
    Keys follow the pattern: `{namespace}:{identifier}`.
    """

    def __init__(self, redis: Redis, default_ttl: int = 300) -> None:
        self._redis = redis
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key, deserializing from JSON."""
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Cache get failed", key=key, error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store a value with optional TTL override."""
        try:
            serialized = json.dumps(value, default=str)
            await self._redis.setex(key, ttl or self._default_ttl, serialized)
            return True
        except (RedisError, TypeError) as exc:
            logger.warning("Cache set failed", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> bool:
        """Remove a key from cache."""
        try:
            await self._redis.delete(key)
            return True
        except RedisError as exc:
            logger.warning("Cache delete failed", key=key, error=str(exc))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists without fetching the value."""
        try:
            return bool(await self._redis.exists(key))
        except RedisError:
            return False

    async def increment(self, key: str, ttl: Optional[int] = None) -> int:
        """Atomic increment for rate limiting counters."""
        try:
            pipe = self._redis.pipeline()
            await pipe.incr(key)
            if ttl:
                await pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        except RedisError as exc:
            logger.warning("Cache increment failed", key=key, error=str(exc))
            return 0

    async def set_token(self, jti: str, user_id: str, ttl: int) -> None:
        """Store a refresh token JTI for server-side revocation."""
        await self.set(f"token:refresh:{jti}", {"user_id": user_id}, ttl=ttl)

    async def revoke_token(self, jti: str) -> None:
        """Revoke a refresh token by removing its JTI from cache."""
        await self.delete(f"token:refresh:{jti}")

    async def is_token_valid(self, jti: str) -> bool:
        """Check if a refresh token JTI is still valid (not revoked)."""
        return await self.exists(f"token:refresh:{jti}")

    async def cache_market_data(
        self, symbol: str, data: dict, ttl: int = 60
    ) -> None:
        """Cache market snapshot data for a symbol."""
        await self.set(f"market:{symbol}", data, ttl=ttl)

    async def get_market_data(self, symbol: str) -> Optional[dict]:
        """Retrieve cached market data."""
        return await self.get(f"market:{symbol}")

    async def check_rate_limit(
        self, identifier: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check and increment rate limit counter.

        Returns:
            (is_allowed, current_count)
        """
        key = f"ratelimit:{identifier}"
        count = await self.increment(key, ttl=window_seconds)
        return count <= limit, count


async def get_cache_manager() -> CacheManager:
    """FastAPI dependency providing a CacheManager instance."""
    return CacheManager(
        redis=get_redis(),
        default_ttl=settings.redis.cache_ttl_seconds,
    )


async def check_redis_health() -> dict:
    """Verify Redis connectivity for health check."""
    try:
        client = get_redis()
        await client.ping()
        return {"status": "healthy"}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
