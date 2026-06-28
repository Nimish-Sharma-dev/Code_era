"""
Generic async repository base implementing the Repository pattern.

Provides CRUD operations with type safety via generics.
Domain repositories extend this with domain-specific query methods.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing CRUD for any SQLAlchemy model.

    Args:
        model: The SQLAlchemy model class this repository manages.
        session: An active async database session.
    """

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def create(self, **kwargs: Any) -> ModelT:
        """Persist a new model instance."""
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelT]:
        """Fetch a single record by primary key."""
        result = await self._session.execute(
            select(self._model).where(self._model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[ModelT]:
        """Fetch paginated records."""
        result = await self._session.execute(
            select(self._model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def update_by_id(
        self, record_id: uuid.UUID, **kwargs: Any
    ) -> Optional[ModelT]:
        """Update fields on an existing record by ID."""
        # Filter out None values to allow partial updates
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return await self.get_by_id(record_id)

        await self._session.execute(
            update(self._model)
            .where(self._model.id == record_id)
            .values(**update_data)
        )
        return await self.get_by_id(record_id)

    async def delete_by_id(self, record_id: uuid.UUID) -> bool:
        """Hard-delete a record by primary key."""
        result = await self._session.execute(
            delete(self._model).where(self._model.id == record_id)
        )
        return result.rowcount > 0

    async def count(self) -> int:
        """Return total count of records."""
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.count()).select_from(self._model)
        )
        return result.scalar_one()
