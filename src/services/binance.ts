import { useEffect, useRef, useState } from 'react';

// Mirrors app/collectors/binance_stream.py: subscribes to BTC/USDT and
// ETH/USDT mini-ticker streams and reconnects with exponential backoff
// (1s, 2s, 4s, capped at 30s). Binance's public WS needs no API key, so
// this can run directly from the client even before a backend exists.

const STREAM_URL = 'wss://stream.binance.com:9443/stream?streams=btcusdt@miniTicker/ethusdt@miniTicker';
const USD_TO_INR = 83.5; // static approximation; swap for a live FX feed later

export interface LiveTick {
  ticker: 'BTC' | 'ETH';
  priceUsd: number;
  priceInr: number;
  changePct24h: number;
  updatedAt: number;
}

export function useBinanceLiveTicks() {
  const [ticks, setTicks] = useState<Record<string, LiveTick>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      const ws = new WebSocket(STREAM_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0;
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data as string);
          const data = payload?.data;
          if (!data?.s) return;
          const symbol: string = data.s; // e.g. BTCUSDT
          const ticker = symbol.startsWith('BTC') ? 'BTC' : symbol.startsWith('ETH') ? 'ETH' : null;
          if (!ticker) return;

          const priceUsd = parseFloat(data.c);
          const openUsd = parseFloat(data.o);
          const changePct24h = openUsd > 0 ? ((priceUsd - openUsd) / openUsd) * 100 : 0;

          setTicks((prev) => ({
            ...prev,
            [ticker]: {
              ticker,
              priceUsd,
              priceInr: priceUsd * USD_TO_INR,
              changePct24h: Math.round(changePct24h * 100) / 100,
              updatedAt: Date.now(),
            },
          }));
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onclose = () => {
        setConnected(false);
        if (!mountedRef.current) return;
        const delay = Math.min(1000 * 2 ** attemptRef.current, 30_000);
        attemptRef.current += 1;
        setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, []);

  return { ticks, connected };
}
