"""
Security utilities: JWT token management, password hashing, and RBAC helpers.

Design decisions:
- Separate access tokens (short-lived) from refresh tokens (long-lived).
- Refresh tokens are stored in Redis to allow server-side revocation.
- Passwords are hashed with bcrypt (cost factor 12).
- All token operations are synchronous (cryptographic ops are CPU-bound).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class TokenType(str, Enum):
    """Distinguishes access tokens from refresh tokens in payload."""

    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str, Enum):
    """Role-based access control roles."""

    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"
    READONLY = "readonly"


# ── Password Utilities ───────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Uses constant-time comparison to prevent timing attacks.
    """
    return _pwd_context.verify(plain, hashed)


# ── Token Creation ───────────────────────────────────────────────────────────


def create_access_token(
    subject: str,
    role: UserRole = UserRole.USER,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: User ID (UUID string).
        role: User's RBAC role.
        extra_claims: Optional additional payload claims.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.jwt.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived refresh token.

    Refresh tokens have a 'jti' that is stored in Redis so they can be
    invalidated server-side on logout or suspicious activity detection.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(days=settings.jwt.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": TokenType.REFRESH.value,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(32),
    }

    return jwt.encode(payload, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


# ── Token Verification ───────────────────────────────────────────────────────


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        JWTError: If the token is invalid, expired, or tampered.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm],
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed", error=str(exc))
        raise


def extract_subject(token: str) -> Optional[str]:
    """Extract the subject (user ID) from a token without raising on error."""
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None


# ── RBAC Helpers ─────────────────────────────────────────────────────────────


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.READONLY: 0,
    UserRole.USER: 1,
    UserRole.ANALYST: 2,
    UserRole.ADMIN: 3,
}


def has_role(user_role: UserRole, required_role: UserRole) -> bool:
    """
    Check if a user's role satisfies a required role level.

    Uses hierarchical comparison: ADMIN > ANALYST > USER > READONLY.
    """
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)


def generate_api_key() -> str:
    """Generate a cryptographically secure API key (48 bytes = 64 base64 chars)."""
    return secrets.token_urlsafe(48)
