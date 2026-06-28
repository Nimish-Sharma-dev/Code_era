import { File } from 'expo-file-system';
import { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { RiskGauge } from '@/components/charts/RiskGauge';
import { TopBar } from '@/components/TopBar';
import { Card } from '@/components/ui/Card';
import { Icon, IconName } from '@/components/ui/Icon';
import { Colors, Radii } from '@/constants/theme';
import { DEMO_TRADE_CSV } from '@/data/seed';
import { parseTradesFromCsv, parseTradesFromJson, uploadTrades } from '@/services/tradex';
import { useFinanceStore } from '@/store/useFinanceStore';
import { runBehavioralEngine } from '@/engines/behavioralEngine';

const PATTERN_ICON: Record<string, IconName> = {
  revenge_trading: 'history',
  escalation: 'trendingUp',
  mental_fatigue: 'sleep',
  frequency_spike: 'trendingUp',
};

const SEVERITY_COLOR = {
  detected: Colors.loss,
  warning: Colors.warning,
  clear: Colors.secondary,
} as const;

export default function TradeXScreen() {
  const trades = useFinanceStore((s) => s.trades);
  const importTrades = useFinanceStore((s) => s.importTrades);
  const score = useMemo(() => runBehavioralEngine(trades), [trades]);
  const [importing, setImporting] = useState(false);

  async function handlePickFile() {
    setImporting(true);
    try {
      const picked = await File.pickFileAsync({ mimeTypes: ['text/csv', 'application/json', 'text/*'] });
      if (picked.canceled) return;
      const content = await picked.result.text();
      const isJson = picked.result.name.toLowerCase().endsWith('.json');
      const parsed = isJson ? parseTradesFromJson(content) : parseTradesFromCsv(content);
      if (parsed.length === 0) {
        Alert.alert('No trades found', 'That file did not contain any rows we could parse.');
        return;
      }
      uploadTrades(parsed);
    } catch (e: any) {
      Alert.alert('Import failed', e?.message ?? 'Could not read that file.');
    } finally {
      setImporting(false);
    }
  }

  function handleLoadDemo() {
    importTrades(parseTradesFromCsv(DEMO_TRADE_CSV));
  }

  return (
    <View style={styles.screen}>
      <TopBar />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {score.alertActive && (
          <View style={styles.alertBanner}>
            <Icon name="warning" size={20} color={Colors.loss} />
            <View style={styles.alertTextWrap}>
              <Text style={styles.alertTitle}>Emotional risk alert</Text>
              <Text style={styles.alertBody}>Recent trading activity suggests high stress levels detected.</Text>
            </View>
          </View>
        )}

        <Card style={styles.gaugeCard}>
          <Text style={styles.gaugeTitle}>Behavioral Score</Text>
          <RiskGauge score={score.riskScore} band={score.band} />
          <Text style={styles.rationale}>{score.rationale}</Text>
        </Card>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pattern Detection</Text>
          {score.patterns.map((p) => {
            const color = SEVERITY_COLOR[p.severity];
            return (
              <View key={p.type} style={styles.patternRow}>
                <View style={styles.patternLeft}>
                  <View style={styles.patternIcon}>
                    <Icon name={PATTERN_ICON[p.type] ?? 'history'} size={20} color={color} />
                  </View>
                  <View>
                    <Text style={styles.patternLabel}>{p.label}</Text>
                    <Text style={styles.patternDesc}>{p.description}</Text>
                  </View>
                </View>
                <View style={[styles.patternBadge, { backgroundColor: `${color}1A`, borderColor: `${color}4D` }]}>
                  <Text style={[styles.patternBadgeText, { color }]}>{p.severity.toUpperCase()}</Text>
                </View>
              </View>
            );
          })}
        </View>

        <Pressable style={styles.uploadArea} onPress={handlePickFile} disabled={importing}>
          <Icon name="upload" size={32} color={Colors.outline} />
          <Text style={styles.uploadTitle}>Import Trade Journal</Text>
          <Text style={styles.uploadBody}>Upload CSV or JSON from MetaTrader/TradingView</Text>
          <View style={styles.selectFileBtn}>
            <Text style={styles.selectFileText}>{importing ? 'Reading file…' : 'Select File'}</Text>
          </View>
        </Pressable>

        <Pressable style={styles.demoLink} onPress={handleLoadDemo}>
          <Text style={styles.demoLinkText}>Use demo trade journal instead</Text>
        </Pressable>

        <View style={styles.insightsRow}>
          <Card style={styles.insightCard}>
            <Text style={styles.insightLabel}>WIN RATE</Text>
            <View style={styles.insightValueRow}>
              <Text style={styles.insightValue}>{score.winRate}%</Text>
              <Text style={[styles.insightDelta, { color: score.winRateDeltaPct >= 0 ? Colors.secondary : Colors.loss }]}>
                {score.winRateDeltaPct >= 0 ? '+' : ''}
                {score.winRateDeltaPct}%
              </Text>
            </View>
          </Card>
          <Card style={styles.insightCard}>
            <Text style={styles.insightLabel}>EMOTIONAL P/L</Text>
            <View style={styles.insightValueRow}>
              <Text style={styles.insightValue}>
                {score.emotionalPnl < 0 ? '-' : ''}₹{Math.abs(Math.round(score.emotionalPnl)).toLocaleString('en-IN')}
              </Text>
              <Text style={[styles.insightDelta, { color: Colors.loss }]}>{score.emotionalPnlPct}%</Text>
            </View>
          </Card>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 32, gap: 20 },
  alertBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    borderRadius: Radii.lg,
    borderWidth: 1,
    borderColor: 'rgba(255,77,77,0.3)',
    backgroundColor: 'rgba(255,77,77,0.08)',
  },
  alertTextWrap: { flex: 1, gap: 2 },
  alertTitle: { fontFamily: 'Inter_700Bold', fontSize: 13, color: Colors.loss },
  alertBody: { fontFamily: 'Inter_400Regular', fontSize: 11, color: 'rgba(255,77,77,0.7)' },
  gaugeCard: { alignItems: 'center', gap: 20 },
  gaugeTitle: { alignSelf: 'flex-start', fontFamily: 'SpaceGrotesk_700Bold', fontSize: 22, color: Colors.onSurface },
  rationale: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.onSurfaceVariant, textAlign: 'center', lineHeight: 18 },
  section: { gap: 10 },
  sectionTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface, paddingHorizontal: 4 },
  patternRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.surfaceContainer,
    borderWidth: 0.5,
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    padding: 16,
  },
  patternLeft: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  patternIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: Colors.surfaceContainerHighest,
    alignItems: 'center',
    justifyContent: 'center',
  },
  patternLabel: { fontFamily: 'Inter_700Bold', fontSize: 14, color: Colors.onSurface },
  patternDesc: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.onSurfaceVariant },
  patternBadge: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, borderWidth: 1 },
  patternBadgeText: { fontFamily: 'Inter_700Bold', fontSize: 10 },
  uploadArea: {
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    paddingVertical: 32,
    alignItems: 'center',
    gap: 6,
  },
  uploadTitle: { fontFamily: 'Inter_700Bold', fontSize: 14, color: Colors.onSurface, marginTop: 8 },
  uploadBody: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.onSurfaceVariant },
  selectFileBtn: {
    marginTop: 12,
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: Radii.md,
    backgroundColor: Colors.primary,
  },
  selectFileText: { fontFamily: 'Inter_700Bold', fontSize: 13, color: Colors.onPrimary },
  demoLink: { alignItems: 'center', paddingVertical: 4 },
  demoLinkText: { fontFamily: 'Inter_600SemiBold', fontSize: 13, color: Colors.primaryLight },
  insightsRow: { flexDirection: 'row', gap: 16, paddingBottom: 12 },
  insightCard: { flex: 1, gap: 6 },
  insightLabel: { fontFamily: 'Inter_500Medium', fontSize: 11, letterSpacing: 0.6, color: Colors.onSurfaceVariant },
  insightValueRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  insightValue: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 22, color: Colors.onSurface },
  insightDelta: { fontFamily: 'Inter_700Bold', fontSize: 11, marginBottom: 2 },
});
