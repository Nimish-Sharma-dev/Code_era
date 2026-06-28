"""Reusable pagination utilities."""
from __future__ import annotations
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    offset: int
    limit: int
    has_next: bool

    @classmethod
    def build(cls, items: List[T], total: int, offset: int, limit: int):
        return cls(
            items=items, total=total, offset=offset,
            limit=limit, has_next=(offset + limit) < total,
        )
