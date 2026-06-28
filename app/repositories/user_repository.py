"""
User repository: domain-specific queries beyond basic CRUD.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.postgres.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication and profile queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email address (case-insensitive)."""
        result = await self._session.execute(
            select(User)
            .where(User.email == email.lower().strip())
            .where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by username."""
        result = await self._session.execute(
            select(User)
            .where(User.username == username)
            .where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_with_relationships(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user with all financial relationships eagerly loaded."""
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
            .options(
                selectinload(User.wallets),
                selectinload(User.incomes),
                selectinload(User.expenses),
                selectinload(User.loans),
                selectinload(User.savings_goals),
                selectinload(User.investments),
            )
        )
        return result.scalar_one_or_none()

    async def update_financial_health_score(
        self, user_id: uuid.UUID, score: float
    ) -> None:
        """Update just the financial health score (called by ML engine)."""
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(financial_health_score=score)
        )

    async def record_login(self, user_id: uuid.UUID) -> None:
        """Update last login timestamp and reset failed login counter."""
        from datetime import datetime, timezone
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(tz=timezone.utc),
                failed_login_attempts=0,
            )
        )

    async def increment_failed_login(self, user_id: uuid.UUID) -> int:
        """Increment failed login counter and return new count."""
        from sqlalchemy import func
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
        )
        result = await self._session.execute(
            select(User.failed_login_attempts).where(User.id == user_id)
        )
        return result.scalar_one()

    async def email_exists(self, email: str) -> bool:
        """Check if an email is already registered."""
        result = await self._session.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str) -> bool:
        """Check if a username is already taken."""
        result = await self._session.execute(
            select(User.id).where(User.username == username)
        )
        return result.scalar_one_or_none() is not None
