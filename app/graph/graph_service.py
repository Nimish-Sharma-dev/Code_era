"""
Graph Intelligence Service: orchestrates all Neo4j operations.

Provides a clean async interface over raw Cypher queries,
mapping between domain models and graph nodes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.db.neo4j.connection import get_neo4j_session
from app.models.neo4j.graph_models import GraphQueries
from app.core.logging import get_logger
from app.core.exceptions import GraphError

logger = get_logger(__name__)


class GraphService:
    """
    Async service wrapping all Neo4j graph operations.

    Methods follow the same pattern: transform domain model → run Cypher
    → return structured result. All queries are parameterised.
    """

    async def upsert_user(self, user: Any) -> None:
        """Sync a User PostgreSQL record into the Neo4j graph."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_USER,
                    id=str(user.id),
                    email=user.email,
                    full_name=user.full_name,
                    risk_tolerance=str(user.risk_tolerance.value if hasattr(user.risk_tolerance, 'value') else user.risk_tolerance),
                    financial_health_score=user.financial_health_score,
                    currency=user.currency,
                )
        except Exception as exc:
            logger.error("Graph upsert_user failed", user_id=str(user.id), error=str(exc))
            raise GraphError(f"Failed to sync user to graph: {exc}")

    async def upsert_wallet(self, wallet: Any) -> None:
        """Sync wallet to graph and link to user."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_WALLET,
                    id=str(wallet.id),
                    user_id=str(wallet.user_id),
                    name=wallet.name,
                    wallet_type=str(wallet.wallet_type.value if hasattr(wallet.wallet_type, 'value') else wallet.wallet_type),
                    balance=float(wallet.balance),
                    currency=wallet.currency,
                    is_primary=wallet.is_primary,
                )
        except Exception as exc:
            logger.error("Graph upsert_wallet failed", error=str(exc))
            raise GraphError(str(exc))

    async def upsert_loan(self, loan: Any) -> None:
        """Sync loan to graph with OWES relationship."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_LOAN,
                    id=str(loan.id),
                    user_id=str(loan.user_id),
                    name=loan.name,
                    loan_type=str(loan.loan_type.value if hasattr(loan.loan_type, 'value') else loan.loan_type),
                    current_balance=float(loan.current_balance),
                    interest_rate=float(loan.interest_rate),
                    monthly_payment=float(loan.monthly_payment),
                )
        except Exception as exc:
            raise GraphError(str(exc))

    async def upsert_asset(
        self, symbol: str, name: str, asset_type: str,
        current_price: float, market_cap: Optional[float] = None,
        sector: Optional[str] = None
    ) -> None:
        """Upsert an asset node (shared across all users)."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_ASSET,
                    symbol=symbol.upper(),
                    name=name,
                    asset_type=asset_type,
                    current_price=float(current_price),
                    market_cap=float(market_cap) if market_cap else None,
                    sector=sector,
                )
        except Exception as exc:
            raise GraphError(str(exc))

    async def link_user_investment(
        self, user_id: str, symbol: str, quantity: float, avg_buy_price: float
    ) -> None:
        """Create/update INVESTED_IN edge between User and Asset."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.LINK_USER_INVESTMENT,
                    user_id=user_id,
                    symbol=symbol.upper(),
                    quantity=float(quantity),
                    avg_buy_price=float(avg_buy_price),
                )
        except Exception as exc:
            raise GraphError(str(exc))

    async def upsert_news_with_sentiment(
        self, url: str, title: str, source: str, published_at: str,
        sentiment_label: str, sentiment_score: float,
        related_symbols: List[str],
    ) -> None:
        """Store news article and link SENTIMENT_TOWARD assets."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_NEWS,
                    url=url,
                    title=title,
                    source=source,
                    published_at=published_at,
                    sentiment_label=sentiment_label,
                    sentiment_score=float(sentiment_score),
                )
                for symbol in related_symbols:
                    await session.run(
                        GraphQueries.LINK_NEWS_TO_ASSET,
                        url=url,
                        symbol=symbol.upper(),
                        score=float(sentiment_score),
                        label=sentiment_label,
                    )
        except Exception as exc:
            raise GraphError(str(exc))

    async def upsert_prediction(
        self, prediction_id: str, symbol: str, direction: str,
        confidence: float, model_name: str, created_at: str
    ) -> None:
        """Store a prediction and link it to an asset."""
        try:
            async with get_neo4j_session() as session:
                await session.run(
                    GraphQueries.UPSERT_PREDICTION,
                    id=prediction_id,
                    symbol=symbol.upper(),
                    direction=direction,
                    confidence=float(confidence),
                    model_name=model_name,
                    created_at=created_at,
                )
        except Exception as exc:
            raise GraphError(str(exc))

    async def get_user_financial_context(self, user_id: str) -> Dict:
        """Fetch complete user financial context from graph for RAG."""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    GraphQueries.GET_USER_FINANCIAL_CONTEXT,
                    user_id=user_id,
                )
                record = await result.single()
                if not record:
                    return {}
                return {
                    "user": dict(record["u"]),
                    "wallets": record["wallets"],
                    "loans": record["loans"],
                    "goals": record["goals"],
                    "investments": record["investments"],
                }
        except Exception as exc:
            logger.error("Graph context fetch failed", user_id=user_id, error=str(exc))
            return {}

    async def get_asset_sentiment(
        self, symbol: str, since: str
    ) -> Dict:
        """Aggregate sentiment for an asset from linked news nodes."""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    GraphQueries.GET_ASSET_SENTIMENT,
                    symbol=symbol.upper(),
                    since=since,
                )
                record = await result.single()
                if not record:
                    return {"symbol": symbol, "avg_sentiment": 0.0, "news_count": 0, "recent_news": []}
                return {
                    "symbol": record["symbol"],
                    "avg_sentiment": float(record["avg_sentiment"] or 0.0),
                    "news_count": record["news_count"],
                    "recent_news": list(record["recent_news"] or []),
                }
        except Exception as exc:
            logger.error("Sentiment fetch failed", symbol=symbol, error=str(exc))
            return {"symbol": symbol, "avg_sentiment": 0.0, "news_count": 0, "recent_news": []}

    async def get_portfolio_graph(self, user_id: str, since: str) -> List[Dict]:
        """Fetch enriched portfolio with sentiment and prediction signals."""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    GraphQueries.GET_PORTFOLIO_GRAPH,
                    user_id=user_id,
                    since=since,
                )
                records = await result.data()
                return records
        except Exception as exc:
            logger.error("Portfolio graph fetch failed", user_id=user_id, error=str(exc))
            return []

    async def get_debt_arbitrage_context(self, user_id: str) -> Dict:
        """Fetch all debt and liquidity data for debt arbitrage analysis."""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    GraphQueries.GET_DEBT_ARBITRAGE_CONTEXT,
                    user_id=user_id,
                )
                record = await result.single()
                return dict(record) if record else {}
        except Exception as exc:
            logger.error("Debt context fetch failed", error=str(exc))
            return {}

    async def get_risk_scoring_context(self, user_id: str) -> Dict:
        """Fetch portfolio composition for risk scoring."""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    GraphQueries.GET_RISK_SCORING_CONTEXT,
                    user_id=user_id,
                )
                record = await result.single()
                return dict(record) if record else {}
        except Exception as exc:
            logger.error("Risk context fetch failed", error=str(exc))
            return {}
