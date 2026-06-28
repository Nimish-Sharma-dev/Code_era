"""Integration tests for authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "SecurePass123",
        "currency": "USD",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert "hashed_password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@example.com", "username": "user1",
        "full_name": "User One", "password": "SecurePass123",
    }
    await client.post("/api/v1/auth/register", json=payload)
    payload["username"] = "user2"
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com", "username": "weakuser",
        "full_name": "Weak User", "password": "weak",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "username": "loginuser",
        "full_name": "Login User", "password": "LoginPass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "LoginPass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "auth2@example.com", "username": "authuser2",
        "full_name": "Auth User", "password": "CorrectPass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "auth2@example.com", "password": "WrongPass999",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_check_public(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
