"""User profile management service."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password, verify_password
from app.core.logging import get_logger
from app.models.postgres.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdateRequest, PasswordChangeRequest

logger = get_logger(__name__)


class UserService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._repo = UserRepository(db_session)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def update_user(self, user_id: uuid.UUID, request: UserUpdateRequest) -> User:
        user = await self.get_user(user_id)
        update_data = request.model_dump(exclude_none=True)
        updated = await self._repo.update_by_id(user_id, **update_data)
        logger.info("User profile updated", user_id=str(user_id))
        return updated

    async def change_password(
        self, user_id: uuid.UUID, request: PasswordChangeRequest
    ) -> None:
        user = await self.get_user(user_id)
        if not verify_password(request.current_password, user.hashed_password):
            raise ValidationError("Current password is incorrect", field="current_password")
        await self._repo.update_by_id(
            user_id, hashed_password=hash_password(request.new_password)
        )
        logger.info("Password changed", user_id=str(user_id))

    async def delete_account(self, user_id: uuid.UUID) -> None:
        """Soft-delete user account."""
        from datetime import datetime, timezone
        await self._repo.update_by_id(
            user_id,
            deleted_at=datetime.now(tz=timezone.utc),
            status="inactive",
        )
        logger.info("User account soft-deleted", user_id=str(user_id))
