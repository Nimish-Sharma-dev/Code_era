"""
Development seed data script.

Creates test users, sample financial data, and dummy market records
for local development and testing. Never run in production.
"""

import asyncio
import uuid
from datetime import datetime, timezone

async def seed():
    from app.db.postgres.connection import get_db_session
    from app.core.security import hash_password
    from app.models.postgres.user import User, UserStatus, RiskToleranceLevel
    from app.models.postgres.financial import Wallet, Income, Expense, Loan, WalletType, IncomeFrequency, ExpenseCategory, LoanType, LoanStatus
    from app.models.postgres.market import NewsArticle

    print("Seeding development data...")

    async with get_db_session() as session:
        # Demo user
        user = User(
            id=uuid.uuid4(),
            email="demo@finai.com",
            username="demo_user",
            full_name="Alex Demo",
            hashed_password=hash_password("DemoPass123"),
            role="user",
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            risk_tolerance=RiskToleranceLevel.MODERATE,
            currency="USD",
        )
        session.add(user)
        await session.flush()

        # Wallets
        session.add(Wallet(
            user_id=user.id, name="Chase Checking",
            wallet_type=WalletType.CHECKING, balance=8500.0, is_primary=True,
        ))
        session.add(Wallet(
            user_id=user.id, name="High-Yield Savings",
            wallet_type=WalletType.SAVINGS, balance=15000.0,
        ))

        # Income
        session.add(Income(
            user_id=user.id, source="Software Engineer Salary",
            amount=8500.0, frequency=IncomeFrequency.MONTHLY, is_taxable=True, tax_rate=0.22,
        ))
        session.add(Income(
            user_id=user.id, source="Freelance Projects",
            amount=1200.0, frequency=IncomeFrequency.MONTHLY, is_taxable=True, tax_rate=0.25,
        ))

        # Expenses
        session.add(Expense(user_id=user.id, name="Rent", amount=2200.0, currency="USD", category=ExpenseCategory.HOUSING, frequency=IncomeFrequency.MONTHLY, is_fixed=True, is_essential=True))
        session.add(Expense(user_id=user.id, name="Groceries", amount=400.0, currency="USD", category=ExpenseCategory.FOOD, frequency=IncomeFrequency.MONTHLY, is_fixed=False, is_essential=True))
        session.add(Expense(user_id=user.id, name="Netflix + Spotify", amount=30.0, currency="USD", category=ExpenseCategory.ENTERTAINMENT, frequency=IncomeFrequency.MONTHLY, is_fixed=True, is_essential=False))

        # Loan
        session.add(Loan(
            user_id=user.id, name="Student Loan",
            loan_type=LoanType.STUDENT, principal_amount=45000.0,
            current_balance=28000.0, interest_rate=5.5,
            monthly_payment=350.0, remaining_term_months=84,
            status=LoanStatus.ACTIVE,
        ))

        # Sample news
        session.add(NewsArticle(
            title="Fed signals rate hold as inflation nears target",
            url="https://example.com/news/fed-2024-01",
            source="Mock News", published_at="2024-01-15T09:00:00Z",
            sentiment_label="neutral", sentiment_score=0.05,
        ))

    print("✅ Seed data created successfully")
    print("  Email: demo@finai.com  |  Password: DemoPass123")


if __name__ == "__main__":
    asyncio.run(seed())
