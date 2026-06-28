"""Unit tests for financial health scorer."""

import pytest
from app.ml_services.financial_health_scorer import FinancialHealthScorer


@pytest.fixture
def scorer():
    return FinancialHealthScorer()


def test_perfect_finances_high_score(scorer):
    breakdown = scorer.compute(
        monthly_income=10000, monthly_expenses=3000,
        monthly_debt_payment=0, total_cash=60000,
        total_debt=0, portfolio_value=100000,
        crypto_value=0,
        goals=[{"target_amount": 10000, "current_amount": 10000}],
    )
    assert breakdown.overall >= 85
    assert breakdown.grade in ("A+", "A")


def test_no_savings_no_emergency_fund_low_score(scorer):
    breakdown = scorer.compute(
        monthly_income=4000, monthly_expenses=4500,
        monthly_debt_payment=300, total_cash=100,
        total_debt=20000, portfolio_value=0,
        crypto_value=0, goals=[],
    )
    assert breakdown.overall < 50
    assert breakdown.grade in ("D", "F")


def test_grade_mapping(scorer):
    cases = [
        (95, "A+"), (85, "A"), (75, "B"), (65, "C"), (55, "D"), (40, "F")
    ]
    for score, expected in cases:
        assert scorer._grade(score) == expected


def test_action_item_exists(scorer):
    breakdown = scorer.compute(
        monthly_income=5000, monthly_expenses=3000,
        monthly_debt_payment=500, total_cash=5000,
        total_debt=15000, portfolio_value=5000,
        crypto_value=0, goals=[],
    )
    assert isinstance(breakdown.action_item, str)
    assert len(breakdown.action_item) > 10
