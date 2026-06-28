"""
User domain model.

Stores authentication credentials, profile data, and risk preferences.
Sensitive fields are never returned in API responses (see schemas/).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.postgres.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class RiskToleranceLevel(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core user entity.

    Relationships are lazy-loaded by default; use selectinload() or
    joinedload() in queries where relations are needed to avoid N+1.
    """

    __tablename__ = "users"

    # ── Identity ─────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Auth ──────────────────────────────────────────────────────────────────
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False
    )
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # ── Financial Profile ─────────────────────────────────────────────────────
    risk_tolerance: Mapped[RiskToleranceLevel] = mapped_column(
        Enum(RiskToleranceLevel), default=RiskToleranceLevel.MODERATE
    )
    monthly_income_target: Mapped[float] = mapped_column(Float, default=0.0)
    emergency_fund_months_target: Mapped[int] = mapped_column(Integer, default=6)
    financial_health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # ── Relationships ─────────────────────────────────────────────────────────
    wallets: Mapped[list["Wallet"]] = relationship(
        "Wallet", back_populates="user", cascade="all, delete-orphan"
    )
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="user", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="user", cascade="all, delete-orphan"
    )
    loans: Mapped[list["Loan"]] = relationship(
        "Loan", back_populates="user", cascade="all, delete-orphan"
    )
    savings_goals: Mapped[list["SavingsGoal"]] = relationship(
        "SavingsGoal", back_populates="user", cascade="all, delete-orphan"
    )
    investments: Mapped[list["Investment"]] = relationship(
        "Investment", back_populates="user", cascade="all, delete-orphan"
    )
    crypto_holdings: Mapped[list["CryptoHolding"]] = relationship(
        "CryptoHolding", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
