import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Dimensions, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { NewsCard } from '@/components/NewsCard';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Icon } from '@/components/ui/Icon';
import { Colors } from '@/constants/theme';
import { KlineInterval, useBinanceLiveTicks, useRealTimeCandles } from '@/services/binance';
import { getAssets, getNews } from '@/services/market';
import { generateMockCandles } from '@/utils/mockCandles';
import { NewsNode } from '@/types';

const CRYPTO_TICKERS = ['BTC', 'ETH'];
const INTERVALS: { key: KlineInterval; label: string }[] = [
  { key: '1m', label: '1m' },
  { key: '5m', label: '5m' },
  { key: '15m', label: '15m' },
  { key: '1h', label: '1h' },
];

export default function AssetDetailScreen() {
  const router = useRouter();
  const { ticker: rawTicker } = useLocalSearchParams<{ ticker: string }>();
  const ticker = (rawTicker ?? '').toUpperCase();
  const isLive = CRYPTO_TICKERS.includes(ticker);

  const [interval, setInterval] = useState<KlineInterval>('1m');
  const { ticks } = useBinanceLiveTicks();
  const { candles: liveCandles, connected } = useRealTimeCandles(
    isLive ? (ticker as 'BTC' | 'ETH') : 'BTC',
    interval,
  );

  const [news, setNews] = useState<NewsNode[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setNewsLoading(true);
    getNews(ticker)
      .then((items) => active && setNews(items))
      .finally(() => active && setNewsLoading(false));
    return () => {
      active = false;
    };
  }, [ticker]);

  const asset = useMemo(() => getAssets().find((a) => a.ticker === ticker), [ticker]);
  const livePrice = ticks[ticker]?.priceInr;
  const currentPrice = isLive && livePrice ? livePrice : asset?.currentPrice ?? 0;
  const changePct = isLive && ticks[ticker] ? ticks[ticker].changePct24h : asset?.changePct24h ?? 0;

  const chartWidth = Dimensions.get('window').width - 32;
  const mockCandles = useMemo(
    () => (isLive ? [] : generateMockCandles(ticker, currentPrice || 100)),
    [isLive, ticker, currentPrice],
  );
  const candles = isLive ? liveCandles : mockCandles;

  const positive = changePct >= 0;

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable style={styles.backBtn} onPress={() => router.back()}>
          <Icon name="arrowRight" size={18} color={Colors.primary} style={styles.backIcon} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTicker}>{ticker}</Text>
          <Text style={styles.headerName}>{asset?.name ?? ''}</Text>
        </View>
        {isLive && (
          <View style={styles.liveDotWrap}>
            <View style={[styles.liveDot, { backgroundColor: connected ? Colors.secondary : Colors.muted }]} />
            <Text style={styles.liveDotLabel}>{connected ? 'LIVE' : 'OFFLINE'}</Text>
          </View>
        )}
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.priceRow}>
          <Text style={styles.price}>
            ₹{currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </Text>
          <Badge label={`${positive ? '+' : ''}${changePct.toFixed(2)}%`} tone={positive ? 'gain' : 'loss'} uppercase={false} />
        </View>

        {isLive && (
          <View style={styles.intervalRow}>
            {INTERVALS.map((iv) => (
              <Chip key={iv.key} label={iv.label} active={interval === iv.key} onPress={() => setInterval(iv.key)} />
            ))}
          </View>
        )}

        <Card style={styles.chartCard} noPadding>
          <View style={{ padding: 12 }}>
            <CandlestickChart candles={candles} width={chartWidth - 24} />
          </View>
        </Card>

        {!isLive && (
          <Text style={styles.illustrativeNote}>
            Illustrative chart — live intraday data for stocks needs a market data
            subscription (Alpha Vantage / Polygon). BTC and ETH stream live from Binance.
          </Text>
        )}

        {asset && (
          <Card style={styles.sentimentCard}>
            <View style={styles.sentimentRow}>
              <View>
                <Text style={styles.sentimentLabel}>FinBERT sentiment</Text>
                <Text style={styles.sentimentScore}>
                  {asset.finbertScore >= 0 ? '+' : ''}
                  {asset.finbertScore.toFixed(2)}
                </Text>
              </View>
              {asset.momentumTrigger && <Badge label="Momentum" tone="primary" />}
            </View>
            <Text style={styles.sentimentSub}>
              Aggregated across {asset.momentumSourceCount} recent headlines.
            </Text>
          </Card>
        )}

        <View style={styles.newsSection}>
          <Text style={styles.sectionTitle}>Related news</Text>
          {newsLoading ? (
            <ActivityIndicator color={Colors.primary} />
          ) : news.length === 0 ? (
            <Text style={styles.emptyText}>No recent headlines for {ticker}.</Text>
          ) : (
            news
              .filter((n) => n.tickers.includes(ticker))
              .slice(0, 5)
              .map((item) => (
                <NewsCard
                  key={item.id}
                  news={item}
                  onAskAboutThis={(n) =>
                    router.push({
                      pathname: '/(tabs)/chat',
                      params: { prefill: `What does this mean for ${ticker}: "${n.headline}"` },
                    })
                  }
                />
              ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  header: {
    height: 64,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.border,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backIcon: { transform: [{ rotate: '180deg' }] },
  headerTitleWrap: { flex: 1 },
  headerTicker: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 18, color: Colors.onSurface },
  headerName: { fontFamily: 'Inter_500Medium', fontSize: 12, color: Colors.onSurfaceVariant },
  liveDotWrap: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  liveDot: { width: 6, height: 6, borderRadius: 3 },
  liveDotLabel: { fontFamily: 'Inter_700Bold', fontSize: 10, color: Colors.onSurfaceVariant, letterSpacing: 0.5 },
  scroll: { padding: 16, gap: 16, paddingBottom: 32 },
  priceRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  price: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 28, color: Colors.onSurface },
  intervalRow: { flexDirection: 'row', gap: 8 },
  chartCard: {},
  illustrativeNote: { fontFamily: 'Inter_400Regular', fontSize: 11, color: Colors.muted, lineHeight: 16 },
  sentimentCard: { gap: 8 },
  sentimentRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sentimentLabel: { fontFamily: 'Inter_500Medium', fontSize: 12, color: Colors.onSurfaceVariant },
  sentimentScore: { fontFamily: 'Inter_700Bold', fontSize: 20, color: Colors.onSurface },
  sentimentSub: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.muted },
  newsSection: { gap: 12 },
  sectionTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
  emptyText: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.muted, textAlign: 'center', paddingVertical: 16 },
});
