"""Dashboard and analytics API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.graph.graph_service import GraphService
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.ml_services.financial_health_scorer import FinancialHealthScorer
from app.ml_services.risk_engine import RiskEngine
from app.repositories.market_repository import PredictionRepository, RecommendationRepository
from app.schemas.market import DashboardResponse, RecommendationResponse, PredictionResponse
from app.services.financial_service import FinancialService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(rate_limit_check)])


@router.get("", response_model=DashboardResponse, summary="Get financial dashboard summary")
async def get_dashboard(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a comprehensive financial dashboard including:
    - Net worth, assets, liabilities
    - Monthly cash flow (income/expenses/savings)
    - Financial Health Score with grade
    - Debt-to-income ratio and emergency fund status
    - Top recommendations and recent predictions
    - Portfolio sentiment summary
    """
    fin_svc = FinancialService(db_session=db)
    scorer = FinancialHealthScorer()
    risk_engine = RiskEngine()
    graph = GraphService()

    # Core financials
    summary = await fin_svc.compute_financial_summary(current_user.id)
    goals = await fin_svc.get_goals(current_user.id)
    investments = await fin_svc.get_investments(current_user.id)
    loans = await fin_svc.get_loans(current_user.id)

    crypto_value = sum(
        i.current_value for i in investments
        if str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class).lower() == "crypto"
    )

    # Financial health score
    health = scorer.compute(
        monthly_income=summary["monthly_income"],
        monthly_expenses=summary["monthly_expenses"],
        monthly_debt_payment=sum(l.monthly_payment for l in loans),
        total_cash=summary["total_cash"],
        total_debt=summary["total_liabilities"],
        portfolio_value=summary["investment_value"],
        crypto_value=crypto_value,
        goals=[{"target_amount": g.target_amount, "current_amount": g.current_amount} for g in goals],
        prev_net_worth=0.0,
    )

    # Recommendations
    rec_repo = RecommendationRepository(db)
    top_recs = await rec_repo.get_user_recommendations(current_user.id, limit=5)

    # Predictions for portfolio
    pred_repo = PredictionRepository(db)
    symbols = [i.symbol for i in investments[:5]]
    recent_preds = await pred_repo.get_recent_predictions(symbols, limit=5)

    # Portfolio sentiment from graph
    since = datetime.now(tz=timezone.utc).replace(day=1).isoformat()
    portfolio_sentiment = {}
    for sym in symbols[:5]:
        sent = await graph.get_asset_sentiment(sym, since=since)
        portfolio_sentiment[sym] = sent.get("avg_sentiment", 0.0)

    monthly_debt = sum(l.monthly_payment for l in loans)

    return DashboardResponse(
        user_id=current_user.id,
        financial_health_score=health.overall,
        net_worth=summary["net_worth"],
        total_assets=summary["total_assets"],
        total_liabilities=summary["total_liabilities"],
        monthly_income=summary["monthly_income"],
        monthly_expenses=summary["monthly_expenses"],
        monthly_savings=summary["monthly_income"] - summary["monthly_expenses"] - monthly_debt,
        savings_rate=summary["savings_rate"],
        debt_to_income_ratio=summary["debt_to_income_ratio"],
        emergency_fund_months=summary["emergency_fund_months"],
        investment_value=summary["investment_value"],
        crypto_value=crypto_value,
        top_recommendations=[RecommendationResponse.model_validate(r) for r in top_recs],
        recent_predictions=[PredictionResponse.model_validate(p) for p in recent_preds],
        portfolio_sentiment=portfolio_sentiment,
    )


@router.get("/risk-profile", summary="Get detailed risk profile")
async def get_risk_profile(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Return a detailed risk assessment for the current user."""
    fin_svc = FinancialService(db_session=db)
    risk_engine = RiskEngine()

    summary = await fin_svc.compute_financial_summary(current_user.id)
    investments = await fin_svc.get_investments(current_user.id)
    loans = await fin_svc.get_loans(current_user.id)

    type_volatilities = {
        "crypto": 0.70,
        "equity": 0.22,
        "etf": 0.15,
        "bond": 0.05,
        "cash": 0.00,
    }
    total_inv = sum(i.current_value for i in investments)
    avg_volatility = 0.0
    if total_inv > 0:
        avg_volatility = sum(
            type_volatilities.get(str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class).lower(), 0.20)
            * (i.current_value / total_inv)
            for i in investments
        )

    investments_list = [
        {
            "symbol": i.symbol,
            "asset_class": str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class),
            "current_value": i.current_value
        }
        for i in investments
    ]

    risk_profile = risk_engine.compute_risk_score(
        monthly_income=summary["monthly_income"],
        monthly_expenses=summary["monthly_expenses"],
        monthly_debt_payment=sum(l.monthly_payment for l in loans),
        total_cash=summary["total_cash"],
        total_debt=summary["total_liabilities"],
        portfolio_value=summary["investment_value"],
        asset_types=[str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class) for i in investments],
        declared_risk_tolerance=str(current_user.risk_tolerance.value if hasattr(current_user.risk_tolerance, 'value') else current_user.risk_tolerance),
        avg_portfolio_volatility=avg_volatility,
        investments=investments_list,
    )

    return {
        "overall_score": risk_profile.overall_score,
        "risk_level": risk_profile.risk_level,
        "components": {
            "debt": risk_profile.debt_score,
            "liquidity": risk_profile.liquidity_score,
            "savings": risk_profile.savings_score,
            "concentration": risk_profile.concentration_score,
            "volatility": risk_profile.volatility_score,
        },
        "explanation": risk_profile.explanation,
        "recommendations": risk_profile.recommendations,
    }
