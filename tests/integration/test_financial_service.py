"""
Integration tests for FinancialService business logic.
Tests use the in-memory SQLite DB from conftest.
"""

from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres.user import User, UserStatus, RiskToleranceLevel
from app.core.security import hash_password, UserRole
from app.schemas.financial import (
    WalletCreate, IncomeCreate, ExpenseCreate,
    LoanCreate, SavingsGoalCreate, InvestmentCreate,
)
from app.services.financial_service import FinancialService


@pytest_asyncio.fixture
async def user_for_financial(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"fin_{uuid.uuid4().hex[:6]}@test.com",
        username=f"fin_{uuid.uuid4().hex[:6]}",
        full_name="Finance Tester",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.USER.value,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        risk_tolerance=RiskToleranceLevel.MODERATE,
        currency="USD",
        timezone="UTC",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_create_and_retrieve_wallet(db_session: AsyncSession, user_for_financial: User):
    svc = FinancialService(db_session=db_session)
    wallet = await svc.create_wallet(
        user_for_financial.id,
        WalletCreate(name="Savings", wallet_type="savings", balance=10000.0)
    )
    assert wallet.id is not None
    wallets = await svc.get_wallets(user_for_financial.id)
    assert any(w.id == wallet.id for w in wallets)


@pytest.mark.asyncio
async def test_financial_summary_calculation(db_session: AsyncSession, user_for_financial: User):
    svc = FinancialService(db_session=db_session)

    await svc.create_wallet(user_for_financial.id,
        WalletCreate(name="Checking", wallet_type="checking", balance=5000.0))
    await svc.create_income(user_for_financial.id,
        IncomeCreate(source="Job", amount=5000.0, frequency="monthly", currency="USD",
                     is_taxable=True, tax_rate=0.22))
    await svc.create_expense(user_for_financial.id,
        ExpenseCreate(name="Rent", amount=1500.0, currency="USD", category="housing",
                      frequency="monthly", is_fixed=True, is_essential=True))
    await svc.create_loan(user_for_financial.id,
        LoanCreate(name="Car", loan_type="auto", principal_amount=20000.0,
                   current_balance=15000.0, interest_rate=4.5,
                   monthly_payment=350.0, remaining_term_months=48))

    summary = await svc.compute_financial_summary(user_for_financial.id)

    assert summary["monthly_income"] == 5000.0
    assert summary["monthly_expenses"] > 0
    assert summary["total_cash"] == 5000.0
    assert summary["total_liabilities"] == 15000.0
    assert "debt_to_income_ratio" in summary
    assert "savings_rate" in summary
    assert "emergency_fund_months" in summary


@pytest.mark.asyncio
async def test_investment_averaging_down(db_session: AsyncSession, user_for_financial: User):
    """Buying same symbol twice should average the price."""
    svc = FinancialService(db_session=db_session)

    inv1 = await svc.create_investment(user_for_financial.id,
        InvestmentCreate(symbol="AAPL", name="Apple", asset_class="equity",
                         quantity=10.0, average_buy_price=150.0))

    inv2 = await svc.create_investment(user_for_financial.id,
        InvestmentCreate(symbol="AAPL", name="Apple", asset_class="equity",
                         quantity=10.0, average_buy_price=130.0))

    # Should be same record, averaged: (10*150 + 10*130) / 20 = 140
    assert abs(inv2.average_buy_price - 140.0) < 0.01
    assert inv2.quantity == 20.0


@pytest.mark.asyncio
async def test_goal_contribution_caps_at_target(db_session: AsyncSession, user_for_financial: User):
    svc = FinancialService(db_session=db_session)

    goal = await svc.create_goal(user_for_financial.id,
        SavingsGoalCreate(name="Vacation", target_amount=3000.0,
                          current_amount=2900.0, priority=2))

    # Contributing more than needed should cap at target
    updated = await svc.contribute_to_goal(user_for_financial.id, goal.id, 500.0)
    assert updated.current_amount == 3000.0
    assert updated.is_completed is True


@pytest.mark.asyncio
async def test_loan_balance_validation(db_session: AsyncSession, user_for_financial: User):
    svc = FinancialService(db_session=db_session)
    from app.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        await svc.create_loan(user_for_financial.id,
            LoanCreate(name="Bad Loan", loan_type="personal",
                       principal_amount=5000.0, current_balance=6000.0,
                       interest_rate=8.0, monthly_payment=200.0,
                       remaining_term_months=36))
