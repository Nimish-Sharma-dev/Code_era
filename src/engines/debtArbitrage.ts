import { Asset, DebtArbitrageResult, Loan } from '@/types';

// Mirrors app/services/debt_arbitrage.py from the spec: traverse the user's
// loans, find the highest interest_rate loan, and compare it against the
// best available risk-adjusted yield implied by FinBERT-scored assets.
//
// We don't have a backtested yield model in this MVP, so "expected yield"
// is a transparent proxy derived from sentiment + momentum strength. This
// keeps the *decision logic* (compare yield vs APR, recommend a strategy)
// faithful to the spec even though the yield number itself is illustrative.
export function expectedYieldPct(asset: Asset): number {
  const sentimentComponent = asset.finbertScore * 18; // -18%..+18%
  const momentumBoost = asset.momentumTrigger ? 4 : 0;
  return Math.round((sentimentComponent + momentumBoost) * 10) / 10;
}

export function runDebtArbitrage(loans: Loan[], assets: Asset[]): DebtArbitrageResult {
  if (loans.length === 0) {
    return {
      strategy: 'INVEST_OVER_DEBT',
      rationale: 'No active debt detected. Free cash flow can be deployed toward top-ranked opportunities.',
    };
  }

  const highestLoan = [...loans].sort((a, b) => b.interestRate - a.interestRate)[0];
  const ranked = [...assets].sort((a, b) => expectedYieldPct(b) - expectedYieldPct(a));
  const bestAsset = ranked[0];
  const bestYieldPct = bestAsset ? expectedYieldPct(bestAsset) : -Infinity;

  const delta = bestYieldPct - highestLoan.interestRate;

  if (delta > 0 && bestAsset) {
    return {
      strategy: 'INVEST_OVER_DEBT',
      rationale: `${bestAsset.ticker}'s sentiment-implied yield (${bestYieldPct.toFixed(1)}%) outpaces your ${highestLoan.label} APR (${highestLoan.interestRate.toFixed(1)}%) by ${delta.toFixed(1)} pts. A split allocation captures the upside while still servicing minimum debt payments.`,
      highestLoan,
      bestYieldTicker: bestAsset.ticker,
      bestYieldPct,
    };
  }

  return {
    strategy: 'PAY_DEBT',
    rationale: `Your highest-interest debt, ${highestLoan.label}, carries a ${highestLoan.interestRate.toFixed(1)}% APR — higher than any current risk-adjusted opportunity (best: ${bestYieldPct === -Infinity ? 'n/a' : bestYieldPct.toFixed(1) + '%'}). Accelerating paydown is the higher-certainty return right now.`,
    highestLoan,
    bestYieldTicker: bestAsset?.ticker,
    bestYieldPct: bestYieldPct === -Infinity ? undefined : bestYieldPct,
  };
}
