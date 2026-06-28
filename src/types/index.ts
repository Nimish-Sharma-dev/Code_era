// Mirrors the Neo4j graph schema + unified API payloads from the
// SmartWallet AI spec (sections 4.2 and 5.6) so the mocked services below
// can be swapped for real FastAPI calls later with no shape changes.

export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH';

export interface User {
  id: string;
  name: string;
  email: string;
  riskScore: number; // 0-1
}

export interface IncomeSource {
  id: string;
  amount: number;
  frequency: 'monthly' | 'weekly' | 'one_time';
  sourceName: string;
  type: 'salaried' | 'freelance' | 'business' | 'multiple';
}

export interface FixedExpense {
  id: string;
  amount: number;
  category: string;
  label: string;
}

export interface Loan {
  id: string;
  balance: number;
  interestRate: number; // annual %, e.g. 18 for 18%
  label: string;
}

export interface Wallet {
  id: string;
  assetType: 'crypto' | 'stock' | 'mutual_fund' | 'fd' | 'cash';
  label: string;
  symbol: string;
  quantity: number;
  balance: number; // current value in INR
  changePct: number;
}

export type AssetClass = 'crypto' | 'stock';

export interface Asset {
  ticker: string;
  name: string;
  assetClass: AssetClass;
  currentPrice: number;
  changePct24h: number;
  predictionSignal: 'bullish' | 'bearish' | 'neutral';
  finbertScore: number; // -1.0 to 1.0
  momentumTrigger: boolean;
  momentumSourceCount: number;
}

export interface NewsNode {
  id: string;
  headline: string;
  source: string;
  url?: string;
  publishedAt: string;
  tickers: string[];
  finbertScore: number; // -1.0 to 1.0
  label: 'positive' | 'negative' | 'neutral';
}

export interface Trade {
  ticker: string;
  side: 'buy' | 'sell';
  qty: number;
  price: number;
  timestamp: string;
}

export interface BehavioralPattern {
  type: 'revenge_trading' | 'escalation' | 'mental_fatigue' | 'frequency_spike';
  label: string;
  description: string;
  severity: 'detected' | 'warning' | 'clear';
}

export interface BehavioralScore {
  riskScore: number; // 0-100
  band: 'LOW' | 'MEDIUM' | 'HIGH';
  patterns: BehavioralPattern[];
  alertActive: boolean;
  rationale: string;
  winRate: number;
  winRateDeltaPct: number;
  emotionalPnl: number;
  emotionalPnlPct: number;
}

export type OpportunityCategory = 'MARKET_TRADE' | 'CASH_OPTIMIZATION' | 'DEBT_STRATEGY';
export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';

export interface ActionableOpportunity {
  id: string;
  category: OpportunityCategory;
  priority: Priority;
  title: string;
  ticker?: string;
  rationale?: string;
  parameters?: {
    entry?: number;
    stopLoss?: number;
    target?: number;
  };
  annualizedImpact?: number;
  ctaLabel: string;
}

export interface SmartWalletStatus {
  freeCashFlow: number;
  burnRateRisk: RiskBand;
  burnRateMonthly: number;
  activeDebtsDetected: number;
  debtLoadApr: number;
  riskScore: number; // 0-100
}

export interface DebtArbitrageResult {
  strategy: 'INVEST_OVER_DEBT' | 'PAY_DEBT';
  rationale: string;
  highestLoan?: Loan;
  bestYieldTicker?: string;
  bestYieldPct?: number;
}

export interface SentimentMomentumResult {
  triggerActive: boolean;
  assetTarget?: string;
  finbertScore?: number;
  headlineSummary?: string;
  sourceCount?: number;
}

export interface PredictionsPayload {
  smartWalletStatus: SmartWalletStatus;
  engines: {
    debtArbitrage: DebtArbitrageResult;
    sentimentMomentum: SentimentMomentumResult;
  };
  actionableOpportunities: ActionableOpportunity[];
  watchlist: {
    totalValue: number;
    avgChangePct: number;
    gainers: number;
    totalTracked: number;
    topMover: { ticker: string; changePct: number };
  };
}

export type Persona = 'day_trader' | 'swing' | 'investor' | 'crypto';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  persona?: Persona;
  timestamp: string;
}
