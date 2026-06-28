"""
Financial entity repositories: Wallet, Income, Expense, Loan,
SavingsGoal, Investment, CryptoHolding.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres.financial import (
    Wallet, Income, Expense, Loan, SavingsGoal, Investment, CryptoHolding,
    LoanStatus,
)
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Wallet, session)

    async def get_user_wallets(self, user_id: uuid.UUID) -> Sequence[Wallet]:
        result = await self._session.execute(
            select(Wallet)
            .where(and_(Wallet.user_id == user_id, Wallet.deleted_at.is_(None)))
            .order_by(Wallet.is_primary.desc(), Wallet.created_at)
        )
        return result.scalars().all()

    async def get_total_balance(self, user_id: uuid.UUID) -> float:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.coalesce(func.sum(Wallet.balance), 0.0))
            .where(and_(Wallet.user_id == user_id, Wallet.is_active == True, Wallet.deleted_at.is_(None)))
        )
        return float(result.scalar_one())

    async def get_primary_wallet(self, user_id: uuid.UUID) -> Optional[Wallet]:
        result = await self._session.execute(
            select(Wallet).where(
                and_(Wallet.user_id == user_id, Wallet.is_primary == True, Wallet.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()


class IncomeRepository(BaseRepository[Income]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Income, session)

    async def get_user_incomes(self, user_id: uuid.UUID, active_only: bool = True) -> Sequence[Income]:
        query = select(Income).where(Income.user_id == user_id)
        if active_only:
            query = query.where(Income.is_active == True)
        result = await self._session.execute(query.order_by(Income.amount.desc()))
        return result.scalars().all()

    async def get_total_monthly_income(self, user_id: uuid.UUID) -> float:
        """Sum monthly-equivalent income for the user."""
        incomes = await self.get_user_incomes(user_id, active_only=True)
        return sum(i.monthly_equivalent for i in incomes)


class ExpenseRepository(BaseRepository[Expense]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Expense, session)

    async def get_user_expenses(self, user_id: uuid.UUID) -> Sequence[Expense]:
        result = await self._session.execute(
            select(Expense).where(Expense.user_id == user_id)
            .order_by(Expense.amount.desc())
        )
        return result.scalars().all()

    async def get_by_category(self, user_id: uuid.UUID, category: str) -> Sequence[Expense]:
        result = await self._session.execute(
            select(Expense).where(and_(Expense.user_id == user_id, Expense.category == category))
        )
        return result.scalars().all()


class LoanRepository(BaseRepository[Loan]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Loan, session)

    async def get_user_loans(
        self, user_id: uuid.UUID, active_only: bool = True
    ) -> Sequence[Loan]:
        query = select(Loan).where(and_(Loan.user_id == user_id, Loan.deleted_at.is_(None)))
        if active_only:
            query = query.where(Loan.status == LoanStatus.ACTIVE)
        result = await self._session.execute(
            query.order_by(Loan.interest_rate.desc())
        )
        return result.scalars().all()

    async def get_total_debt(self, user_id: uuid.UUID) -> float:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.coalesce(func.sum(Loan.current_balance), 0.0))
            .where(and_(Loan.user_id == user_id, Loan.status == LoanStatus.ACTIVE))
        )
        return float(result.scalar_one())

    async def get_total_monthly_debt_payments(self, user_id: uuid.UUID) -> float:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.coalesce(func.sum(Loan.monthly_payment), 0.0))
            .where(and_(Loan.user_id == user_id, Loan.status == LoanStatus.ACTIVE))
        )
        return float(result.scalar_one())


class SavingsGoalRepository(BaseRepository[SavingsGoal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SavingsGoal, session)

    async def get_user_goals(self, user_id: uuid.UUID) -> Sequence[SavingsGoal]:
        result = await self._session.execute(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == user_id)
            .order_by(SavingsGoal.priority)
        )
        return result.scalars().all()


class InvestmentRepository(BaseRepository[Investment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Investment, session)

    async def get_user_investments(self, user_id: uuid.UUID) -> Sequence[Investment]:
        result = await self._session.execute(
            select(Investment)
            .where(and_(Investment.user_id == user_id, Investment.is_active == True))
            .order_by(Investment.current_value.desc())
        )
        return result.scalars().all()

    async def get_by_symbol(self, user_id: uuid.UUID, symbol: str) -> Optional[Investment]:
        result = await self._session.execute(
            select(Investment).where(
                and_(Investment.user_id == user_id, Investment.symbol == symbol.upper())
            )
        )
        return result.scalar_one_or_none()

    async def get_portfolio_value(self, user_id: uuid.UUID) -> float:
        investments = await self.get_user_investments(user_id)
        return sum(i.current_value for i in investments)
