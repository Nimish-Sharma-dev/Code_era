"""Celery tasks for market data ingestion."""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

# Tracked symbols — in production, load from DB dynamically
EQUITY_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "SPY", "QQQ", "BRK-B"]
CRYPTO_TOP_N = 20


@celery_app.task(bind=True, name="app.workers.market_tasks.fetch_all_market_prices")
def fetch_all_market_prices(self):
    """Fetch latest prices for all tracked equity symbols."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_fetch_prices())
    finally:
        loop.close()


async def _async_fetch_prices():
    from app.collectors.market_collector import YahooFinanceCollector
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.market import MarketSnapshot
    from datetime import datetime, timezone

    collector = YahooFinanceCollector()
    prices = await collector.fetch_multiple_prices(EQUITY_SYMBOLS)

    async with get_db_session() as session:
        for symbol, price in prices.items():
            snapshot = MarketSnapshot(
                symbol=symbol,
                asset_type="equity",
                open_price=price,
                high_price=price,
                low_price=price,
                close_price=price,
                volume=0,
                source="yahoo_finance",
            )
            session.add(snapshot)

    await collector.close()
    logger.info("Equity prices updated", count=len(prices))
    return {"updated": len(prices), "symbols": list(prices.keys())}


@celery_app.task(bind=True, name="app.workers.market_tasks.fetch_crypto_prices")
def fetch_crypto_prices(self):
    """Fetch top crypto prices from CoinGecko."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_fetch_crypto())
    finally:
        loop.close()


async def _async_fetch_crypto():
    from app.collectors.market_collector import CoinGeckoCollector
    from app.db.postgres.connection import get_db_session
    from app.models.postgres.market import MarketSnapshot

    collector = CoinGeckoCollector()
    coins = await collector.fetch_top_coins(limit=CRYPTO_TOP_N)

    async with get_db_session() as session:
        for coin in coins:
            snapshot = MarketSnapshot(
                symbol=coin["symbol"],
                asset_type="crypto",
                open_price=coin["current_price"],
                high_price=coin["current_price"],
                low_price=coin["current_price"],
                close_price=coin["current_price"],
                volume=coin.get("volume_24h", 0),
                market_cap=coin.get("market_cap"),
                source="coingecko",
            )
            session.add(snapshot)

    await collector.close()
    logger.info("Crypto prices updated", count=len(coins))
    return {"updated": len(coins)}


@celery_app.task(bind=True, name="app.workers.market_tasks.fetch_and_store_news")
def fetch_and_store_news(self):
    """Fetch financial news and store unprocessed articles."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_fetch_news())
    finally:
        loop.close()


async def _async_fetch_news():
    from app.collectors.market_collector import NewsAPICollector
    from app.db.postgres.connection import get_db_session
    from app.repositories.market_repository import NewsArticleRepository

    collector = NewsAPICollector()
    articles = await collector.fetch_financial_news()
    saved = 0

    async with get_db_session() as session:
        repo = NewsArticleRepository(session)
        for article in articles:
            if not await repo.url_exists(article["url"]):
                await repo.create(
                    title=article["title"],
                    summary=article.get("summary"),
                    url=article["url"],
                    source=article["source"],
                    published_at=article["published_at"],
                )
                saved += 1

    await collector.close()
    logger.info("News articles stored", saved=saved, total=len(articles))
    return {"saved": saved, "total": len(articles)}
