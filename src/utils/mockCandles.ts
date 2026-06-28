import { Candle } from '@/services/binance';

// Deterministic illustrative candles for asset classes we don't have a free
// live OHLC feed for (stocks — Alpha Vantage/Polygon both require API keys
// we don't have). Seeded by ticker so the same asset always renders the
// same shape rather than jumping around on every render.
function seededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

function hashTicker(ticker: string): number {
  let hash = 0;
  for (let i = 0; i < ticker.length; i++) hash = (hash * 31 + ticker.charCodeAt(i)) % 100000;
  return hash || 1;
}

export function generateMockCandles(ticker: string, endPrice: number, count = 40): Candle[] {
  const rand = seededRandom(hashTicker(ticker));
  const volatility = endPrice * 0.012;
  const candles: Candle[] = [];

  // Walk backwards from the known current price so the series ends exactly there.
  let price = endPrice;
  const now = Date.now();
  const intervalMs = 60_000;

  for (let i = count - 1; i >= 0; i--) {
    const close = price;
    const open = close + (rand() - 0.5) * volatility;
    const high = Math.max(open, close) + rand() * volatility * 0.6;
    const low = Math.min(open, close) - rand() * volatility * 0.6;
    candles.unshift({
      time: now - i * intervalMs,
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
    });
    price = open;
  }

  return candles;
}
