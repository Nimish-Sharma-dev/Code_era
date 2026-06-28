import { Asset, NewsNode, User } from '@/types';

// Seed data per the spec's Day 3 / Day 7 build plan: 6 tracked assets and a
// pool of pre-scored demo headlines so the app never depends on live
// FinBERT/Marketaux quota for the first paint or for offline demos.

export const SEED_USER: User = {
  id: 'demo-user-1',
  name: 'Alex',
  email: 'alex@smartwallet.ai',
  riskScore: 0.62,
};

export const SEED_ASSETS: Asset[] = [
  {
    ticker: 'BTC',
    name: 'Bitcoin',
    assetClass: 'crypto',
    currentPrice: 6_77_04_50 / 100, // placeholder, overwritten by live Binance feed
    changePct24h: 1.8,
    predictionSignal: 'bullish',
    finbertScore: 0.55,
    momentumTrigger: false,
    momentumSourceCount: 3,
  },
  {
    ticker: 'ETH',
    name: 'Ethereum',
    assetClass: 'crypto',
    currentPrice: 1_94_200,
    changePct24h: 5.12,
    predictionSignal: 'bullish',
    finbertScore: 0.84,
    momentumTrigger: true,
    momentumSourceCount: 6,
  },
  {
    ticker: 'NVDA',
    name: 'Nvidia Corp',
    assetClass: 'stock',
    currentPrice: 1245.6,
    changePct24h: 2.45,
    predictionSignal: 'bullish',
    finbertScore: 0.89,
    momentumTrigger: true,
    momentumSourceCount: 5,
  },
  {
    ticker: 'AAPL',
    name: 'Apple Inc',
    assetClass: 'stock',
    currentPrice: 228.4,
    changePct24h: 0.6,
    predictionSignal: 'bullish',
    finbertScore: 0.62,
    momentumTrigger: false,
    momentumSourceCount: 2,
  },
  {
    ticker: 'MSFT',
    name: 'Microsoft Corp',
    assetClass: 'stock',
    currentPrice: 452.1,
    changePct24h: -0.2,
    predictionSignal: 'neutral',
    finbertScore: 0.1,
    momentumTrigger: false,
    momentumSourceCount: 1,
  },
  {
    ticker: 'GOOGL',
    name: 'Alphabet Inc',
    assetClass: 'stock',
    currentPrice: 178.9,
    changePct24h: -1.4,
    predictionSignal: 'bearish',
    finbertScore: -0.76,
    momentumTrigger: false,
    momentumSourceCount: 4,
  },
];

export const SEED_NEWS: NewsNode[] = [
  {
    id: 'news-1',
    headline: 'Nvidia partners with major cloud providers for next-gen AI infrastructure rollout.',
    source: 'Reuters',
    publishedAt: new Date(Date.now() - 14 * 60_000).toISOString(),
    tickers: ['NVDA', 'AI', 'Cloud'],
    finbertScore: 0.92,
    label: 'positive',
  },
  {
    id: 'news-2',
    headline: 'Tesla faces new regulatory hurdles in key international markets following safety review.',
    source: 'Bloomberg',
    publishedAt: new Date(Date.now() - 32 * 60_000).toISOString(),
    tickers: ['TSLA', 'EV'],
    finbertScore: -0.45,
    label: 'negative',
  },
  {
    id: 'news-3',
    headline: 'Ethereum sees surge in network activity as institutional inflows accelerate.',
    source: 'CoinDesk',
    publishedAt: new Date(Date.now() - 50 * 60_000).toISOString(),
    tickers: ['ETH'],
    finbertScore: 0.84,
    label: 'positive',
  },
  {
    id: 'news-4',
    headline: 'Alphabet faces fresh antitrust scrutiny over ad-tech dominance in EU markets.',
    source: 'Financial Times',
    publishedAt: new Date(Date.now() - 70 * 60_000).toISOString(),
    tickers: ['GOOGL'],
    finbertScore: -0.76,
    label: 'negative',
  },
  {
    id: 'news-5',
    headline: 'Apple supplier reports record quarterly shipments ahead of holiday season.',
    source: 'CNBC',
    publishedAt: new Date(Date.now() - 95 * 60_000).toISOString(),
    tickers: ['AAPL'],
    finbertScore: 0.62,
    label: 'positive',
  },
  {
    id: 'news-6',
    headline: 'Bitcoin consolidates above key support as ETF inflows remain steady.',
    source: 'CoinDesk',
    publishedAt: new Date(Date.now() - 120 * 60_000).toISOString(),
    tickers: ['BTC'],
    finbertScore: 0.55,
    label: 'positive',
  },
];

export const DEMO_TRADE_CSV = `ticker,side,qty,price,timestamp
NVDA,buy,10,880.20,2026-06-20T09:31:00Z
NVDA,sell,10,872.10,2026-06-20T09:48:00Z
NVDA,buy,18,871.50,2026-06-20T09:50:00Z
NVDA,sell,18,860.00,2026-06-20T10:05:00Z
ETH,buy,2,193000,2026-06-21T14:10:00Z
ETH,sell,2,196500,2026-06-21T16:40:00Z
BTC,buy,0.05,6700000,2026-06-22T08:15:00Z
NVDA,buy,25,865.00,2026-06-23T09:45:00Z
NVDA,sell,25,850.40,2026-06-23T09:58:00Z
NVDA,buy,40,849.00,2026-06-23T10:01:00Z
`;
