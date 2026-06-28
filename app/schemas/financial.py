"""Financial entity schemas: Wallet, Income, Expense, Loan, SavingsGoal."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Wallet ────────────────────────────────────────────────────────────────────

class WalletCreate(BaseModel):
    name: str = Field(..., max_length=100)
    wallet_type: str
    balance: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", max_length=3)
    institution: Optional[str] = Field(None, max_length=100)
    account_number_last4: Optional[str] = Field(None, max_length=4)
    is_primary: bool = False
    notes: Optional[str] = None


class WalletUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    balance: Optional[float] = Field(None, ge=0)
    is_primary: Optional[bool] = None
    notes: Optional[str] = None


class WalletResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    wallet_type: str
    balance: float
    currency: str
    institution: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime


# ── Income ────────────────────────────────────────────────────────────────────

class IncomeCreate(BaseModel):
    source: str = Field(..., max_length=200)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    frequency: str
    is_taxable: bool = True
    tax_rate: float = Field(default=0.0, ge=0, le=1)
    description: Optional[str] = None


class IncomeUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


class IncomeResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    source: str
    amount: float
    currency: str
    frequency: str
    is_taxable: bool
    tax_rate: float
    is_active: bool
    monthly_equivalent: float
    created_at: datetime


# ── Expense ───────────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    name: str = Field(..., max_length=200)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    category: str
    frequency: str
    is_fixed: bool = True
    is_essential: bool = True
    merchant: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    amount: float
    currency: str
    category: str
    frequency: str
    is_fixed: bool
    is_essential: bool
    created_at: datetime


# ── Loan ─────────────────────────────────────────────────────────────────────

class LoanCreate(BaseModel):
    name: str = Field(..., max_length=200)
    loan_type: str
    principal_amount: float = Field(..., gt=0)
    current_balance: float = Field(..., ge=0)
    interest_rate: float = Field(..., ge=0, le=100)
    monthly_payment: float = Field(..., gt=0)
    remaining_term_months: int = Field(..., gt=0)
    lender: Optional[str] = Field(None, max_length=100)
    is_tax_deductible: bool = False
    notes: Optional[str] = None


class LoanResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    loan_type: str
    principal_amount: float
    current_balance: float
    interest_rate: float
    monthly_payment: float
    remaining_term_months: int
    lender: Optional[str]
    status: str
    total_interest_remaining: float
    created_at: datetime


# ── Savings Goal ──────────────────────────────────────────────────────────────

class SavingsGoalCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(default=0.0, ge=0)
    target_date: Optional[str] = None
    monthly_contribution: float = Field(default=0.0, ge=0)
    priority: int = Field(default=1, ge=1, le=10)


class SavingsGoalResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    target_date: Optional[str]
    monthly_contribution: float
    priority: int
    progress_percent: float
    is_completed: bool
    created_at: datetime


# ── Investment ────────────────────────────────────────────────────────────────

class InvestmentCreate(BaseModel):
    symbol: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    asset_class: str
    quantity: float = Field(..., gt=0)
    average_buy_price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    exchange: Optional[str] = Field(None, max_length=20)
    sector: Optional[str] = Field(None, max_length=50)


class InvestmentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    symbol: str
    name: str
    asset_class: str
    quantity: float
    average_buy_price: float
    current_price: float
    currency: str
    cost_basis: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    created_at: datetime
