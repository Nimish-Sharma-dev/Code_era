"""Celery tasks for ML pipelines: sentiment, indicators, predictions, recommendations."""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.workers.ml_tasks.run_sentiment_pipeline")
def run_sentiment_pipeline(self):
    """Run FinBERT on all unprocessed news articles."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_run_sentiment())
    finally:
        loop.close()


async def _async_run_sentiment():
    from app.ml_services.finbert_service import get_finbert_service
    from app.db.postgres.connection import get_db_session
    from app.repositories.market_repository import NewsArticleRepository
    from app.graph.graph_service import GraphService

    finbert = get_finbert_service()
    graph = GraphService()
    processed = 0

    async with get_db_session() as session:
        repo = NewsArticleRepository(session)
        articles = await repo.get_unprocessed(limit=50)

        if not articles:
            return {"processed": 0}

        texts = [a.title + (" " + a.summary if a.summary else "") for a in articles]
        results = await finbert.analyze_batch(texts)

        for article, sentiment in zip(articles, results):
            await repo.update_by_id(
                article.id,
                sentiment_label=sentiment.label,
                sentiment_score=sentiment.score,
                positive_score=sentiment.positive,
                negative_score=sentiment.negative,
                neutral_score=sentiment.neutral,
            )
            # Store in graph if related to tracked symbols
            related = []
            if article.related_symbols:
                import json
                try:
                    related = json.loads(article.related_symbols)
                except Exception:
                    pass

            await graph.upsert_news_with_sentiment(
                url=article.url,
                title=article.title,
                source=article.source,
                published_at=article.published_at,
                sentiment_label=sentiment.label,
                sentiment_score=sentiment.score,
                related_symbols=related,
            )
            processed += 1

    logger.info("FinBERT sentiment pipeline complete", processed=processed)
    return {"processed": processed}


@celery_app.task(bind=True, name="app.workers.ml_tasks.compute_technical_indicators")
def compute_technical_indicators(self):
    """Compute and store technical indicators for all tracked symbols."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_compute_indicators())
    finally:
        loop.close()


async def _async_compute_indicators():
    import pandas as pd
    from app.collectors.market_collector import YahooFinanceCollector, AlphaVantageCollector
    from app.ml_services.technical_indicators import TechnicalIndicatorEngine
    from app.db.postgres.connection import get_db_session
    from app.repositories.market_repository import TechnicalIndicatorRepository
    from app.workers.market_tasks import EQUITY_SYMBOLS

    collector = YahooFinanceCollector()
    av_collector = AlphaVantageCollector()
    engine = TechnicalIndicatorEngine()
    updated = 0

    fear_greed = await av_collector.fetch_fear_greed_proxy()

    for symbol in EQUITY_SYMBOLS[:10]:  # Throttle to 10 at a time
        try:
            bars = await collector.fetch_ohlcv(symbol, period="6mo", interval="1d")
            if len(bars) < 30:
                continue

            df = pd.DataFrame(bars).rename(columns={
                "open": "open", "high": "high", "low": "low",
                "close": "close", "volume": "volume",
            })
            indicators = engine.compute_all(df, fear_greed=fear_greed)

            async with get_db_session() as session:
                repo = TechnicalIndicatorRepository(session)
                await repo.create(
                    symbol=symbol,
                    timeframe="1D",
                    fear_greed_index=fear_greed,
                    **{k: v for k, v in indicators.items() if k != "fear_greed_index"},
                )
            updated += 1
        except Exception as exc:
            logger.warning("Indicator computation failed", symbol=symbol, error=str(exc))

    await collector.close()
    await av_collector.close()
    logger.info("Technical indicators computed", updated=updated)
    return {"updated": updated}


@celery_app.task(bind=True, name="app.workers.ml_tasks.run_prediction_pipeline")
def run_prediction_pipeline(self):
    """Generate market predictions for all tracked symbols."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_run_predictions())
    finally:
        loop.close()


async def _async_run_predictions():
    import uuid
    from datetime import datetime, timezone
    from app.ml_services.market_predictor import MarketPredictor, FeatureBuilder
    from app.db.postgres.connection import get_db_session
    from app.repositories.market_repository import TechnicalIndicatorRepository, PredictionRepository
    from app.graph.graph_service import GraphService
    from app.workers.market_tasks import EQUITY_SYMBOLS

    predictor = MarketPredictor()
    feature_builder = FeatureBuilder()
    graph = GraphService()
    generated = 0

    async with get_db_session() as session:
        indicator_repo = TechnicalIndicatorRepository(session)
        prediction_repo = PredictionRepository(session)

        for symbol in EQUITY_SYMBOLS:
            try:
                indicator = await indicator_repo.get_latest(symbol)
                if not indicator:
                    continue

                features = feature_builder.build(
                    indicators={
                        col: getattr(indicator, col, None)
                        for col in feature_builder.FEATURE_COLUMNS
                        if hasattr(indicator, col)
                    },
                    latest_close=indicator.sma_20 or 100.0,
                )
                direction, confidence = predictor.predict(features)

                prediction = await prediction_repo.create(
                    symbol=symbol,
                    model_name="MarketPredictor",
                    model_version=predictor._version,
                    direction=direction,
                    confidence=confidence,
                    prediction_horizon_days=7,
                )

                await graph.upsert_prediction(
                    prediction_id=str(prediction.id),
                    symbol=symbol,
                    direction=direction,
                    confidence=confidence,
                    model_name="MarketPredictor",
                    created_at=datetime.now(tz=timezone.utc).isoformat(),
                )
                generated += 1
            except Exception as exc:
                logger.warning("Prediction failed", symbol=symbol, error=str(exc))

    logger.info("Predictions generated", count=generated)
    return {"generated": generated}


@celery_app.task(bind=True, name="app.workers.ml_tasks.refresh_all_user_recommendations")
def refresh_all_user_recommendations(self):
    """Regenerate recommendations for all active users."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_refresh_recommendations())
    finally:
        loop.close()


