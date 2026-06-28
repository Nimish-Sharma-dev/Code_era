"""Integration tests for financial entity endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_wallet(client: AsyncClient, auth_headers: dict):
    # Create
    resp = await client.post("/api/v1/wallets", headers=auth_headers, json={
        "name": "Main Checking",
        "wallet_type": "checking",
        "balance": 5000.0,
        "currency": "USD",
        "is_primary": True,
    })
    assert resp.status_code == 201
    wallet = resp.json()
    assert wallet["name"] == "Main Checking"
    assert wallet["balance"] == 5000.0

    # List
    resp = await client.get("/api/v1/wallets", headers=auth_headers)
    assert resp.status_code == 200
    wallets = resp.json()
    assert len(wallets) >= 1


@pytest.mark.asyncio
async def test_create_loan_validates_balance(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/loans", headers=auth_headers, json={
        "name": "Personal Loan",
        "loan_type": "personal",
        "principal_amount": 5000.0,
        "current_balance": 9999.0,  # Exceeds principal — should fail
        "interest_rate": 8.5,
        "monthly_payment": 200.0,
        "remaining_term_months": 36,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_valid_loan(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/loans", headers=auth_headers, json={
        "name": "Student Loan",
        "loan_type": "student",
        "principal_amount": 30000.0,
        "current_balance": 22000.0,
        "interest_rate": 5.5,
        "monthly_payment": 300.0,
        "remaining_term_months": 84,
    })
    assert resp.status_code == 201
    loan = resp.json()
    assert loan["interest_rate"] == 5.5
    assert "total_interest_remaining" in loan


@pytest.mark.asyncio
async def test_savings_goal_contribution(client: AsyncClient, auth_headers: dict):
    # Create goal
    resp = await client.post("/api/v1/savings-goals", headers=auth_headers, json={
        "name": "Emergency Fund",
        "target_amount": 12000.0,
        "current_amount": 3000.0,
        "priority": 1,
    })
    assert resp.status_code == 201
    goal_id = resp.json()["id"]

    # Contribute
    resp = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        headers=auth_headers,
        params={"amount": 500.0},
    )
    assert resp.status_code == 200
    assert resp.json()["current_amount"] == 3500.0


@pytest.mark.asyncio
async def test_income_monthly_equivalent(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/income", headers=auth_headers, json={
        "source": "Salary",
        "amount": 100000.0,
        "frequency": "annual",
        "currency": "USD",
        "is_taxable": True,
        "tax_rate": 0.25,
    })
    assert resp.status_code == 201
    income = resp.json()
    # Annual $100k / 12 = ~$8333/month
    assert abs(income["monthly_equivalent"] - 8333.33) < 1
