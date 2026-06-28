"""
FastAPI dependencies for authentication, authorisation, and rate limiting.

These are injected into route handlers via Depends().
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import UserRole, decode_token, has_role
from app.core.exceptions import AuthenticationError, AuthorizationError, RateLimitError
from app.core.logging import get_logger
from app.db.postgres.connection import get_db
from app.db.postgres.redis_client import CacheManager, get_cache_manager
from app.repositories.user_repository import UserRepository
from app.models.postgres.user import User, UserStatus
from app.config.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: decode JWT and return the authenticated User.

    Raises HTTP 401 if token is missing, invalid, or expired.
    Raises HTTP 403 if user account is suspended/deleted.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id_str))

    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="User not found")

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Account suspended")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Alias dependency ensuring user is active (not just authenticated)."""
    return current_user


def require_role(required_role: UserRole):
    """
    Factory that returns a dependency enforcing a minimum role level.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = UserRole(current_user.role) if current_user.role in [r.value for r in UserRole] else UserRole.USER
        if not has_role(user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role.value}",
            )
        return current_user
    return role_checker


async def rate_limit_check(
    current_user: User = Depends(get_current_user),
    cache: CacheManager = Depends(get_cache_manager),
) -> None:
    """
    Per-user rate limiting dependency.

    Limits to settings.rate_limit_per_minute requests per 60s window.
    Uses Redis atomic increment for accuracy under concurrent load.
    """
    allowed, count = await cache.check_rate_limit(
        identifier=f"user:{current_user.id}",
        limit=settings.rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {settings.rate_limit_per_minute}/minute",
            headers={"Retry-After": "60"},
        )


# Convenience type aliases for route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
