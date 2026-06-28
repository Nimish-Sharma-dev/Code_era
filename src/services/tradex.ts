import { runBehavioralEngine } from '@/engines/behavioralEngine';
import { useFinanceStore } from '@/store/useFinanceStore';
import { genId } from '@/utils/id';
import { Trade } from '@/types';

// Local stand-in for POST /tradex/trades/upload, GET /tradex/behavioral-score,
// GET /tradex/patterns (spec section 5.5). Trades land in the persisted
// store instead of a Postgres `trades` table; the scoring formula matches
// the spec's Day 6 weighting (loss_streak*0.4 + position_delta*0.35 + freq_spike*0.25).

export function parseTradesFromCsv(csv: string): Trade[] {
  const lines = csv.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const header = lines[0].split(',').map((h) => h.trim().toLowerCase());
  const idx = {
    ticker: header.indexOf('ticker'),
    side: header.indexOf('side'),
    qty: header.indexOf('qty'),
    price: header.indexOf('price'),
    timestamp: header.indexOf('timestamp'),
  };

  return lines.slice(1).filter(Boolean).map((line) => {
    const cols = line.split(',');
    return {
      ticker: cols[idx.ticker]?.trim().toUpperCase(),
      side: (cols[idx.side]?.trim().toLowerCase() as Trade['side']) ?? 'buy',
      qty: parseFloat(cols[idx.qty]),
      price: parseFloat(cols[idx.price]),
      timestamp: cols[idx.timestamp]?.trim(),
    };
  }).filter((t) => t.ticker && !Number.isNaN(t.qty) && !Number.isNaN(t.price) && t.timestamp);
}

export function parseTradesFromJson(json: string): Trade[] {
  const parsed = JSON.parse(json);
  const arr = Array.isArray(parsed) ? parsed : parsed?.trades;
  if (!Array.isArray(arr)) return [];
  return arr.map((t: any) => ({
    ticker: String(t.ticker).toUpperCase(),
    side: (t.side ?? 'buy').toLowerCase(),
    qty: Number(t.qty),
    price: Number(t.price),
    timestamp: t.timestamp,
  }));
}

export function uploadTrades(trades: Trade[]): { scanId: string; count: number } {
  useFinanceStore.getState().importTrades(trades);
  return { scanId: genId('scan'), count: trades.length };
}

export function getBehavioralScore() {
  const trades = useFinanceStore.getState().trades;
  return runBehavioralEngine(trades);
}

export function getPatterns() {
  return getBehavioralScore().patterns;
}
