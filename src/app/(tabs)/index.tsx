import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { MetricCard } from '@/components/MetricCard';
import { OpportunityCard } from '@/components/OpportunityCard';
import { TopBar } from '@/components/TopBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Grid2 } from '@/components/ui/Grid2';
import { Icon } from '@/components/ui/Icon';
import { Colors } from '@/constants/theme';
import { useBinanceLiveTicks } from '@/services/binance';
import { getPredictions } from '@/services/market';
import { useFinanceStore } from '@/store/useFinanceStore';
import { PredictionsPayload } from '@/types';

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function DashboardScreen() {
  const router = useRouter();
  const userName = useFinanceStore((s) => s.user.name);
  const { ticks } = useBinanceLiveTicks();
  const [data, setData] = useState<PredictionsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setRefreshing(true) : setLoading(true);
    setError(false);
    try {
      const liveTicks = Object.fromEntries(
        Object.entries(ticks).map(([k, v]) => [k, { priceInr: v.priceInr, changePct24h: v.changePct24h }]),
      );
      const payload = await getPredictions(liveTicks);
      setData(payload);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <View style={styles.screen}>
        <TopBar />
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.screen}>
        <TopBar />
        <View style={styles.center}>
          <Text style={styles.errorText}>Couldn't load your dashboard.</Text>
          <Button label="Tap to retry" variant="ghost" onPress={() => load()} />
        </View>
      </View>
    );
  }

  const { smartWalletStatus, engines, actionableOpportunities, watchlist } = data;

  return (
    <View style={styles.screen}>
      <TopBar />
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={Colors.primary} />}
      >
        <View style={styles.greetingSection}>
          <Text style={styles.greeting}>
            {greeting()}, {userName}
          </Text>
          <Text style={styles.greetingSub}>Welcome to SmartWallet AI</Text>
        </View>

        <Grid2>
          <MetricCard
            label="Watchlist total"
            value={`₹${Math.round(watchlist.totalValue).toLocaleString('en-IN')}`}
            sublabel={`${watchlist.avgChangePct >= 0 ? '+' : ''}${watchlist.avgChangePct}%`}
          />
          <MetricCard
            label="Avg change"
            value={`${watchlist.avgChangePct}%`}
            sublabel={watchlist.avgChangePct >= 0 ? 'Healthy' : 'Watch closely'}
          />
          <MetricCard
            label="Gainers"
            value={`${watchlist.gainers} / ${watchlist.totalTracked}`}
            sublabel={watchlist.gainers >= watchlist.totalTracked / 2 ? 'Bullish trend' : 'Mixed signals'}
          />
          <MetricCard
            label="Top mover"
            value={watchlist.topMover.ticker}
            sublabel={`${watchlist.topMover.changePct >= 0 ? '+' : ''}${watchlist.topMover.changePct}%`}
          />
        </Grid2>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>SmartWallet Status</Text>
          <Grid2>
            <MetricCard
              variant="low"
              label="FCF"
              value={`₹${Math.round(smartWalletStatus.freeCashFlow).toLocaleString('en-IN')}`}
              badge={{ label: smartWalletStatus.burnRateRisk, tone: 'gain' }}
            />
            <MetricCard
              variant="low"
              label="Burn rate"
              value={`₹${Math.round(smartWalletStatus.burnRateMonthly).toLocaleString('en-IN')}/mo`}
              badge={{
                label: smartWalletStatus.burnRateRisk === 'LOW' ? 'HEALTHY' : smartWalletStatus.burnRateRisk,
                tone: smartWalletStatus.burnRateRisk === 'HIGH' ? 'loss' : 'gain',
              }}
            />
            <MetricCard
              variant="low"
              label="Debt load"
              value={`${smartWalletStatus.debtLoadApr}%`}
              badge={{ label: 'APR', tone: smartWalletStatus.debtLoadApr > 0 ? 'loss' : 'neutral' }}
            />
            <MetricCard
              variant="low"
              label="Risk score"
              value={`${smartWalletStatus.riskScore}/100`}
              badge={{
                label: smartWalletStatus.riskScore >= 70 ? 'HIGH' : smartWalletStatus.riskScore >= 40 ? 'MEDIUM' : 'LOW',
                tone: smartWalletStatus.riskScore >= 70 ? 'loss' : smartWalletStatus.riskScore >= 40 ? 'warning' : 'gain',
              }}
            />
          </Grid2>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Opportunities</Text>

          {engines.sentimentMomentum.triggerActive && engines.sentimentMomentum.assetTarget && (
            <Pressable onPress={() => router.push(`/asset/${engines.sentimentMomentum.assetTarget}`)}>
              <Card style={styles.sentimentCard}>
                <View style={styles.sentimentLeft}>
                  <View style={styles.sentimentIcon}>
                    <Icon name="analytics" size={20} color={Colors.primary} />
                  </View>
                  <View>
                    <Text style={styles.sentimentTicker}>{engines.sentimentMomentum.assetTarget}</Text>
                    <Text style={styles.sentimentSub}>Sentiment momentum</Text>
                  </View>
                </View>
                <Badge label={`FinBERT: ${engines.sentimentMomentum.finbertScore?.toFixed(2)}`} tone="primary" uppercase={false} />
              </Card>
            </Pressable>
          )}

          {actionableOpportunities.map((opp) => (
            <OpportunityCard
              key={opp.id}
              opportunity={opp}
              onPress={() => router.push(opp.ticker ? `/asset/${opp.ticker}` : '/(tabs)/portfolio')}
            />
          ))}

          {actionableOpportunities.length === 0 && (
            <Text style={styles.emptyText}>No high-confidence opportunities right now — check back soon.</Text>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  errorText: { fontFamily: 'Inter_500Medium', fontSize: 14, color: Colors.onSurfaceVariant },
  scroll: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 32, gap: 24 },
  greetingSection: { gap: 2 },
  greeting: { fontFamily: 'Inter_700Bold', fontSize: 20, color: Colors.onSurface },
  greetingSub: { fontFamily: 'Inter_500Medium', fontSize: 12, color: Colors.onSurfaceVariant },
  section: { gap: 16 },
  sectionTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 18, color: Colors.onSurface, paddingHorizontal: 4 },
  sentimentCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(28,31,42,0.6)',
  },
  sentimentLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  sentimentIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: Colors.surfaceContainerHighest,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sentimentTicker: { fontFamily: 'Inter_700Bold', fontSize: 14, color: Colors.onSurface },
  sentimentSub: { fontFamily: 'Inter_500Medium', fontSize: 12, color: Colors.onSurfaceVariant },
  emptyText: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.muted, textAlign: 'center', paddingVertical: 12 },
});
