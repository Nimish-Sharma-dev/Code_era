"""
Financial entity routes: Wallets, Income, Expenses, Loans, Savings Goals, Investments.
All routes are scoped to the authenticated user — ownership enforced in services.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.graph.graph_service import GraphService
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.schemas.financial import (
    WalletCreate, WalletUpdate, WalletResponse,
    IncomeCreate, IncomeUpdate, IncomeResponse,
    ExpenseCreate, ExpenseResponse,
    LoanCreate, LoanResponse,
    SavingsGoalCreate, SavingsGoalResponse,
    InvestmentCreate, InvestmentResponse,
)
from app.services.financial_service import FinancialService

router = APIRouter(tags=["Finance"], dependencies=[Depends(rate_limit_check)])


def _svc(db: AsyncSession = Depends(get_db)) -> FinancialService:
    return FinancialService(db_session=db)


# ─── Wallets ──────────────────────────────────────────────────────────────────

wallets_router = APIRouter(prefix="/wallets")

@wallets_router.get("", response_model=List[WalletResponse], summary="List all wallets")
async def list_wallets(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_wallets(current_user.id)

@wallets_router.post("", response_model=WalletResponse, status_code=201, summary="Create wallet")
async def create_wallet(
    body: WalletCreate, current_user: CurrentUser,
    svc: FinancialService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    wallet = await svc.create_wallet(current_user.id, body)
    # Sync to graph
    graph = GraphService()
    await graph.upsert_wallet(wallet)
    return wallet

@wallets_router.put("/{wallet_id}", response_model=WalletResponse, summary="Update wallet")
async def update_wallet(
    wallet_id: UUID, body: WalletUpdate,
    current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    return await svc.update_wallet(current_user.id, wallet_id, body)

@wallets_router.delete("/{wallet_id}", status_code=204, summary="Delete wallet")
async def delete_wallet(
    wallet_id: UUID, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    await svc.delete_wallet(current_user.id, wallet_id)


# ─── Income ───────────────────────────────────────────────────────────────────

income_router = APIRouter(prefix="/income")

@income_router.get("", response_model=List[IncomeResponse], summary="List income sources")
async def list_income(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_incomes(current_user.id)

@income_router.post("", response_model=IncomeResponse, status_code=201, summary="Add income source")
async def create_income(
    body: IncomeCreate, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    return await svc.create_income(current_user.id, body)

@income_router.delete("/{income_id}", status_code=204, summary="Remove income source")
async def delete_income(
    income_id: UUID, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    await svc.delete_income(current_user.id, income_id)


# ─── Expenses ─────────────────────────────────────────────────────────────────

expenses_router = APIRouter(prefix="/expenses")

@expenses_router.get("", response_model=List[ExpenseResponse], summary="List expenses")
async def list_expenses(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_expenses(current_user.id)

@expenses_router.post("", response_model=ExpenseResponse, status_code=201, summary="Add expense")
async def create_expense(
    body: ExpenseCreate, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    return await svc.create_expense(current_user.id, body)

@expenses_router.delete("/{expense_id}", status_code=204, summary="Delete expense")
async def delete_expense(
    expense_id: UUID, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    await svc.delete_expense(current_user.id, expense_id)


# ─── Loans ────────────────────────────────────────────────────────────────────

loans_router = APIRouter(prefix="/loans")

@loans_router.get("", response_model=List[LoanResponse], summary="List loans")
async def list_loans(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_loans(current_user.id)

@loans_router.post("", response_model=LoanResponse, status_code=201, summary="Add loan")
async def create_loan(
    body: LoanCreate, current_user: CurrentUser,
    svc: FinancialService = Depends(_svc),
):
    loan = await svc.create_loan(current_user.id, body)
    graph = GraphService()
    await graph.upsert_loan(loan)
    return loan

@loans_router.delete("/{loan_id}", status_code=204, summary="Remove loan")
async def delete_loan(
    loan_id: UUID, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    from app.repositories.financial_repository import LoanRepository
    from app.db.postgres.connection import get_db_session
    async with get_db_session() as db:
        repo = LoanRepository(db)
        loan = await repo.get_by_id(loan_id)
        if loan and loan.user_id == current_user.id:
            from datetime import datetime, timezone
            await repo.update_by_id(loan_id, deleted_at=datetime.now(tz=timezone.utc))


# ─── Savings Goals ────────────────────────────────────────────────────────────

goals_router = APIRouter(prefix="/savings-goals")

@goals_router.get("", response_model=List[SavingsGoalResponse], summary="List savings goals")
async def list_goals(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_goals(current_user.id)

@goals_router.post("", response_model=SavingsGoalResponse, status_code=201, summary="Create savings goal")
async def create_goal(
    body: SavingsGoalCreate, current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    return await svc.create_goal(current_user.id, body)

@goals_router.post("/{goal_id}/contribute", response_model=SavingsGoalResponse, summary="Add contribution")
async def contribute(
    goal_id: UUID, amount: float,
    current_user: CurrentUser, svc: FinancialService = Depends(_svc),
):
    return await svc.contribute_to_goal(current_user.id, goal_id, amount)


# ─── Investments ──────────────────────────────────────────────────────────────

investments_router = APIRouter(prefix="/investments")

@investments_router.get("", response_model=List[InvestmentResponse], summary="List investments")
async def list_investments(current_user: CurrentUser, svc: FinancialService = Depends(_svc)):
    return await svc.get_investments(current_user.id)

@investments_router.post("", response_model=InvestmentResponse, status_code=201, summary="Add investment")
async def create_investment(
    body: InvestmentCreate, current_user: CurrentUser,
    svc: FinancialService = Depends(_svc),
):
    investment = await svc.create_investment(current_user.id, body)
    # Sync asset + user-investment edge to graph
    graph = GraphService()
    await graph.upsert_asset(
        symbol=investment.symbol, name=investment.name,
        asset_type=investment.asset_class.value if hasattr(investment.asset_class, 'value') else investment.asset_class,
        current_price=investment.current_price,
    )
    await graph.link_user_investment(
        user_id=str(current_user.id),
        symbol=investment.symbol,
        quantity=investment.quantity,
        avg_buy_price=investment.average_buy_price,
    )
    return investment


# Register all sub-routers on the main router
router.include_router(wallets_router)
router.include_router(income_router)
router.include_router(expenses_router)
router.include_router(loans_router)
router.include_router(goals_router)
router.include_router(investments_router)
