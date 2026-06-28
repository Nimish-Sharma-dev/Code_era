"""
Celery application configuration and task definitions.

Workers handle:
  - Periodic market data ingestion
  - FinBERT batch sentiment processing
  - Technical indicator computation
  - Prediction generation
  - Recommendation refresh
  - Financial health score updates
  - Notification dispatch
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "finai_workers",
    broker=settings.redis.celery_broker_url,
    backend=settings.redis.celery_broker_url.replace("/1", "/2"),
    include=[
        "app.workers.market_tasks",
        "app.workers.ml_tasks",
        "app.workers.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # Acknowledge after completion (fault tolerance)
    worker_prefetch_multiplier=1,  # One task at a time per worker (fair scheduling)
    task_soft_time_limit=300,      # 5 min soft limit
    task_time_limit=600,           # 10 min hard limit
    result_expires=3600,
    beat_schedule={
        # Market data — every 15 minutes during market hours
        "fetch-market-prices": {
            "task": "app.workers.market_tasks.fetch_all_market_prices",
            "schedule": 900,  # 15 min
        },
        # News — every hour
        "fetch-news": {
            "task": "app.workers.market_tasks.fetch_and_store_news",
            "schedule": 3600,  # 1 hour
        },
        # FinBERT sentiment — every hour (after news)
        "run-finbert": {
            "task": "app.workers.ml_tasks.run_sentiment_pipeline",
            "schedule": 3700,  # Slightly after news
        },
        # Technical indicators — every 4 hours
        "compute-indicators": {
            "task": "app.workers.ml_tasks.compute_technical_indicators",
            "schedule": 14400,  # 4 hours
        },
        # ML predictions — twice daily
        "run-predictions": {
            "task": "app.workers.ml_tasks.run_prediction_pipeline",
            "schedule": crontab(hour="9,17", minute="0"),
        },
        # Refresh recommendations — twice daily
        "refresh-recommendations": {
            "task": "app.workers.ml_tasks.refresh_all_user_recommendations",
            "schedule": crontab(hour="9,18", minute="30"),
        },
        # Health scores — daily
        "update-health-scores": {
            "task": "app.workers.ml_tasks.update_financial_health_scores",
            "schedule": crontab(hour="8", minute="0"),
        },
        # Crypto prices — every 5 minutes (24/7 markets)
        "fetch-crypto-prices": {
            "task": "app.workers.market_tasks.fetch_crypto_prices",
            "schedule": 300,  # 5 min
        },
    },
)
