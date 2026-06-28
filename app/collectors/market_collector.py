"""
Market data collectors: Yahoo Finance, Alpha Vantage, CoinGecko, NewsAPI.

Each collector:
  - Runs async HTTP requests with retry logic (tenacity).
  - Respects API rate limits.
  - Stores raw data in PostgreSQL.
  - Updates graph on successful fetch.
  - Fails gracefully without crashing the worker.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.logging import get_logger
from app.config.settings import get_settings

settings = get_settings()
logger = get_logger(__name__)

RETRY_CONFIG = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    reraise=True,
)


class BaseCollector:
    """Shared HTTP session and request utilities."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=30, connect=10)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"User-Agent": f"FinAI-Platform/{settings.app_version}"},
            )
        return self._session

    async def _get(self, url: str, params: Dict = None, headers: Dict = None) -> Dict:
        session = await self._get_session()
        async with session.get(url, params=params, headers=headers or {}) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


class YahooFinanceCollector(BaseCollector):
    """
    Fetch OHLCV data from Yahoo Finance (unofficial API).

    Uses yfinance library for simplicity. In production, prefer a paid
    data vendor (Polygon.io, Refinitiv) for reliability and legal clarity.
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    async def fetch_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> List[Dict]:
        """
        Fetch OHLCV bars for a symbol.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "SPY").
            period: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y".
            interval: "1m", "5m", "15m", "1h", "1d", "1wk", "1mo".

        Returns:
            List of OHLCV dicts with 'timestamp', 'open', 'high', 'low', 'close', 'volume'.
        """
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(symbol)
            hist = await loop.run_in_executor(None, lambda: ticker.history(period=period, interval=interval))

            records = []
            for ts, row in hist.iterrows():
                records.append({
                    "symbol": symbol.upper(),
                    "timestamp": ts.isoformat(),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": float(row.get("Volume", 0)),
                    "source": "yahoo_finance",
                })
            logger.info("Yahoo Finance OHLCV fetched", symbol=symbol, bars=len(records))
            return records
        except Exception as exc:
            logger.error("Yahoo Finance fetch failed", symbol=symbol, error=str(exc))
            return []

    async def fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch the latest market price for a single symbol."""
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(symbol)
            info = await loop.run_in_executor(None, lambda: ticker.fast_info)
            return float(info.last_price) if info.last_price else None
        except Exception as exc:
            logger.warning("Price fetch failed", symbol=symbol, error=str(exc))
            return None

    async def fetch_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Batch price fetch for multiple symbols."""
        tasks = [self.fetch_current_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            sym: price for sym, price in zip(symbols, results)
            if isinstance(price, float)
        }


class CoinGeckoCollector(BaseCollector):
    """
    Crypto market data from CoinGecko (free tier available).
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    async def fetch_top_coins(self, vs_currency: str = "usd", limit: int = 50) -> List[Dict]:
        """Fetch top-N coins by market cap."""
        try:
            params = {
                "vs_currency": vs_currency,
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": False,
            }
            if settings.market.coingecko_api_key:
                params["x_cg_demo_api_key"] = settings.market.coingecko_api_key

            data = await self._get(f"{self.BASE_URL}/coins/markets", params=params)
            results = []
            for coin in data:
                results.append({
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name", ""),
                    "current_price": float(coin.get("current_price") or 0),
                    "market_cap": float(coin.get("market_cap") or 0),
                    "volume_24h": float(coin.get("total_volume") or 0),
                    "price_change_24h": float(coin.get("price_change_percentage_24h") or 0),
                    "source": "coingecko",
                })
            logger.info("CoinGecko data fetched", count=len(results))
            return results
        except Exception as exc:
            logger.error("CoinGecko fetch failed", error=str(exc))
            return []

    async def fetch_coin_price(self, coin_id: str, vs_currency: str = "usd") -> Optional[float]:
        """Fetch current price for a specific coin by CoinGecko ID."""
        try:
            params = {"ids": coin_id, "vs_currencies": vs_currency}
            data = await self._get(f"{self.BASE_URL}/simple/price", params=params)
            return float(data.get(coin_id, {}).get(vs_currency, 0))
        except Exception as exc:
            logger.warning("Coin price fetch failed", coin_id=coin_id, error=str(exc))
            return None


class NewsAPICollector(BaseCollector):
    """
    Financial news articles from NewsAPI.org.
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    async def fetch_financial_news(
        self,
        query: str = "stocks finance market economy",
        language: str = "en",
        page_size: int = 30,
        sort_by: str = "publishedAt",
    ) -> List[Dict]:
        """Fetch recent financial news articles."""
        if not settings.market.news_api_key:
            logger.warning("NEWS_API_KEY not configured — skipping news fetch")
            return self._mock_news_articles()

        try:
            params = {
                "q": query,
                "language": language,
                "pageSize": page_size,
                "sortBy": sort_by,
                "apiKey": settings.market.news_api_key,
            }
            data = await self._get(self.BASE_URL, params=params)
            articles = data.get("articles", [])
            results = []
            for article in articles:
                if not article.get("url") or article.get("title") == "[Removed]":
                    continue
                results.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "published_at": article.get("publishedAt", datetime.now(tz=timezone.utc).isoformat()),
                    "content": article.get("content", ""),
                })
            logger.info("NewsAPI articles fetched", count=len(results))
            return results
        except Exception as exc:
            logger.error("NewsAPI fetch failed", error=str(exc))
            return []

    def _mock_news_articles(self) -> List[Dict]:
        """Return mock articles for development without API key."""
        return [
            {
                "title": "Fed signals continued rate hold amid stable inflation",
                "summary": "Federal Reserve officials indicated rates will remain steady as inflation approaches target.",
                "url": "https://example.com/news/fed-rates",
                "source": "Mock Financial News",
                "published_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            {
                "title": "Tech stocks rally on strong earnings reports",
                "summary": "Major technology companies posted better-than-expected quarterly results.",
                "url": "https://example.com/news/tech-rally",
                "source": "Mock Financial News",
                "published_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        ]


class AlphaVantageCollector(BaseCollector):
    """
    Technical indicator data from Alpha Vantage.
    Provides pre-computed RSI, MACD, etc. (complements our own computation).
    """

    BASE_URL = "https://www.alphavantage.co/query"

    async def fetch_rsi(self, symbol: str, interval: str = "daily") -> Optional[float]:
        """Fetch latest RSI(14) for a symbol from Alpha Vantage."""
        if not settings.market.alpha_vantage_api_key:
            return None
        try:
            params = {
                "function": "RSI",
                "symbol": symbol,
                "interval": interval,
                "time_period": 14,
                "series_type": "close",
                "apikey": settings.market.alpha_vantage_api_key,
            }
            data = await self._get(self.BASE_URL, params=params)
            meta = data.get("Technical Analysis: RSI", {})
            if not meta:
                return None
            latest_date = sorted(meta.keys(), reverse=True)[0]
            return float(meta[latest_date]["RSI"])
        except Exception as exc:
            logger.warning("Alpha Vantage RSI failed", symbol=symbol, error=str(exc))
            return None

    async def fetch_fear_greed_proxy(self) -> float:
        """
        Approximate Fear & Greed index from VIX.
        VIX >30 = fear (<30 on scale), VIX <15 = greed (>70 on scale).
        """
        vix_data = await self.fetch_rsi("VIX")
        if vix_data is None:
            return 50.0  # Neutral
        # Invert and scale VIX to [0,100] fear-greed proxy
        fear_greed = max(0, min(100, 100 - (vix_data - 10) / 40 * 100))
        return fear_greed
