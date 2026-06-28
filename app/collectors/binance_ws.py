"""
Binance WebSocket collector for real-time crypto price streaming.

Connects to Binance's public WebSocket streams (no API key required
for market data). Streams are multiplexed using a combined stream URL.

Architecture:
  - One persistent async WebSocket connection per worker.
  - Prices are written to Redis (TTL=60s) immediately on receipt.
  - Periodically flushed to PostgreSQL by the Celery beat task.
  - Reconnection with exponential backoff on disconnect.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Dict, List, Optional

import websockets
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)
import logging

from app.core.logging import get_logger
from app.db.postgres.redis_client import get_redis

logger = get_logger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream"

# Default symbols to stream (BTC, ETH, BNB, SOL, XRP)
DEFAULT_SYMBOLS = ["btcusdt", "ethusdt", "bnbusdt", "solusdt", "xrpusdt"]


class BinanceWebSocketCollector:
    """
    Real-time crypto price collector via Binance WebSocket streams.

    Usage:
        collector = BinanceWebSocketCollector(symbols=["btcusdt", "ethusdt"])
        await collector.start()        # runs indefinitely
        await collector.stop()
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        on_price_update: Optional[Callable] = None,
    ) -> None:
        self._symbols = [s.lower() for s in (symbols or DEFAULT_SYMBOLS)]
        self._on_price_update = on_price_update or self._default_handler
        self._running = False
        self._ws = None
        self._prices: Dict[str, float] = {}

    def _build_stream_url(self) -> str:
        """Combine multiple mini-ticker streams into one connection."""
        streams = "/".join(f"{sym}@miniTicker" for sym in self._symbols)
        return f"{BINANCE_WS_BASE}?streams={streams}"

    async def start(self) -> None:
        """Start the WebSocket listener. Runs until stop() is called."""
        self._running = True
        logger.info("Binance WebSocket starting", symbols=self._symbols)
        await self._connect_loop()

    async def stop(self) -> None:
        """Gracefully stop the collector."""
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info("Binance WebSocket stopped")

    async def _connect_loop(self) -> None:
        """Connection loop with exponential backoff on failure."""
        backoff = 1
        while self._running:
            try:
                url = self._build_stream_url()
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=2 ** 20,  # 1MB max message
                ) as ws:
                    self._ws = ws
                    backoff = 1  # Reset backoff on successful connection
                    logger.info("Binance WebSocket connected")
                    await self._message_loop(ws)
            except websockets.exceptions.ConnectionClosed as exc:
                logger.warning("WebSocket closed", code=exc.code, reason=exc.reason)
            except Exception as exc:
                logger.error("WebSocket error", error=str(exc))

            if self._running:
                logger.info(f"Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _message_loop(self, ws) -> None:
        """Process incoming WebSocket messages."""
        async for raw_message in ws:
            if not self._running:
                break
            try:
                data = json.loads(raw_message)
                stream_data = data.get("data", data)
                await self._process_ticker(stream_data)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Message parse error", error=str(exc))

    async def _process_ticker(self, ticker: dict) -> None:
        """
        Process a mini-ticker message.

        Mini-ticker format:
          e: event type, s: symbol, c: close price, v: volume, ...
        """
        symbol = ticker.get("s", "").upper()
        close_price = float(ticker.get("c", 0))
        volume = float(ticker.get("v", 0))

        if not symbol or close_price <= 0:
            return

        self._prices[symbol] = close_price
        await self._on_price_update(symbol, close_price, volume)

    @staticmethod
    async def _default_handler(symbol: str, price: float, volume: float) -> None:
        """Default handler: cache price in Redis (TTL=60s)."""
        try:
            redis = get_redis()
            await redis.setex(
                f"binance:price:{symbol}",
                60,
                json.dumps({"price": price, "volume": volume}),
            )
        except Exception as exc:
            logger.warning("Redis price cache failed", symbol=symbol, error=str(exc))

    def get_cached_price(self, symbol: str) -> Optional[float]:
        """Return the most recently received price for a symbol (in-memory)."""
        return self._prices.get(symbol.upper())

    def get_all_prices(self) -> Dict[str, float]:
        """Return all currently tracked prices."""
        return dict(self._prices)


async def run_binance_collector(symbols: Optional[List[str]] = None) -> None:
    """Entry point for running the collector as a standalone async task."""
    collector = BinanceWebSocketCollector(symbols=symbols)
    try:
        await collector.start()
    except KeyboardInterrupt:
        await collector.stop()
