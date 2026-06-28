import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { NewsCard } from '@/components/NewsCard';
import { SentimentBar } from '@/components/SentimentBar';
import { TopBar } from '@/components/TopBar';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Icon } from '@/components/ui/Icon';
import { Colors } from '@/constants/theme';
import { getAssets, getNews } from '@/services/market';
import { NewsNode } from '@/types';

const TABS = ['General', 'Sectors', 'Crypto', 'Forex'] as const;

export default function MarketsScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('General');
  const [news, setNews] = useState<NewsNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  const assets = getAssets();
  const momentumAssets = [...assets].sort((a, b) => Math.abs(b.finbertScore) - Math.abs(a.finbertScore)).slice(0, 5);

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setRefreshing(true) : setLoading(true);
    setError(false);
    try {
      const ticker = activeTab === 'Crypto' ? 'BTC' : undefined;
      const items = await getNews(ticker);
      setNews(items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [activeTab]);

  useEffect(() => {
    load();
  }, [load]);

  function onAskAboutThis(item: NewsNode) {
    router.push({
      pathname: '/(tabs)/chat',
      params: { prefill: `What does this mean for my portfolio: "${item.headline}"` },
    });
  }

  return (
    <View style={styles.screen}>
      <TopBar />
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={Colors.primary} />}
      >
        <View style={styles.headerRow}>
          <View style={styles.headerLeft}>
            <Text style={styles.headerTitle}>MARKETS</Text>
            <View style={styles.livePill}>
              <View style={styles.liveDot} />
              <Text style={styles.livePillText}>Live data</Text>
            </View>
          </View>
          <Icon name="search" size={20} color={Colors.outline} />
        </View>

        <Card variant="low" style={styles.momentumCard}>
          <View style={styles.momentumHeader}>
            <View style={styles.momentumTitleRow}>
              <Icon name="trendingUp" size={18} color={Colors.primary} />
              <Text style={styles.momentumTitle}>FinBERT Momentum</Text>
            </View>
            <Text style={styles.momentumSub}>24h Sentiment</Text>
          </View>
          <View style={styles.momentumList}>
            {momentumAssets.map((a) => (
              <SentimentBar key={a.ticker} ticker={a.ticker} score={a.finbertScore} />
            ))}
          </View>
        </Card>

        <View style={styles.tabRow}>
          {TABS.map((t) => (
            <Chip key={t} label={t} active={activeTab === t} onPress={() => setActiveTab(t)} />
          ))}
        </View>

        {loading && (
          <View style={styles.center}>
            <ActivityIndicator color={Colors.primary} />
          </View>
        )}

        {error && (
          <View style={styles.center}>
            <Text style={styles.errorText}>Couldn't load the news feed.</Text>
            <Button label="Tap to retry" variant="ghost" onPress={() => load()} />
          </View>
        )}

        {!loading && !error && (
          <View style={styles.newsList}>
            {news.map((item) => (
              <NewsCard key={item.id} news={item} onAskAboutThis={onAskAboutThis} />
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  scroll: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 32, gap: 20 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { fontFamily: 'Inter_700Bold', fontSize: 16, color: Colors.onSurface, letterSpacing: 0.6 },
  livePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: 'rgba(0,194,168,0.1)',
    borderWidth: 0.5,
    borderColor: 'rgba(0,194,168,0.25)',
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.secondary },
  livePillText: { fontFamily: 'Inter_700Bold', fontSize: 10, color: Colors.secondary, letterSpacing: 0.4 },
  momentumCard: { gap: 16 },
  momentumHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  momentumTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  momentumTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
  momentumSub: { fontFamily: 'Inter_600SemiBold', fontSize: 11, color: Colors.outline },
  momentumList: { gap: 14 },
  tabRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  center: { alignItems: 'center', gap: 12, paddingVertical: 24 },
  errorText: { fontFamily: 'Inter_500Medium', fontSize: 14, color: Colors.onSurfaceVariant },
  newsList: { gap: 16 },
});
