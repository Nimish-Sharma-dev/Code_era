import { genId } from '@/utils/id';
import { ActionableOpportunity, Asset, RiskBand } from '@/types';

// Mirrors app/services/risk_allocator.py: cross-references high-confidence
// Asset signals against the user's free_cash_flow and risk profile. When
// burn_rate_risk is HIGH, volatile (crypto) assets are filtered out
// entirely rather than just down-ranked, matching the spec's gating rule.
export function runRiskAllocator(
  assets: Asset[],
  freeCashFlow: number,
  burnRateRisk: RiskBand,
  riskScore: number, // 0-1
): ActionableOpportunity[] {
  let pool = assets.filter((a) => Math.abs(a.finbertScore) >= 0.3);

  if (burnRateRisk === 'HIGH') {
    pool = pool.filter((a) => a.assetClass !== 'crypto');
  } else if (burnRateRisk === 'MEDIUM' && riskScore < 0.5) {
    pool = pool.filter((a) => a.assetClass !== 'crypto' || a.finbertScore >= 0.6);
  }

  const ranked = [...pool].sort((a, b) => {
    const scoreA = a.finbertScore + (a.momentumTrigger ? 0.2 : 0);
    const scoreB = b.finbertScore + (b.momentumTrigger ? 0.2 : 0);
    return scoreB - scoreA;
  });

  const sizeableCash = Math.max(freeCashFlow, 0);
  const allocationCap = sizeableCash > 0 ? sizeableCash * 0.3 : 25_000;

  return ranked.slice(0, 3).map((asset, idx) => {
    const bullish = asset.finbertScore >= 0;
    const entry = asset.currentPrice;
    const target = bullish ? entry * 1.08 : entry * 0.92;
    const stopLoss = bullish ? entry * 0.97 : entry * 1.03;

    return {
      id: genId('opp'),
      category: 'MARKET_TRADE',
      priority: idx === 0 && asset.momentumTrigger ? 'HIGH' : idx === 0 ? 'MEDIUM' : 'LOW',
      title: `${asset.ticker} ${bullish ? 'Momentum Breakout' : 'Downside Hedge'}`,
      ticker: asset.ticker,
      rationale: `FinBERT sentiment of ${asset.finbertScore.toFixed(2)} across ${asset.momentumSourceCount} sources, sized within your ₹${Math.round(
        allocationCap,
      ).toLocaleString('en-IN')} deployable cash.`,
      parameters: {
        entry: Math.round(entry * 100) / 100,
        target: Math.round(target * 100) / 100,
        stopLoss: Math.round(stopLoss * 100) / 100,
      },
      ctaLabel: `Execute ${bullish ? 'Market Trade' : 'Hedge'}`,
    };
  });
}
