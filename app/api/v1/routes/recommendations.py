"""Recommendations and risk profile API routes."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.ml_services.risk_engine import RiskEngine
from app.ml_services.recommendation_engine import RecommendationEngine
from app.repositories.market_repository import PredictionRepository, RecommendationRepository
from app.schemas.market import RecommendationResponse
from app.services.financial_service import FinancialService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"], dependencies=[Depends(rate_limit_check)])


@router.get("", response_model=List[RecommendationResponse], summary="Get personalised recommendations")
async def get_recommendations(
    limit: int = Query(default=10, ge=1, le=20),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Return pre-computed personalised recommendations for the current user.
    Recommendations are refreshed twice daily by the background worker.
    """
    repo = RecommendationRepository(db)
    recs = await repo.get_user_recommendations(current_user.id, limit=limit)
    return [RecommendationResponse.model_validate(r) for r in recs]


@router.post("/refresh", response_model=List[RecommendationResponse], summary="Force-refresh recommendations now")
async def refresh_recommendations(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate recommendations on-demand using current financial state.
    Use sparingly — the background job handles this automatically.
    """
    fin_svc = FinancialService(db_session=db)
    risk_engine = RiskEngine()
    rec_engine = RecommendationEngine()
    pred_repo = PredictionRepository(db)
    rec_repo = RecommendationRepository(db)

    summary = await fin_svc.compute_financial_summary(current_user.id)
    loans = await fin_svc.get_loans(current_user.id)
    goals = await fin_svc.get_goals(current_user.id)
    investments = await fin_svc.get_investments(current_user.id)

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
        monthly_debt_payment=summary.get("monthly_debt", 0),
        total_cash=summary["total_cash"],
        total_debt=summary["total_liabilities"],
        portfolio_value=summary["investment_value"],
        asset_types=[str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class) for i in investments],
        declared_risk_tolerance=str(current_user.risk_tolerance.value if hasattr(current_user.risk_tolerance, 'value') else current_user.risk_tolerance),
        avg_portfolio_volatility=avg_volatility,
        investments=investments_list,
    )

    symbols = [i.symbol for i in investments]
    predictions = []
    for sym in symbols[:5]:
        pred = await pred_repo.get_latest_for_symbol(sym)
        if pred:
            predictions.append({
                "symbol": pred.symbol,
                "direction": pred.direction.value if hasattr(pred.direction, 'value') else pred.direction,
                "confidence": pred.confidence,
            })

    crypto_value = sum(
        i.current_value for i in investments
        if str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class).lower() == "crypto"
    )

    from app.repositories.market_repository import NewsArticleRepository
    news_repo = NewsArticleRepository(db)
    recent_articles = await news_repo.get_latest(limit=100)
    portfolio_sentiment = {}
    for sym in symbols:
        scores = []
        for art in recent_articles:
            if art.related_symbols and sym.upper() in art.related_symbols.upper():
                if art.sentiment_score is not None:
                    scores.append(art.sentiment_score)
        portfolio_sentiment[sym] = sum(scores) / len(scores) if scores else 0.0

    recommendations = rec_engine.generate(
        user_id=str(current_user.id),
        risk_profile=risk_profile,
        monthly_income=summary["monthly_income"],
        monthly_expenses=summary["monthly_expenses"],
        monthly_debt_payment=summary.get("monthly_debt", 0),
        total_cash=summary["total_cash"],
        total_debt=summary["total_liabilities"],
        portfolio_value=summary["investment_value"],
        crypto_value=crypto_value,
        loans=[{"name": l.name, "interest_rate": l.interest_rate, "current_balance": l.current_balance} for l in loans],
        goals=[{"name": g.name, "target_amount": g.target_amount, "current_amount": g.current_amount, "priority": g.priority} for g in goals],
        investments=[{"symbol": i.symbol, "asset_class": str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class), "current_value": i.current_value} for i in investments],
        market_predictions=predictions,
        portfolio_sentiment=portfolio_sentiment,
        risk_tolerance=str(current_user.risk_tolerance.value if hasattr(current_user.risk_tolerance, 'value') else current_user.risk_tolerance),
    )

    saved = []
    for rec in recommendations[:10]:
        r = await rec_repo.create(
            user_id=current_user.id,
            action=rec.action,
            symbol=rec.symbol,
            category=rec.category,
            title=rec.title,
            explanation=rec.explanation,
            confidence_score=rec.confidence_score,
            risk_level=rec.risk_level,
            expected_roi=rec.expected_roi,
        )
        saved.append(RecommendationResponse.model_validate(r))

    return saved


@router.patch("/{recommendation_id}/dismiss", status_code=204, summary="Dismiss a recommendation")
async def dismiss_recommendation(
    recommendation_id: UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    repo = RecommendationRepository(db)
    rec = await repo.get_by_id(recommendation_id)
    if rec and rec.user_id == current_user.id:
        await repo.update_by_id(recommendation_id, is_dismissed=True)


@router.patch("/{recommendation_id}/act", status_code=204, summary="Mark recommendation as acted upon")
async def act_on_recommendation(
    recommendation_id: UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    repo = RecommendationRepository(db)
    rec = await repo.get_by_id(recommendation_id)
    if rec and rec.user_id == current_user.id:
        await repo.update_by_id(recommendation_id, is_acted_upon=True)
