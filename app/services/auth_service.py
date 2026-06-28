"""
Authentication service: registration, login, token management, logout.

Business logic lives here; the repository handles persistence;
routes handle HTTP concerns only.
"""

from __future__ import annotations

from datetime import timedelta, timezone, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError, ConflictError, NotFoundError, AuthorizationError
)
from app.core.security import (
    UserRole, create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password,
)
from app.core.logging import get_logger
from app.db.postgres.redis_client import CacheManager
from app.models.postgres.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRegisterRequest, TokenResponse
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)

MAX_FAILED_LOGINS = 5


class AuthService:
    """
    Handles all authentication workflows.

    Injected dependencies:
        db_session: Active async database session.
        cache: Redis cache manager for token storage.
    """

    def __init__(self, db_session: AsyncSession, cache: CacheManager) -> None:
        self._repo = UserRepository(db_session)
        self._cache = cache
        self._session = db_session

    async def register(self, request: UserRegisterRequest) -> User:
        """
        Register a new user.

        Validates email/username uniqueness, hashes the password,
        and persists the user. Syncs to Neo4j graph asynchronously.
        """
        if await self._repo.email_exists(request.email):
            raise ConflictError(f"Email '{request.email}' is already registered")

        if await self._repo.username_exists(request.username):
            raise ConflictError(f"Username '{request.username}' is already taken")

        user = await self._repo.create(
            email=request.email.lower().strip(),
            username=request.username,
            full_name=request.full_name,
            phone=request.phone,
            hashed_password=hash_password(request.password),
            currency=request.currency,
            role=UserRole.USER.value,
            status=UserStatus.ACTIVE,  # In prod: PENDING_VERIFICATION until email confirmed
            is_email_verified=False,
        )

        logger.info("User registered", user_id=str(user.id), email=user.email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and issue JWT token pair.

        Implements account lockout after MAX_FAILED_LOGINS attempts.
        """
        user = await self._repo.get_by_email(email)
        if not user:
            # Constant-time response to prevent user enumeration
            verify_password("dummy", hash_password("dummy"))
            raise AuthenticationError("Invalid email or password")

        if user.failed_login_attempts >= MAX_FAILED_LOGINS:
            raise AuthorizationError(
                "Account locked due to too many failed login attempts. "
                "Contact support to unlock."
            )

        if user.status == UserStatus.SUSPENDED:
            raise AuthorizationError("Account suspended. Contact support.")

        if not verify_password(password, user.hashed_password):
            await self._repo.increment_failed_login(user.id)
            raise AuthenticationError("Invalid email or password")

        # Successful auth
        await self._repo.record_login(user.id)

        role = UserRole(user.role) if user.role in [r.value for r in UserRole] else UserRole.USER
        access_token = create_access_token(str(user.id), role=role)
        refresh_token = create_refresh_token(str(user.id))

        # Decode refresh token to get JTI for Redis storage
        refresh_payload = decode_token(refresh_token)
        jti = refresh_payload["jti"]
        ttl_seconds = settings.jwt.refresh_token_expire_days * 86400
        await self._cache.set_token(jti, str(user.id), ttl=ttl_seconds)

        logger.info("User logged in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt.access_token_expire_minutes * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Issue a new access token from a valid refresh token.

        Verifies the token signature AND confirms the JTI is in Redis
        (server-side validity check).
        """
        from jose import JWTError
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise AuthenticationError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        jti = payload.get("jti")
        if not jti or not await self._cache.is_token_valid(jti):
            raise AuthenticationError("Refresh token has been revoked")

        user_id = payload["sub"]
        user = await self._repo.get_by_id(__import__("uuid").UUID(user_id))
        if not user or user.status != UserStatus.ACTIVE:
            raise AuthenticationError("User not found or inactive")

        role = UserRole(user.role) if user.role in [r.value for r in UserRole] else UserRole.USER
        new_access_token = create_access_token(user_id, role=role)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,  # Reuse existing refresh token
            token_type="bearer",
            expires_in=settings.jwt.access_token_expire_minutes * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        """
        Revoke a refresh token by removing its JTI from Redis.

        The access token will expire naturally (no server-side revocation
        needed since access tokens are short-lived).
        """
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await self._cache.revoke_token(jti)
                logger.info("Refresh token revoked", jti=jti)
        except Exception:
            # Silently ignore invalid tokens on logout
            pass
