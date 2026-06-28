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

export type KlineInterval = '1m' | '5m' | '15m' | '1h';

export interface Candle {
  time: number; // candle open time, unix ms
  open: number;
  high: number;
  low: number;
  close: number;
}

const CANDLE_FLUSH_THROTTLE_MS = 200;

// Seeds from Binance's REST klines endpoint (so the chart isn't empty while
// the WebSocket connects), then keeps the last candle live via the
// kline WebSocket stream — merging ticks into the in-progress candle and
// only appending a new one once a fresh interval boundary opens, per the
// standard "live candle" pattern. Updates are throttled to ~5/sec since the
// stream can tick multiple times a second and a render that often is wasted
// battery for a value nobody can perceive changing that fast.
export function useRealTimeCandles(symbol: 'BTC' | 'ETH', interval: KlineInterval = '1m', limit = 60) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [connected, setConnected] = useState(false);
  const pendingRef = useRef<Candle | null>(null);
  const throttleRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;
    setCandles([]);

    fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}USDT&interval=${interval}&limit=${limit}`)
      .then((res) => res.json())
      .then((rows: any[]) => {
        if (!active || !Array.isArray(rows)) return;
        setCandles(
          rows.map((r) => ({
            time: r[0],
            open: parseFloat(r[1]),
            high: parseFloat(r[2]),
            low: parseFloat(r[3]),
            close: parseFloat(r[4]),
          })),
        );
      })
      .catch(() => {
        // live WS candles below still arrive even if the historical seed fails
      });

    return () => {
      active = false;
    };
  }, [symbol, interval, limit]);

  useEffect(() => {
    let mounted = true;
    let attempt = 0;
    let ws: WebSocket | null = null;

    function flushPending() {
      throttleRef.current = null;
      const incoming = pendingRef.current;
      if (!incoming) return;
      pendingRef.current = null;
      setCandles((prev) => {
        const last = prev[prev.length - 1];
        const merged = last && last.time === incoming.time ? [...prev.slice(0, -1), incoming] : [...prev, incoming];
        return merged.slice(-limit);
      });
    }

    function connect() {
      if (!mounted) return;
      ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}usdt@kline_${interval}`);

      ws.onopen = () => {
        attempt = 0;
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string);
          const k = msg?.k;
          if (!k) return;
          pendingRef.current = {
            time: k.t,
            open: parseFloat(k.o),
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: parseFloat(k.c),
          };
          if (!throttleRef.current) {
            throttleRef.current = setTimeout(flushPending, CANDLE_FLUSH_THROTTLE_MS);
          }
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => setConnected(false);

      ws.onclose = () => {
        setConnected(false);
        if (!mounted) return;
        const delay = Math.min(1000 * 2 ** attempt, 30_000);
        attempt += 1;
        setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      mounted = false;
      if (throttleRef.current) clearTimeout(throttleRef.current);
      ws?.close();
    };
  }, [symbol, interval, limit]);

  return { candles, connected };
}
