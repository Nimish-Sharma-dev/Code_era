"""Export all PostgreSQL models for Alembic auto-detection."""

from app.models.postgres.base import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin
from app.models.postgres.user import User, RiskToleranceLevel, UserStatus
from app.models.postgres.financial import (
    Wallet, WalletType,
    Income, IncomeFrequency,
    Expense, ExpenseCategory,
    Loan, LoanStatus, LoanType,
    SavingsGoal,
    Investment, AssetClass,
    CryptoHolding,
    Notification, NotificationType,
)
from app.models.postgres.market import (
    MarketSnapshot,
    NewsArticle, SentimentLabel,
    TechnicalIndicator,
    Prediction, PredictionDirection,
    Recommendation, RecommendationAction,
)

__all__ = [
    "Base",
    "User", "RiskToleranceLevel", "UserStatus",
    "Wallet", "Income", "Expense", "Loan",
    "SavingsGoal", "Investment", "CryptoHolding",
    "Notification",
    "MarketSnapshot", "NewsArticle", "TechnicalIndicator",
    "Prediction", "Recommendation",
]
