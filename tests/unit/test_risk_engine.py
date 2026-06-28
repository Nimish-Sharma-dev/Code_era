"""Unit tests for the financial risk scoring engine."""

import pytest
from app.ml_services.risk_engine import RiskEngine


@pytest.fixture
def engine():
    return RiskEngine()


def test_no_debt_low_risk(engine):
    profile = engine.compute_risk_score(
        monthly_income=8000, monthly_expenses=3000,
        monthly_debt_payment=0, total_cash=30000,
        total_debt=0, portfolio_value=50000,
        asset_types=["equity", "bond", "etf"],
        declared_risk_tolerance="moderate",
    )
    assert profile.risk_level in ("low", "moderate")
    assert profile.debt_score < 20


def test_high_dti_raises_risk(engine):
    profile = engine.compute_risk_score(
        monthly_income=5000, monthly_expenses=2000,
        monthly_debt_payment=2500, total_cash=1000,
        total_debt=80000, portfolio_value=0,
        asset_types=[],
        declared_risk_tolerance="conservative",
    )
    assert profile.risk_level in ("high", "critical")
    assert profile.debt_score > 60


def test_no_emergency_fund_high_liquidity_risk(engine):
    profile = engine.compute_risk_score(
        monthly_income=6000, monthly_expenses=4000,
        monthly_debt_payment=500, total_cash=0,
        total_debt=5000, portfolio_value=10000,
        asset_types=["equity"],
        declared_risk_tolerance="moderate",
    )
    assert profile.liquidity_score > 50


def test_negative_savings_rate_increases_score(engine):
    profile = engine.compute_risk_score(
        monthly_income=3000, monthly_expenses=3500,
        monthly_debt_payment=200, total_cash=2000,
        total_debt=10000, portfolio_value=0,
        asset_types=[],
        declared_risk_tolerance="moderate",
    )
    assert profile.savings_score > 60


def test_recommendations_generated(engine):
    profile = engine.compute_risk_score(
        monthly_income=5000, monthly_expenses=3000,
        monthly_debt_payment=1500, total_cash=1000,
        total_debt=50000, portfolio_value=0,
        asset_types=[], declared_risk_tolerance="moderate",
    )
    assert len(profile.recommendations) > 0
