// Lightweight stand-in for the spec's FinBERT pipeline (ProsusAI/finbert).
// Running the real HuggingFace model isn't feasible on-device, and this is
// a frontend-only build for now — so headlines are scored with a financial
// sentiment lexicon, normalised to the same -1.0..+1.0 range FinBERT would
// produce. Swap `scoreHeadline` for a call to app/collectors/finbert_pipeline.py
// once the FastAPI backend is live; nothing else in the app needs to change.

const POSITIVE_WORDS = [
  'surge', 'surges', 'rally', 'rallies', 'soar', 'soars', 'gain', 'gains', 'jump', 'jumps',
  'beat', 'beats', 'record', 'growth', 'profit', 'profits', 'upgrade', 'upgraded', 'bullish',
  'outperform', 'partnership', 'partners', 'breakthrough', 'strong', 'rebound', 'recovery',
  'inflows', 'optimis', 'expansion', 'accelerat', 'boost', 'boosts', 'higher', 'rises', 'rise',
];

const NEGATIVE_WORDS = [
  'plunge', 'plunges', 'crash', 'crashes', 'slump', 'slumps', 'fall', 'falls', 'drop', 'drops',
  'miss', 'misses', 'downgrade', 'downgraded', 'bearish', 'underperform', 'lawsuit', 'probe',
  'investigation', 'antitrust', 'scrutiny', 'hurdle', 'hurdles', 'recall', 'layoff', 'layoffs',
  'weak', 'losses', 'loss', 'decline', 'declines', 'volatil', 'concern', 'concerns', 'risk',
  'sell-off', 'selloff', 'lower', 'cuts', 'cut', 'fraud', 'regulatory',
];

export function scoreHeadline(headline: string): number {
  const text = headline.toLowerCase();
  let score = 0;
  let hits = 0;

  for (const word of POSITIVE_WORDS) {
    if (text.includes(word)) {
      score += 1;
      hits += 1;
    }
  }
  for (const word of NEGATIVE_WORDS) {
    if (text.includes(word)) {
      score -= 1;
      hits += 1;
    }
  }

  if (hits === 0) return 0;
  // Normalise into -1..1, with diminishing returns for many keyword hits
  // (mirrors how a real classifier's confidence saturates).
  const normalised = Math.tanh(score / Math.max(hits, 2));
  return Math.round(normalised * 100) / 100;
}

export function labelForScore(score: number): 'positive' | 'negative' | 'neutral' {
  if (score > 0.15) return 'positive';
  if (score < -0.15) return 'negative';
  return 'neutral';
}
