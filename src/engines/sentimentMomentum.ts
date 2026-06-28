import { Asset, NewsNode, SentimentMomentumResult } from '@/types';

const MOMENTUM_SCORE_THRESHOLD = 0.7;
const MOMENTUM_SOURCE_THRESHOLD = 5;
const MOMENTUM_WINDOW_MS = 3 * 60 * 60 * 1000; // 3 hours, per spec

// Mirrors the News Sentiment Momentum Trigger: aggregates FinBERT scores
// across recent NewsNodes pointing at a given asset. If a significant
// volume of high-score sentiment articles land within a 3h window, the
// trigger fires and becomes the dashboard's headline_summary.
export function runSentimentMomentum(news: NewsNode[], assets: Asset[]): SentimentMomentumResult {
  const now = Date.now();
  const byTicker = new Map<string, NewsNode[]>();

  for (const item of news) {
    const age = now - new Date(item.publishedAt).getTime();
    if (age > MOMENTUM_WINDOW_MS) continue;
    for (const ticker of item.tickers) {
      const list = byTicker.get(ticker) ?? [];
      list.push(item);
      byTicker.set(ticker, list);
    }
  }

  let best: { ticker: string; avgScore: number; count: number } | undefined;
  for (const [ticker, items] of byTicker) {
    const avgScore = items.reduce((s, i) => s + i.finbertScore, 0) / items.length;
    if (Math.abs(avgScore) >= MOMENTUM_SCORE_THRESHOLD && items.length >= MOMENTUM_SOURCE_THRESHOLD) {
      if (!best || Math.abs(avgScore) > Math.abs(best.avgScore)) {
        best = { ticker, avgScore, count: items.length };
      }
    }
  }

  // Fall back to the seeded/asset-level momentum flag so the dashboard
  // always has something to show even before enough live news accumulates.
  if (!best) {
    const flagged = assets.find((a) => a.momentumTrigger);
    if (flagged) {
      return {
        triggerActive: true,
        assetTarget: flagged.ticker,
        finbertScore: flagged.finbertScore,
        sourceCount: flagged.momentumSourceCount,
        headlineSummary: `${flagged.momentumSourceCount} high-confidence headlines pushed ${flagged.ticker} sentiment to ${flagged.finbertScore.toFixed(2)} in the last 3 hours.`,
      };
    }
    return { triggerActive: false };
  }

  return {
    triggerActive: true,
    assetTarget: best.ticker,
    finbertScore: Math.round(best.avgScore * 100) / 100,
    sourceCount: best.count,
    headlineSummary: `${best.count} high-confidence headlines pushed ${best.ticker} sentiment to ${best.avgScore.toFixed(2)} in the last 3 hours.`,
  };
}
