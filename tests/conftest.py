"""
Pytest fixtures shared across all test suites.

Provides:
  - Async test client (TestClient wrapping the FastAPI app)
  - Isolated test database session (rolled back after each test)
  - Mock Redis cache
  - Mock Neo4j graph service
  - Authenticated test user and token
"""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password, UserRole
from app.main import create_app
from app.models.postgres.base import Base
from app.models.postgres.user import User, UserStatus, RiskToleranceLevel
from app.db.postgres.connection import get_db
from app.db.postgres.redis_client import get_cache_manager, CacheManager


# ─── Event Loop ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── In-Memory Test Database ─────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Each test gets a transaction that is rolled back afterwards."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ─── Mock Cache ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_cache():
    cache = AsyncMock(spec=CacheManager)
    cache.check_rate_limit.return_value = (True, 1)
    cache.is_token_valid.return_value = True
    cache.set_token.return_value = None
    cache.revoke_token.return_value = None
    return cache


# ─── Test User ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="test@finai.com",
        username="testuser",
        full_name="Test User",
        hashed_password=hash_password("TestPass123"),
        role=UserRole.USER.value,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        risk_tolerance=RiskToleranceLevel.MODERATE,
        currency="USD",
        timezone="UTC",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def test_token(test_user: User) -> str:
    return create_access_token(str(test_user.id), role=UserRole.USER)


@pytest.fixture
def auth_headers(test_token: str) -> dict:
    return {"Authorization": f"Bearer {test_token}"}


# ─── Test HTTP Client ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_cache: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with overridden DB and cache dependencies."""
    app = create_app()

    async def override_get_db():
        yield db_session

    async def override_get_cache():
        return mock_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache_manager] = override_get_cache

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
