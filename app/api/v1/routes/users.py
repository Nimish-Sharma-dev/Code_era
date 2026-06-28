"""User profile management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.schemas.user import UserResponse, UserUpdateRequest, PasswordChangeRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    dependencies=[Depends(rate_limit_check)],
)
async def get_profile(current_user: CurrentUser):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    dependencies=[Depends(rate_limit_check)],
)
async def update_profile(
    request: UserUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update profile fields. Only provided fields are changed."""
    service = UserService(db_session=db)
    updated = await service.update_user(current_user.id, request)
    return UserResponse.model_validate(updated)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change account password",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db_session=db)
    await service.change_password(current_user.id, request)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete user account",
)
async def delete_account(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db_session=db)
    await service.delete_account(current_user.id)
