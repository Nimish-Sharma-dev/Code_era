import { BehavioralPattern, BehavioralScore, Trade } from '@/types';

interface RoundTrip {
  ticker: string;
  qty: number;
  notional: number;
  pnl: number;
  isWin: boolean;
  openedAt: number;
  closedAt: number;
}

function buildRoundTrips(trades: Trade[]): RoundTrip[] {
  const sorted = [...trades].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const openQueues = new Map<string, { qty: number; price: number; ts: number }[]>();
  const roundTrips: RoundTrip[] = [];

  for (const trade of sorted) {
    const ts = new Date(trade.timestamp).getTime();
    if (trade.side === 'buy') {
      const queue = openQueues.get(trade.ticker) ?? [];
      queue.push({ qty: trade.qty, price: trade.price, ts });
      openQueues.set(trade.ticker, queue);
      continue;
    }

    // sell: close against the oldest open lot(s) for that ticker (FIFO)
    const queue = openQueues.get(trade.ticker) ?? [];
    let remaining = trade.qty;
    while (remaining > 0 && queue.length > 0) {
      const lot = queue[0];
      const matched = Math.min(lot.qty, remaining);
      const pnl = (trade.price - lot.price) * matched;
      roundTrips.push({
        ticker: trade.ticker,
        qty: matched,
        notional: lot.price * matched,
        pnl,
        isWin: pnl > 0,
        openedAt: lot.ts,
        closedAt: ts,
      });
      lot.qty -= matched;
      remaining -= matched;
      if (lot.qty <= 0) queue.shift();
    }
    openQueues.set(trade.ticker, queue);
  }

  return roundTrips.sort((a, b) => a.closedAt - b.closedAt);
}

const REVENGE_WINDOW_MS = 15 * 60 * 1000;

export function runBehavioralEngine(trades: Trade[]): BehavioralScore {
  if (trades.length === 0) {
    return {
      riskScore: 0,
      band: 'LOW',
      patterns: [
        { type: 'revenge_trading', label: 'Revenge Trading', description: 'Rapid entry after loss', severity: 'clear' },
        { type: 'escalation', label: 'Escalation', description: 'Increasing size on bias', severity: 'clear' },
        { type: 'mental_fatigue', label: 'Mental Fatigue', description: 'Low decision quality', severity: 'clear' },
      ],
      alertActive: false,
      rationale: 'Import your trade journal to generate a behavioral risk score.',
      winRate: 0,
      winRateDeltaPct: 0,
      emotionalPnl: 0,
      emotionalPnlPct: 0,
    };
  }

  const roundTrips = buildRoundTrips(trades);

  // 1. Trailing loss streak (most recent consecutive losses)
  let lossStreak = 0;
  for (let i = roundTrips.length - 1; i >= 0; i--) {
    if (roundTrips[i].isWin) break;
    lossStreak += 1;
  }
  const lossStreakScore = Math.min(lossStreak / 3, 1) * 100;

  // 2. Position escalation after a loss, and revenge-trading detection
  let escalationCount = 0;
  let revengeDetected = false;
  let revengeRationale = '';
  let emotionalPnl = 0;

  for (let i = 1; i < roundTrips.length; i++) {
    const prev = roundTrips[i - 1];
    const curr = roundTrips[i];
    if (!prev.isWin && curr.notional > prev.notional) {
      escalationCount += 1;
      const gapMs = curr.openedAt - prev.closedAt;
      if (gapMs >= 0 && gapMs <= REVENGE_WINDOW_MS) {
        revengeDetected = true;
        emotionalPnl += curr.pnl;
        if (!revengeRationale) {
          const lossTime = new Date(prev.closedAt).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          });
          revengeRationale = `Your current state indicates "Revenge Bias" after the ${lossTime} losing trade on ${prev.ticker}. Recommendation: take a 15-minute cooldown.`;
        }
      }
    }
  }
  const escalationScore = Math.min((escalationCount / roundTrips.length) * 100, 100);

  // 3. Trading frequency spike
  const timestamps = trades.map((t) => new Date(t.timestamp).getTime()).sort((a, b) => a - b);
  const spanHours = Math.max((timestamps[timestamps.length - 1] - timestamps[0]) / 3_600_000, 1 / 60);
  const avgPerHour = trades.length / spanHours;
  const freqSpikeScore = Math.min((avgPerHour / 6) * 100, 100);

  const riskScore = Math.round(lossStreakScore * 0.4 + escalationScore * 0.35 + freqSpikeScore * 0.25);
  const band = riskScore >= 70 ? 'HIGH' : riskScore >= 40 ? 'MEDIUM' : 'LOW';

  // Late-night trades (22:00–05:00) as a mental-fatigue proxy
  const lateNightTrades = trades.filter((t) => {
    const hour = new Date(t.timestamp).getHours();
    return hour >= 22 || hour < 5;
  });
  const fatigueSeverity: BehavioralPattern['severity'] =
    lateNightTrades.length === 0 ? 'clear' : lateNightTrades.length >= 3 ? 'detected' : 'warning';

  const patterns: BehavioralPattern[] = [
    {
      type: 'revenge_trading',
      label: 'Revenge Trading',
      description: 'Rapid entry after loss',
      severity: revengeDetected ? 'detected' : 'clear',
    },
    {
      type: 'escalation',
      label: 'Escalation',
      description: 'Increasing size on bias',
      severity: escalationScore === 0 ? 'clear' : escalationScore < 50 ? 'warning' : 'detected',
    },
    {
      type: 'mental_fatigue',
      label: 'Mental Fatigue',
      description: 'Low decision quality',
      severity: fatigueSeverity,
    },
  ];

  const wins = roundTrips.filter((r) => r.isWin).length;
  const winRate = roundTrips.length > 0 ? (wins / roundTrips.length) * 100 : 0;
  const mid = Math.floor(roundTrips.length / 2);
  const firstHalf = roundTrips.slice(0, mid);
  const secondHalf = roundTrips.slice(mid);
  const winRateOf = (rts: RoundTrip[]) =>
    rts.length > 0 ? (rts.filter((r) => r.isWin).length / rts.length) * 100 : 0;
  const winRateDeltaPct = Math.round((winRateOf(secondHalf) - winRateOf(firstHalf)) * 10) / 10;

  const totalNotional = roundTrips.reduce((s, r) => s + r.notional, 0) || 1;
  const emotionalPnlPct = Math.round((emotionalPnl / totalNotional) * 1000) / 10;

  const rationale =
    revengeRationale ||
    (band === 'HIGH'
      ? 'Trading frequency and position sizing suggest elevated stress. Consider pausing before the next entry.'
      : band === 'MEDIUM'
        ? 'Some early signs of emotional trading. Stay disciplined with position sizing.'
        : 'No significant behavioral risk patterns detected in this trade journal.');

  return {
    riskScore,
    band,
    patterns,
    alertActive: band === 'HIGH',
    rationale,
    winRate: Math.round(winRate * 10) / 10,
    winRateDeltaPct,
    emotionalPnl: Math.round(emotionalPnl),
    emotionalPnlPct,
  };
}
