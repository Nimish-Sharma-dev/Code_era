"""Notifications API routes."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"], dependencies=[Depends(rate_limit_check)])


@router.get("", summary="Get user notifications")
async def list_notifications(
    unread_only: bool = Query(default=False),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    notifications = await svc.get_notifications(current_user.id, unread_only=unread_only)
    return [
        {
            "id": str(n.id), "type": str(n.notification_type.value if hasattr(n.notification_type, 'value') else n.notification_type),
            "title": n.title, "message": n.message,
            "is_read": n.is_read, "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.patch("/{notification_id}/read", status_code=204, summary="Mark notification as read")
async def mark_read(
    notification_id: UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.mark_read(notification_id)
