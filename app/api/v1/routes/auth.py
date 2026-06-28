"""Authentication API routes: register, login, refresh, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.db.postgres.redis_client import CacheManager, get_cache_manager
from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest, UserResponse,
    TokenResponse, RefreshTokenRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache_manager),
) -> AuthService:
    return AuthService(db_session=db, cache=cache)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    request: UserRegisterRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """
    Create a new user account.

    - Validates email/username uniqueness.
    - Hashes the password with bcrypt.
    - Returns the created user profile (no tokens — requires separate login).
    """
    user = await auth_service.register(request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT token pair",
)
async def login(
    request: UserLoginRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """
    Authenticate with email and password.

    Returns an access token (short-lived) and refresh token (long-lived).
    Use the access token in the Authorization: Bearer <token> header.
    """
    return await auth_service.login(request.email, request.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Obtain a new access token using a refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """
    Exchange a valid refresh token for a new access token.

    Refresh tokens are stored server-side in Redis and can be revoked.
    """
    return await auth_service.refresh_access_token(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token and invalidate session",
)
async def logout(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """
    Revoke the provided refresh token.

    The access token will expire naturally after its configured TTL.
    """
    await auth_service.logout(request.refresh_token)