async def _async_refresh_recommendations():
    from sqlalchemy import select
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.user import User, UserStatus
    from app.services.financial_service import FinancialService
    from app.ml_services.risk_engine import RiskEngine
    from app.ml_services.recommendation_engine import RecommendationEngine
    from app.repositories.market_repository import PredictionRepository
    from app.graph.graph_service import GraphService

    risk_engine = RiskEngine()
    rec_engine = RecommendationEngine()
    graph = GraphService()
    refreshed = 0

    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.status == UserStatus.ACTIVE).limit(500)
        )
        users = result.scalars().all()

        fin_service = FinancialService(session)
        pred_repo = PredictionRepository(session)

        for user in users:
            try:
                summary = await fin_service.compute_financial_summary(user.id)
                loans = await fin_service.get_loans(user.id)
                goals = await fin_service.get_goals(user.id)
                investments = await fin_service.get_investments(user.id)

                risk_profile = risk_engine.compute_risk_score(
                    monthly_income=summary["monthly_income"],
                    monthly_expenses=summary["monthly_expenses"],
                    monthly_debt_payment=summary.get("monthly_debt", 0),
                    total_cash=summary["total_cash"],
                    total_debt=summary["total_liabilities"],
                    portfolio_value=summary["investment_value"],
                    asset_types=[i.asset_class.value for i in investments],
                    declared_risk_tolerance=str(user.risk_tolerance.value if hasattr(user.risk_tolerance, 'value') else user.risk_tolerance),
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

                recommendations = rec_engine.generate(
                    user_id=str(user.id),
                    risk_profile=risk_profile,
                    monthly_income=summary["monthly_income"],
                    monthly_expenses=summary["monthly_expenses"],
                    monthly_debt_payment=summary.get("monthly_debt", 0),
                    total_cash=summary["total_cash"],
                    total_debt=summary["total_liabilities"],
                    portfolio_value=summary["investment_value"],
                    crypto_value=0,
                    loans=[{"name": l.name, "interest_rate": l.interest_rate, "current_balance": l.current_balance} for l in loans],
                    goals=[{"name": g.name, "target_amount": g.target_amount, "current_amount": g.current_amount, "priority": g.priority} for g in goals],
                    investments=[{"symbol": i.symbol, "asset_class": str(i.asset_class.value if hasattr(i.asset_class, 'value') else i.asset_class), "current_value": i.current_value} for i in investments],
                    market_predictions=predictions,
                    portfolio_sentiment={},
                    risk_tolerance=str(user.risk_tolerance.value if hasattr(user.risk_tolerance, 'value') else user.risk_tolerance),
                )

                from app.repositories.market_repository import RecommendationRepository
                rec_repo = RecommendationRepository(session)
                for rec in recommendations[:5]:
                    await rec_repo.create(
                        user_id=user.id,
                        action=rec.action,
                        symbol=rec.symbol,
                        category=rec.category,
                        title=rec.title,
                        explanation=rec.explanation,
                        confidence_score=rec.confidence_score,
                        risk_level=rec.risk_level,
                    )
                refreshed += 1
            except Exception as exc:
                logger.warning("Recommendation refresh failed", user_id=str(user.id), error=str(exc))

    logger.info("Recommendations refreshed", users=refreshed)
    return {"refreshed": refreshed}


@celery_app.task(bind=True, name="app.workers.ml_tasks.update_financial_health_scores")
def update_financial_health_scores(self):
    """Recompute and persist financial health scores for all active users."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_update_health_scores())
    finally:
        loop.close()


async def _async_update_health_scores():
    from sqlalchemy import select
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.user import User, UserStatus
    from app.ml_services.financial_health_scorer import FinancialHealthScorer
    from app.repositories.user_repository import UserRepository
    from app.services.financial_service import FinancialService

    scorer = FinancialHealthScorer()
    updated = 0

    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.status == UserStatus.ACTIVE).limit(500)
        )
        users = result.scalars().all()
        fin_service = FinancialService(session)
        user_repo = UserRepository(session)

        for user in users:
            try:
                summary = await fin_service.compute_financial_summary(user.id)
                goals = await fin_service.get_goals(user.id)

                breakdown = scorer.compute(
                    monthly_income=summary["monthly_income"],
                    monthly_expenses=summary["monthly_expenses"],
                    monthly_debt_payment=0,
                    total_cash=summary["total_cash"],
                    total_debt=summary["total_liabilities"],
                    portfolio_value=summary["investment_value"],
                    crypto_value=0,
                    goals=[{"target_amount": g.target_amount, "current_amount": g.current_amount} for g in goals],
                )
                await user_repo.update_financial_health_score(user.id, breakdown.overall)
                updated += 1
            except Exception as exc:
                logger.warning("Health score update failed", user_id=str(user.id), error=str(exc))

    logger.info("Health scores updated", count=updated)
    return {"updated": updated}
