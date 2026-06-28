import { SEED_ASSETS } from '@/data/seed';
import { runDebtArbitrage } from '@/engines/debtArbitrage';
import { runRiskAllocator } from '@/engines/riskAllocator';
import { runSentimentMomentum } from '@/engines/sentimentMomentum';
import { useFinanceStore } from '@/store/useFinanceStore';
import { genId } from '@/utils/id';
import { Asset, ActionableOpportunity, NewsNode, PredictionsPayload } from '@/types';
import { fetchLiveNews } from './newsdata';

// Local stand-in for GET /market/predictions, /market/assets, /market/news,
// /market/sentiment/:ticker (spec section 5.3). Reads live BTC/ETH prices
// when supplied, otherwise falls back to seed data — same contract a real
// FastAPI handler reading Redis + Neo4j would expose.

export function getAssets(
  liveTicks?: Record<string, { priceInr: number; changePct24h: number }>,
  type?: 'crypto' | 'stock',
): Asset[] {
  const merged = SEED_ASSETS.map((asset) => {
    const live = liveTicks?.[asset.ticker];
    if (!live) return asset;
    return { ...asset, currentPrice: live.priceInr, changePct24h: live.changePct24h };
  });
  return type ? merged.filter((a) => a.assetClass === type) : merged;
}

export async function getNews(ticker?: string): Promise<NewsNode[]> {
  return fetchLiveNews(ticker);
}

export async function getSentiment(ticker: string) {
  const news = await fetchLiveNews(ticker);
  const matched = news.filter((n) => n.tickers.includes(ticker));
  const avgScore =
    matched.length > 0 ? matched.reduce((s, n) => s + n.finbertScore, 0) / matched.length : 0;
  return {
    ticker,
    aggregatedScore: Math.round(avgScore * 100) / 100,
    momentumSourceCount: matched.length,
    direction: avgScore > 0 ? 'bullish' : avgScore < 0 ? 'bearish' : 'neutral',
    headlines: matched.slice(0, 6),
  };
}

function buildCashOptimizationOpportunity(freeCashFlow: number): ActionableOpportunity | null {
  if (freeCashFlow <= 0) return null;
  const annualizedImpact = Math.round(freeCashFlow * 0.04 * 12); // 4%/mo idle-cash savings proxy
  return {
    id: genId('opp'),
    category: 'CASH_OPTIMIZATION',
    priority: 'LOW',
    title: 'Move idle cash into a liquid fund',
    rationale: `You're carrying ₹${Math.round(freeCashFlow).toLocaleString('en-IN')}/mo in free cash flow. Sweeping the unused portion into a liquid fund captures yield instead of letting it sit idle.`,
    annualizedImpact,
    ctaLabel: 'Review Cash Optimization',
  };
}

function buildDebtOpportunity(rationale: string, loanLabel: string): ActionableOpportunity {
  return {
    id: genId('opp'),
    category: 'DEBT_STRATEGY',
    priority: 'MEDIUM',
    title: `Consolidate ${loanLabel}`,
    rationale,
    ctaLabel: 'Review Consolidation Plan',
  };
}

export async function getPredictions(
  liveTicks?: Record<string, { priceInr: number; changePct24h: number }>,
  riskFilter?: 'low' | 'medium' | 'high',
): Promise<PredictionsPayload> {
  const state = useFinanceStore.getState();
  const assets = getAssets(liveTicks);
  const news = await fetchLiveNews();

  const freeCashFlow = state.freeCashFlow();
  const burnRateRisk = state.burnRateRisk();
  const riskScore = state.riskScore100();

  let pool = assets;
  if (riskFilter === 'low') pool = assets.filter((a) => a.assetClass !== 'crypto');

  const marketOpportunities = runRiskAllocator(pool, freeCashFlow, burnRateRisk, state.user.riskScore);
  const debtArbitrage = runDebtArbitrage(state.loans, assets);
  const sentimentMomentum = runSentimentMomentum(news, assets);

  const opportunities: ActionableOpportunity[] = [...marketOpportunities];
  if (debtArbitrage.strategy === 'PAY_DEBT' && debtArbitrage.highestLoan) {
    opportunities.push(
      buildDebtOpportunity(debtArbitrage.rationale, debtArbitrage.highestLoan.label),
    );
  } else {
    const cashOpp = buildCashOptimizationOpportunity(freeCashFlow);
    if (cashOpp) opportunities.push(cashOpp);
  }

  const sorted = assets.slice().sort((a, b) => b.changePct24h - a.changePct24h);
  const topMover = sorted[0] ?? assets[0];
  const gainers = assets.filter((a) => a.changePct24h > 0).length;
  const avgChangePct =
    assets.length > 0 ? assets.reduce((s, a) => s + a.changePct24h, 0) / assets.length : 0;
  const totalValue = state.totalWalletValue();

  return {
    smartWalletStatus: {
      freeCashFlow,
      burnRateRisk,
      burnRateMonthly: state.totalMonthlyExpenses(),
      activeDebtsDetected: state.loans.length,
      debtLoadApr: state.highestInterestLoan()?.interestRate ?? 0,
      riskScore,
    },
    engines: {
      debtArbitrage,
      sentimentMomentum,
    },
    actionableOpportunities: opportunities,
    watchlist: {
      totalValue,
      avgChangePct: Math.round(avgChangePct * 100) / 100,
      gainers,
      totalTracked: assets.length,
      topMover: { ticker: topMover?.ticker ?? '—', changePct: topMover?.changePct24h ?? 0 },
    },
  };
}
