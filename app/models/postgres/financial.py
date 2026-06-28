"""
Financial domain models: Wallet, Income, Expense, Loan, SavingsGoal,
Investment, CryptoHolding, Notification.

All monetary values are stored as Float (USD by default) — in a real
production system consider using Numeric(precision=20, scale=8) to avoid
floating-point rounding errors for financial calculations.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.postgres.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


# ── Enumerations ──────────────────────────────────────────────────────────────

class WalletType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    CRYPTO = "crypto"
    CASH = "cash"
    CREDIT = "credit"


class IncomeFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


class ExpenseCategory(str, enum.Enum):
    HOUSING = "housing"
    FOOD = "food"
    TRANSPORT = "transport"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    CLOTHING = "clothing"
    PERSONAL = "personal"
    SAVINGS = "savings"
    DEBT_PAYMENT = "debt_payment"
    INSURANCE = "insurance"
    INVESTMENT = "investment"
    OTHER = "other"


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted"
    DEFERRED = "deferred"


class LoanType(str, enum.Enum):
    MORTGAGE = "mortgage"
    AUTO = "auto"
    STUDENT = "student"
    PERSONAL = "personal"
    CREDIT_CARD = "credit_card"
    BUSINESS = "business"
    PAYDAY = "payday"
    OTHER = "other"


class AssetClass(str, enum.Enum):
    EQUITY = "equity"
    BOND = "bond"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    REIT = "reit"
    COMMODITY = "commodity"
    ALTERNATIVE = "alternative"


class NotificationType(str, enum.Enum):
    ALERT = "alert"
    RECOMMENDATION = "recommendation"
    MARKET_EVENT = "market_event"
    GOAL_MILESTONE = "goal_milestone"
    RISK_WARNING = "risk_warning"
    SENTIMENT_ALERT = "sentiment_alert"
    DEBT_REMINDER = "debt_reminder"


# ── Models ────────────────────────────────────────────────────────────────────

class Wallet(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User's financial accounts/wallets."""

    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    wallet_type: Mapped[WalletType] = mapped_column(Enum(WalletType), nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    institution: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_number_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="wallets")


class Income(Base, UUIDMixin, TimestampMixin):
    """Recurring or one-time income sources."""

    __tablename__ = "incomes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    frequency: Mapped[IncomeFrequency] = mapped_column(Enum(IncomeFrequency), nullable=False)
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def monthly_equivalent(self) -> float:
        """Normalize income to monthly equivalent."""
        multipliers = {
            IncomeFrequency.DAILY: 30,
            IncomeFrequency.WEEKLY: 4.33,
            IncomeFrequency.BIWEEKLY: 2.17,
            IncomeFrequency.MONTHLY: 1,
            IncomeFrequency.QUARTERLY: 1 / 3,
            IncomeFrequency.ANNUAL: 1 / 12,
            IncomeFrequency.ONE_TIME: 0,
        }
        return self.amount * multipliers.get(self.frequency, 1)

    user: Mapped["User"] = relationship("User", back_populates="incomes")


class Expense(Base, UUIDMixin, TimestampMixin):
    """Tracked expenses with category and recurrence."""

    __tablename__ = "expenses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), nullable=False)
    frequency: Mapped[IncomeFrequency] = mapped_column(Enum(IncomeFrequency), nullable=False)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=True)
    merchant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="expenses")


class Loan(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Debt/loan tracking with amortization support."""

    __tablename__ = "loans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType), nullable=False)
    principal_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_balance: Mapped[float] = mapped_column(Float, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)  # Annual %
    monthly_payment: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    lender: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), default=LoanStatus.ACTIVE)
    is_tax_deductible: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def total_interest_remaining(self) -> float:
        """Approximate total interest remaining (simple calculation)."""
        return (self.monthly_payment * self.remaining_term_months) - self.current_balance

    user: Mapped["User"] = relationship("User", back_populates="loans")


class SavingsGoal(Base, UUIDMixin, TimestampMixin):
    """Named savings goals with target amounts and deadlines."""

    __tablename__ = "savings_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0)
    target_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO date
    monthly_contribution: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=highest
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def progress_percent(self) -> float:
        if self.target_amount == 0:
            return 0.0
        return min((self.current_amount / self.target_amount) * 100, 100.0)

    user: Mapped["User"] = relationship("User", back_populates="savings_goals")


class Investment(Base, UUIDMixin, TimestampMixin):
    """Stock/ETF/bond investment holdings."""

    __tablename__ = "investments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.average_buy_price

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.current_value - self.cost_basis

    @property
    def unrealized_pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    user: Mapped["User"] = relationship("User", back_populates="investments")


class CryptoHolding(Base, UUIDMixin, TimestampMixin):
    """Cryptocurrency holdings."""

    __tablename__ = "crypto_holdings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_buy_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    current_price_usd: Mapped[float] = mapped_column(Float, default=0.0)
    wallet_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_staked: Mapped[bool] = mapped_column(Boolean, default=False)
    staking_apy: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship("User", back_populates="crypto_holdings")


class Notification(Base, UUIDMixin, TimestampMixin):
    """User notifications from various platform engines."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    user: Mapped["User"] = relationship("User", back_populates="notifications")
