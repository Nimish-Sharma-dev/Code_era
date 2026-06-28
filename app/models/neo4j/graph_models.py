"""
Neo4j graph node definitions and Cypher query library.

Rather than an ORM layer (which doesn't exist for Neo4j), we define:
1. Dataclass-style node models for type-safe manipulation in Python.
2. A centralised Cypher query library for all graph operations.

This keeps graph logic in one place and prevents Cypher injection
through strict parameterisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Node Dataclasses ──────────────────────────────────────────────────────────

@dataclass
class UserNode:
    id: str
    email: str
    full_name: str
    risk_tolerance: str
    financial_health_score: Optional[float] = None
    currency: str = "USD"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class WalletNode:
    id: str
    name: str
    wallet_type: str
    balance: float
    currency: str = "USD"
    is_primary: bool = False


@dataclass
class AssetNode:
    symbol: str
    name: str
    asset_type: str  # equity/crypto/etf/bond
    current_price: float = 0.0
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    exchange: Optional[str] = None


@dataclass
class LoanNode:
    id: str
    name: str
    loan_type: str
    current_balance: float
    interest_rate: float
    monthly_payment: float


@dataclass
class GoalNode:
    id: str
    name: str
    target_amount: float
    current_amount: float
    priority: int = 1


@dataclass
class NewsNode:
    url: str
    title: str
    source: str
    published_at: str
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None


@dataclass
class PredictionNode:
    id: str
    symbol: str
    direction: str
    confidence: float
    model_name: str
    created_at: str


@dataclass
class RecommendationNode:
    id: str
    action: str
    category: str
    title: str
    confidence_score: float
    risk_level: str


# ── Cypher Query Library ──────────────────────────────────────────────────────

class GraphQueries:
    """
    Centralised Cypher query library.

    All queries use parameterised inputs ($param) to prevent Cypher injection.
    Queries are grouped by domain area.
    """

    # ── User Graph ────────────────────────────────────────────────────────────

    UPSERT_USER = """
    MERGE (u:User {id: $id})
    SET u.email = $email,
        u.full_name = $full_name,
        u.risk_tolerance = $risk_tolerance,
        u.financial_health_score = $financial_health_score,
        u.currency = $currency,
        u.updated_at = datetime()
    RETURN u
    """

    UPSERT_WALLET = """
    MERGE (w:Wallet {id: $id})
    SET w.name = $name,
        w.wallet_type = $wallet_type,
        w.balance = $balance,
        w.currency = $currency,
        w.updated_at = datetime()
    WITH w
    MATCH (u:User {id: $user_id})
    MERGE (u)-[:HAS_WALLET]->(w)
    RETURN w
    """

    UPSERT_LOAN = """
    MERGE (l:Loan {id: $id})
    SET l.name = $name,
        l.loan_type = $loan_type,
        l.current_balance = $current_balance,
        l.interest_rate = $interest_rate,
        l.monthly_payment = $monthly_payment,
        l.updated_at = datetime()
    WITH l
    MATCH (u:User {id: $user_id})
    MERGE (u)-[:OWES]->(l)
    RETURN l
    """

    UPSERT_GOAL = """
    MERGE (g:Goal {id: $id})
    SET g.name = $name,
        g.target_amount = $target_amount,
        g.current_amount = $current_amount,
        g.priority = $priority,
        g.updated_at = datetime()
    WITH g
    MATCH (u:User {id: $user_id})
    MERGE (u)-[:HAS_GOAL]->(g)
    RETURN g
    """

    UPSERT_ASSET = """
    MERGE (a:Asset {symbol: $symbol})
    SET a.name = $name,
        a.asset_type = $asset_type,
        a.current_price = $current_price,
        a.market_cap = $market_cap,
        a.sector = $sector,
        a.updated_at = datetime()
    RETURN a
    """

    LINK_USER_INVESTMENT = """
    MATCH (u:User {id: $user_id})
    MATCH (a:Asset {symbol: $symbol})
    MERGE (u)-[r:INVESTED_IN]->(a)
    SET r.quantity = $quantity,
        r.avg_buy_price = $avg_buy_price,
        r.updated_at = datetime()
    RETURN r
    """

    UPSERT_NEWS = """
    MERGE (n:News {url: $url})
    SET n.title = $title,
        n.source = $source,
        n.published_at = $published_at,
        n.sentiment_label = $sentiment_label,
        n.sentiment_score = $sentiment_score,
        n.updated_at = datetime()
    RETURN n
    """

    LINK_NEWS_TO_ASSET = """
    MATCH (n:News {url: $url})
    MATCH (a:Asset {symbol: $symbol})
    MERGE (n)-[r:SENTIMENT_TOWARD]->(a)
    SET r.score = $score,
        r.label = $label
    RETURN r
    """

    UPSERT_PREDICTION = """
    MERGE (p:Prediction {id: $id})
    SET p.symbol = $symbol,
        p.direction = $direction,
        p.confidence = $confidence,
        p.model_name = $model_name,
        p.created_at = $created_at
    WITH p
    MATCH (a:Asset {symbol: $symbol})
    MERGE (p)-[:PREDICTS]->(a)
    RETURN p
    """

    UPSERT_RECOMMENDATION = """
    MERGE (r:Recommendation {id: $id})
    SET r.action = $action,
        r.category = $category,
        r.title = $title,
        r.confidence_score = $confidence_score,
        r.risk_level = $risk_level,
        r.created_at = datetime()
    WITH r
    MATCH (u:User {id: $user_id})
    MERGE (u)<-[:RECOMMENDS]-(r)
    RETURN r
    """

    # ── Context Extraction Queries ────────────────────────────────────────────

    GET_USER_FINANCIAL_CONTEXT = """
    MATCH (u:User {id: $user_id})
    OPTIONAL MATCH (u)-[:HAS_WALLET]->(w:Wallet)
    OPTIONAL MATCH (u)-[:OWES]->(l:Loan)
    OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)
    OPTIONAL MATCH (u)-[:INVESTED_IN]->(a:Asset)
    RETURN u,
           collect(DISTINCT {id: w.id, name: w.name, balance: w.balance, type: w.wallet_type}) AS wallets,
           collect(DISTINCT {id: l.id, name: l.name, balance: l.current_balance, rate: l.interest_rate}) AS loans,
           collect(DISTINCT {id: g.id, name: g.name, target: g.target_amount, current: g.current_amount}) AS goals,
           collect(DISTINCT {symbol: a.symbol, name: a.name, price: a.current_price}) AS investments
    """

    GET_ASSET_SENTIMENT = """
    MATCH (n:News)-[r:SENTIMENT_TOWARD]->(a:Asset {symbol: $symbol})
    WHERE n.published_at > $since
    RETURN a.symbol AS symbol,
           avg(r.score) AS avg_sentiment,
           count(n) AS news_count,
           collect({title: n.title, score: r.score, label: r.label, date: n.published_at})[..10] AS recent_news
    """

    GET_PORTFOLIO_GRAPH = """
    MATCH (u:User {id: $user_id})-[:INVESTED_IN]->(a:Asset)
    OPTIONAL MATCH (n:News)-[:SENTIMENT_TOWARD]->(a)
    WHERE n.published_at > $since
    OPTIONAL MATCH (p:Prediction)-[:PREDICTS]->(a)
    RETURN a.symbol, a.name, a.current_price,
           avg(n.sentiment_score) AS avg_sentiment,
           collect(DISTINCT p.direction)[0] AS latest_prediction,
           collect(DISTINCT p.confidence)[0] AS prediction_confidence
    """

    GET_DEBT_ARBITRAGE_CONTEXT = """
    MATCH (u:User {id: $user_id})-[:OWES]->(l:Loan)
    MATCH (u)-[:HAS_WALLET]->(w:Wallet)
    RETURN u.risk_tolerance AS risk_tolerance,
           collect(DISTINCT {
               id: l.id,
               name: l.name,
               balance: l.current_balance,
               rate: l.interest_rate,
               payment: l.monthly_payment,
               type: l.loan_type
           }) AS loans,
           sum(w.balance) AS total_liquid_assets
    ORDER BY l.interest_rate DESC
    """

    GET_RISK_SCORING_CONTEXT = """
    MATCH (u:User {id: $user_id})
    OPTIONAL MATCH (u)-[:INVESTED_IN]->(a:Asset)
    OPTIONAL MATCH (u)-[:OWES]->(l:Loan)
    OPTIONAL MATCH (u)-[:HAS_WALLET]->(w:Wallet)
    RETURN u.risk_tolerance,
           count(DISTINCT a) AS asset_count,
           collect(DISTINCT a.asset_type) AS asset_types,
           sum(l.current_balance) AS total_debt,
           sum(w.balance) AS total_cash,
           sum(a.current_price) AS total_investment_value
    """

    GET_RECOMMENDATIONS_FOR_USER = """
    MATCH (r:Recommendation)-[:RECOMMENDS]->(u:User {id: $user_id})
    WHERE r.created_at > $since
    RETURN r
    ORDER BY r.confidence_score DESC
    LIMIT $limit
    """

    DELETE_USER_GRAPH = """
    MATCH (u:User {id: $user_id})
    OPTIONAL MATCH (u)-[*1..2]->(n)
    DETACH DELETE u, n
    """
