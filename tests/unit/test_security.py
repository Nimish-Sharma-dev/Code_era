"""Unit tests for JWT token creation and password hashing."""

from __future__ import annotations

import pytest
from jose import JWTError

from app.core.security import (
    UserRole, create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password, has_role,
)


def test_password_hash_and_verify():
    plain = "MySecurePass123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPass", hashed)


def test_password_different_hashes_same_input():
    """Bcrypt salt ensures same input produces different hashes."""
    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2
    assert verify_password("same_password", h1)
    assert verify_password("same_password", h2)


def test_access_token_creation_and_decode():
    user_id = "test-user-123"
    token = create_access_token(user_id, role=UserRole.USER)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "user"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_refresh_token_type():
    token = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_role_hierarchy():
    assert has_role(UserRole.ADMIN, UserRole.USER)
    assert has_role(UserRole.ADMIN, UserRole.ADMIN)
    assert has_role(UserRole.ANALYST, UserRole.USER)
    assert not has_role(UserRole.USER, UserRole.ADMIN)
    assert not has_role(UserRole.READONLY, UserRole.USER)
