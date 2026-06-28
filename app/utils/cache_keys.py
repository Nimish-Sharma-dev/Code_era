"""Centralised cache key definitions. Prevents typos and key collisions."""
from __future__ import annotations


class CacheKeys:
    # User
    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:profile:{user_id}"

    @staticmethod
    def user_financial_summary(user_id: str) -> str:
        return f"user:financial_summary:{user_id}"

    @staticmethod
    def user_recommendations(user_id: str) -> str:
        return f"user:recommendations:{user_id}"

    @staticmethod
    def user_risk_profile(user_id: str) -> str:
        return f"user:risk_profile:{user_id}"

    # Market
    @staticmethod
    def market_price(symbol: str) -> str:
        return f"market:price:{symbol.upper()}"

    @staticmethod
    def market_sentiment(symbol: str) -> str:
        return f"market:sentiment:{symbol.upper()}"

    @staticmethod
    def market_prediction(symbol: str) -> str:
        return f"market:prediction:{symbol.upper()}"

    @staticmethod
    def technical_indicators(symbol: str, timeframe: str = "1D") -> str:
        return f"market:indicators:{symbol.upper()}:{timeframe}"

    # News
    @staticmethod
    def latest_news(limit: int) -> str:
        return f"news:latest:{limit}"

    # Session
    @staticmethod
    def refresh_token(jti: str) -> str:
        return f"token:refresh:{jti}"

    @staticmethod
    def rate_limit(user_id: str) -> str:
        return f"ratelimit:user:{user_id}"

    # Graph
    @staticmethod
    def user_graph_context(user_id: str) -> str:
        return f"graph:context:{user_id}"
