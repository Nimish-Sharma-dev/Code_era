"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), default="user"),
        sa.Column("status", sa.String(30), default="active"),
        sa.Column("is_email_verified", sa.Boolean, default=False),
        sa.Column("is_two_factor_enabled", sa.Boolean, default=False),
        sa.Column("two_factor_secret", sa.String(100)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_attempts", sa.Integer, default=0),
        sa.Column("risk_tolerance", sa.String(20), default="moderate"),
        sa.Column("monthly_income_target", sa.Float, default=0.0),
        sa.Column("emergency_fund_months_target", sa.Integer, default=6),
        sa.Column("financial_health_score", sa.Float),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("timezone", sa.String(50), default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # Wallets
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("wallet_type", sa.String(20), nullable=False),
        sa.Column("balance", sa.Float, default=0.0),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("institution", sa.String(100)),
        sa.Column("account_number_last4", sa.String(4)),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    # Incomes
    op.create_table(
        "incomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("is_taxable", sa.Boolean, default=True),
        sa.Column("tax_rate", sa.Float, default=0.0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Expenses
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("is_fixed", sa.Boolean, default=True),
        sa.Column("is_essential", sa.Boolean, default=True),
        sa.Column("merchant", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Loans
    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("loan_type", sa.String(20), nullable=False),
        sa.Column("principal_amount", sa.Float, nullable=False),
        sa.Column("current_balance", sa.Float, nullable=False),
        sa.Column("interest_rate", sa.Float, nullable=False),
        sa.Column("monthly_payment", sa.Float, nullable=False),
        sa.Column("remaining_term_months", sa.Integer, nullable=False),
        sa.Column("lender", sa.String(100)),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("is_tax_deductible", sa.Boolean, default=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # Savings Goals
    op.create_table(
        "savings_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("target_amount", sa.Float, nullable=False),
        sa.Column("current_amount", sa.Float, default=0.0),
        sa.Column("target_date", sa.String(10)),
        sa.Column("monthly_contribution", sa.Float, default=0.0),
        sa.Column("priority", sa.Integer, default=1),
        sa.Column("is_completed", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Investments
    op.create_table(
        "investments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("average_buy_price", sa.Float, nullable=False),
        sa.Column("current_price", sa.Float, default=0.0),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("exchange", sa.String(20)),
        sa.Column("sector", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_investments_symbol", "investments", ["symbol"])

    # Crypto Holdings
    op.create_table(
        "crypto_holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("average_buy_price_usd", sa.Float, nullable=False),
        sa.Column("current_price_usd", sa.Float, default=0.0),
        sa.Column("wallet_address", sa.String(200)),
        sa.Column("exchange", sa.String(50)),
        sa.Column("is_staked", sa.Boolean, default=False),
        sa.Column("staking_apy", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, default=False),
        sa.Column("metadata", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # Market Snapshots
    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("asset_type", sa.String(20), default="equity"),
        sa.Column("open_price", sa.Float, nullable=False),
        sa.Column("high_price", sa.Float, nullable=False),
        sa.Column("low_price", sa.Float, nullable=False),
        sa.Column("close_price", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column("market_cap", sa.Float),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_market_snapshots_symbol", "market_snapshots", ["symbol"])

    # News Articles
    op.create_table(
        "news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("url", sa.String(2000), nullable=False, unique=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("published_at", sa.String(30), nullable=False),
        sa.Column("related_symbols", sa.Text),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("sentiment_score", sa.Float),
        sa.Column("positive_score", sa.Float),
        sa.Column("negative_score", sa.Float),
        sa.Column("neutral_score", sa.Float),
        sa.Column("embedding_stored", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Technical Indicators
    op.create_table(
        "technical_indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), default="1D"),
        sa.Column("sma_20", sa.Float), sa.Column("sma_50", sa.Float), sa.Column("sma_200", sa.Float),
        sa.Column("ema_12", sa.Float), sa.Column("ema_26", sa.Float),
        sa.Column("rsi_14", sa.Float), sa.Column("macd", sa.Float),
        sa.Column("macd_signal", sa.Float), sa.Column("macd_histogram", sa.Float),
        sa.Column("atr_14", sa.Float), sa.Column("bollinger_upper", sa.Float),
        sa.Column("bollinger_lower", sa.Float), sa.Column("volume_sma_20", sa.Float),
        sa.Column("obv", sa.Float), sa.Column("fear_greed_index", sa.Float),
        sa.Column("avg_sentiment_score", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_technical_indicators_symbol", "technical_indicators", ["symbol"])

    # Predictions
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("predicted_price", sa.Float),
        sa.Column("prediction_horizon_days", sa.Integer, default=7),
        sa.Column("features_used", sa.Text),
        sa.Column("actual_direction", sa.String(20)),
        sa.Column("was_correct", sa.Boolean),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_predictions_symbol", "predictions", ["symbol"])

    # Recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("symbol", sa.String(20)),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("expected_roi", sa.Float),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("is_acted_upon", sa.Boolean, default=False),
        sa.Column("is_dismissed", sa.Boolean, default=False),
        sa.Column("expires_at", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])


def downgrade() -> None:
    for table in [
        "recommendations", "predictions", "technical_indicators",
        "news_articles", "market_snapshots", "notifications",
        "crypto_holdings", "investments", "savings_goals",
        "loans", "expenses", "incomes", "wallets", "users",
    ]:
        op.drop_table(table)
