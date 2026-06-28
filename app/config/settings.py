"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables with strong typing,
validation, and sensible defaults. Never hardcode secrets.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection configuration."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    db: str = "finai_db"
    user: str = "finai_user"
    password: str = "password"
    pool_size: int = Field(default=20, ge=1, le=100)
    max_overflow: int = Field(default=40, ge=0, le=200)
    pool_timeout: int = Field(default=30, ge=5, le=120)
    pool_pre_ping: bool = True
    echo: bool = False

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class Neo4jSettings(BaseSettings):
    """Neo4j graph database configuration."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", extra="ignore")

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0
    max_transaction_retry_time: float = 30.0


class RedisSettings(BaseSettings):
    """Redis cache configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    cache_ttl_seconds: int = 300
    max_connections: int = 50

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    @property
    def celery_broker_url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/1"
        return f"redis://{self.host}:{self.port}/1"


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")

    secret_key: str = "change-me-in-production-must-be-32-chars-min"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class MLSettings(BaseSettings):
    """Machine Learning model configuration."""

    model_config = SettingsConfigDict(env_prefix="ML_", extra="ignore")

    model_registry_path: str = "/app/ml_models"
    finbert_model: str = "ProsusAI/finbert"
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model_path: str = "/app/llm_models/mistral-7b"
    vector_store_path: str = "/app/vector_store"
    prediction_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    sentiment_alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    device: str = "cpu"  # "cuda" for GPU inference


class MarketDataSettings(BaseSettings):
    """External market data API configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    alpha_vantage_api_key: str = ""
    news_api_key: str = ""
    coingecko_api_key: str = ""
    binance_api_key: str = ""
    binance_secret_key: str = ""


class Settings(BaseSettings):
    """
    Master application settings.

    Aggregates all sub-settings and provides application-level configuration.
    Settings are loaded from environment variables with .env file support.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "FinAI Platform"
    app_env: str = Field(default="development", pattern="^(development|staging|production)$")
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = Field(default=4, ge=1, le=32)
    reload: bool = False

    # ── CORS / Security ──────────────────────────────────────────────────────
    allowed_hosts: List[str] = ["*"]
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 100

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"
    sentry_dsn: Optional[str] = None

    # ── Feature Flags ────────────────────────────────────────────────────────
    enable_crypto: bool = True
    enable_rag_chatbot: bool = True
    enable_ml_predictions: bool = True
    enable_graph_intelligence: bool = True

    # ── Sub-settings (composed via nested instantiation) ─────────────────────
    @property
    def database(self) -> DatabaseSettings:
        return DatabaseSettings()

    @property
    def neo4j(self) -> Neo4jSettings:
        return Neo4jSettings()

    @property
    def redis(self) -> RedisSettings:
        return RedisSettings()

    @property
    def jwt(self) -> JWTSettings:
        return JWTSettings()

    @property
    def ml(self) -> MLSettings:
        return MLSettings()

    @property
    def market(self) -> MarketDataSettings:
        return MarketDataSettings()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    Using lru_cache ensures settings are loaded only once per process,
    which improves performance and avoids repeated disk/env reads.
    """
    return Settings()
