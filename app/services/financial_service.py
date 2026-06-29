"""
Financial entity management service.

Orchestrates CRUD for wallets, income, expenses, loans, savings goals,
and investments. Also computes derived financial metrics.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, AuthorizationError, ValidationError
from app.core.logging import get_logger
from app.repositories.financial_repository import (
    WalletRepository, IncomeRepository, ExpenseRepository,
    LoanRepository, SavingsGoalRepository, InvestmentRepository,
)
from app.schemas.financial import (
    WalletCreate, WalletUpdate,
    IncomeCreate, IncomeUpdate,
    ExpenseCreate,
    LoanCreate,
    SavingsGoalCreate,
    InvestmentCreate,
)
from app.models.postgres.financial import (
    Wallet, Income, Expense, Loan, SavingsGoal, Investment
)

logger = get_logger(__name__)


class FinancialService:
    """
    Unified service for all financial entity operations.

    All ownership checks are enforced here — a user can only access
    their own financial data.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._wallet_repo = WalletRepository(db_session)
        self._income_repo = IncomeRepository(db_session)
        self._expense_repo = ExpenseRepository(db_session)
        self._loan_repo = LoanRepository(db_session)
        self._goal_repo = SavingsGoalRepository(db_session)
        self._investment_repo = InvestmentRepository(db_session)

    # ── Wallet ────────────────────────────────────────────────────────────────

    async def create_wallet(self, user_id: uuid.UUID, data: WalletCreate) -> Wallet:
        return await self._wallet_repo.create(user_id=user_id, **data.model_dump())

    async def get_wallets(self, user_id: uuid.UUID) -> Sequence[Wallet]:
        return await self._wallet_repo.get_user_wallets(user_id)

    async def update_wallet(
        self, user_id: uuid.UUID, wallet_id: uuid.UUID, data: WalletUpdate
    ) -> Wallet:
        wallet = await self._wallet_repo.get_by_id(wallet_id)
        if not wallet or wallet.user_id != user_id:
            raise NotFoundError("Wallet", wallet_id)
        return await self._wallet_repo.update_by_id(wallet_id, **data.model_dump(exclude_none=True))

    async def delete_wallet(self, user_id: uuid.UUID, wallet_id: uuid.UUID) -> None:
        wallet = await self._wallet_repo.get_by_id(wallet_id)
        if not wallet or wallet.user_id != user_id:
            raise NotFoundError("Wallet", wallet_id)
        from datetime import datetime, timezone
        await self._wallet_repo.update_by_id(wallet_id, deleted_at=datetime.now(tz=timezone.utc))

    # ── Income ────────────────────────────────────────────────────────────────

    async def create_income(self, user_id: uuid.UUID, data: IncomeCreate) -> Income:
        return await self._income_repo.create(user_id=user_id, **data.model_dump())

    async def get_incomes(self, user_id: uuid.UUID) -> Sequence[Income]:
        return await self._income_repo.get_user_incomes(user_id)

    async def delete_income(self, user_id: uuid.UUID, income_id: uuid.UUID) -> None:
        income = await self._income_repo.get_by_id(income_id)
        if not income or income.user_id != user_id:
            raise NotFoundError("Income", income_id)
        await self._income_repo.update_by_id(income_id, is_active=False)

    # ── Expenses ──────────────────────────────────────────────────────────────

    async def create_expense(self, user_id: uuid.UUID, data: ExpenseCreate) -> Expense:
        return await self._expense_repo.create(user_id=user_id, **data.model_dump())

    async def get_expenses(self, user_id: uuid.UUID) -> Sequence[Expense]:
        return await self._expense_repo.get_user_expenses(user_id)

    async def delete_expense(self, user_id: uuid.UUID, expense_id: uuid.UUID) -> None:
        expense = await self._expense_repo.get_by_id(expense_id)
        if not expense or expense.user_id != user_id:
            raise NotFoundError("Expense", expense_id)
        await self._expense_repo.delete_by_id(expense_id)

    # ── Loans ────────────────────────────────────────────────────────────────

    async def create_loan(self, user_id: uuid.UUID, data: LoanCreate) -> Loan:
        if data.current_balance > data.principal_amount:
            raise ValidationError("Current balance cannot exceed principal amount")
        return await self._loan_repo.create(user_id=user_id, **data.model_dump())

    async def get_loans(self, user_id: uuid.UUID) -> Sequence[Loan]:
        return await self._loan_repo.get_user_loans(user_id)

    async def get_total_monthly_debt_payment(self, user_id: uuid.UUID) -> float:
        return await self._loan_repo.get_total_monthly_debt_payments(user_id)

    # ── Savings Goals ─────────────────────────────────────────────────────────

    async def create_goal(self, user_id: uuid.UUID, data: SavingsGoalCreate) -> SavingsGoal:
        return await self._goal_repo.create(user_id=user_id, **data.model_dump())

    async def get_goals(self, user_id: uuid.UUID) -> Sequence[SavingsGoal]:
        return await self._goal_repo.get_user_goals(user_id)

    async def contribute_to_goal(
        self, user_id: uuid.UUID, goal_id: uuid.UUID, amount: float
    ) -> SavingsGoal:
        goal = await self._goal_repo.get_by_id(goal_id)
        if not goal or goal.user_id != user_id:
            raise NotFoundError("SavingsGoal", goal_id)
        new_amount = min(goal.current_amount + amount, goal.target_amount)
        is_completed = new_amount >= goal.target_amount
        return await self._goal_repo.update_by_id(
            goal_id, current_amount=new_amount, is_completed=is_completed
        )

    # ── Investments ───────────────────────────────────────────────────────────

    async def create_investment(self, user_id: uuid.UUID, data: InvestmentCreate) -> Investment:
        existing = await self._investment_repo.get_by_symbol(user_id, data.symbol)
        if existing:
            # Average down / up logic
            total_cost = existing.cost_basis + (data.quantity * data.average_buy_price)
            total_qty = existing.quantity + data.quantity
            new_avg = total_cost / total_qty
            return await self._investment_repo.update_by_id(
                existing.id, quantity=total_qty, average_buy_price=new_avg
            )
        return await self._investment_repo.create(
            user_id=user_id, **data.model_dump()
        )

    async def get_investments(self, user_id: uuid.UUID) -> Sequence[Investment]:
        return await self._investment_repo.get_user_investments(user_id)

    # ── Aggregate Metrics ─────────────────────────────────────────────────────

    async def compute_financial_summary(self, user_id: uuid.UUID) -> Dict:
        """
        Compute key financial metrics for dashboard and ML features.

        Returns a structured dict of financial health indicators.
        """
        total_cash = await self._wallet_repo.get_total_balance(user_id)
        monthly_income = await self._income_repo.get_total_monthly_income(user_id)
        total_debt = await self._loan_repo.get_total_debt(user_id)
        monthly_debt = await self._loan_repo.get_total_monthly_debt_payments(user_id)
        portfolio_value = await self._investment_repo.get_portfolio_value(user_id)

        expenses = await self._expense_repo.get_user_expenses(user_id)
        monthly_expenses = sum(
            e.amount if e.frequency == "monthly" else e.amount / 12
            for e in expenses
        )

        monthly_savings = monthly_income - monthly_expenses - monthly_debt
        savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0
        dti_ratio = (monthly_debt / monthly_income) if monthly_income > 0 else 0
        emergency_fund_months = total_cash / monthly_expenses if monthly_expenses > 0 else 0
        net_worth = total_cash + portfolio_value - total_debt

        return {
            "net_worth": net_worth,
            "total_assets": total_cash + portfolio_value,
            "total_liabilities": total_debt,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_savings": monthly_savings,
            "monthly_debt": monthly_debt,
            "savings_rate": savings_rate,
            "debt_to_income_ratio": dti_ratio,
            "emergency_fund_months": emergency_fund_months,
            "investment_value": portfolio_value,
            "total_cash": total_cash,
        }
