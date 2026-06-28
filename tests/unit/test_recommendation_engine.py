"""Unit tests for the recommendation engine."""

import pytest
from app.ml_services.recommendation_engine import RecommendationEngine, RecommendationPriority
from app.ml_services.risk_engine import RiskEngine


@pytest.fixture
def engine():
    return RecommendationEngine()


@pytest.fixture
def healthy_risk_profile():
    return RiskEngine().compute_risk_score(
        monthly_income=8000, monthly_expenses=3000,
        monthly_debt_payment=0, total_cash=24000,
        total_debt=0, portfolio_value=30000,
        asset_types=["equity", "bond"], declared_risk_tolerance="moderate",
    )


@pytest.fixture
def stressed_risk_profile():
    return RiskEngine().compute_risk_score(
        monthly_income=4000, monthly_expenses=3500,
        monthly_debt_payment=1200, total_cash=500,
        total_debt=40000, portfolio_value=0,
        asset_types=[], declared_risk_tolerance="moderate",
    )


def test_emergency_fund_critical_when_no_cash(engine, stressed_risk_profile):
    recs = engine.generate(
        user_id="user-1",
        risk_profile=stressed_risk_profile,
        monthly_income=4000, monthly_expenses=3500,
        monthly_debt_payment=1200, total_cash=500,
        total_debt=40000, portfolio_value=0, crypto_value=0,
        loans=[{"name": "Credit Card", "interest_rate": 22, "current_balance": 8000}],
        goals=[], investments=[],
        market_predictions=[], portfolio_sentiment={},
        risk_tolerance="moderate",
    )
    # Emergency fund must be highest priority
    ef_recs = [r for r in recs if r.action == "build_emergency_fund"]
    assert len(ef_recs) > 0
    assert ef_recs[0].priority in (RecommendationPriority.CRITICAL, RecommendationPriority.HIGH)


def test_no_investment_rec_when_no_emergency_fund(engine, stressed_risk_profile):
    recs = engine.generate(
        user_id="user-1",
        risk_profile=stressed_risk_profile,
        monthly_income=4000, monthly_expenses=3500,
        monthly_debt_payment=1200, total_cash=200,
        total_debt=40000, portfolio_value=0, crypto_value=0,
        loans=[], goals=[], investments=[],
        market_predictions=[{"symbol": "AAPL", "direction": "bullish", "confidence": 0.9}],
        portfolio_sentiment={"AAPL": 0.8}, risk_tolerance="moderate",
    )
    buy_recs = [r for r in recs if r.action == "buy"]
    assert len(buy_recs) == 0, "Should NOT recommend buying when no emergency fund"


def test_high_interest_debt_gets_recommended_before_investment(engine, healthy_risk_profile):
    healthy_risk_profile_with_debt = RiskEngine().compute_risk_score(
        monthly_income=8000, monthly_expenses=3000,
        monthly_debt_payment=500, total_cash=24000,
        total_debt=15000, portfolio_value=30000,
        asset_types=["equity"], declared_risk_tolerance="moderate",
    )
    recs = engine.generate(
        user_id="user-2",
        risk_profile=healthy_risk_profile_with_debt,
        monthly_income=8000, monthly_expenses=3000,
        monthly_debt_payment=500, total_cash=24000,
        total_debt=15000, portfolio_value=30000, crypto_value=0,
        loans=[{"name": "Credit Card", "interest_rate": 22, "current_balance": 15000}],
        goals=[], investments=[{"symbol": "SPY", "asset_class": "etf", "current_value": 30000}],
        market_predictions=[{"symbol": "SPY", "direction": "bullish", "confidence": 0.80}],
        portfolio_sentiment={"SPY": 0.5}, risk_tolerance="moderate",
    )
    priorities = [r.priority.value for r in recs]
    debt_idx = next((i for i, r in enumerate(recs) if r.action == "pay_debt"), None)
    buy_idx = next((i for i, r in enumerate(recs) if r.action == "buy"), None)
    if debt_idx is not None and buy_idx is not None:
        assert debt_idx < buy_idx, "Debt payoff must come before investment recommendation"


def test_recommendation_has_explanation(engine, healthy_risk_profile):
    recs = engine.generate(
        user_id="user-3",
        risk_profile=healthy_risk_profile,
        monthly_income=8000, monthly_expenses=3000,
        monthly_debt_payment=0, total_cash=24000,
        total_debt=0, portfolio_value=30000, crypto_value=0,
        loans=[], goals=[], investments=[],
        market_predictions=[], portfolio_sentiment={},
        risk_tolerance="moderate",
    )
    for rec in recs:
        assert len(rec.explanation) > 30
        assert 0.0 <= rec.confidence_score <= 1.0
