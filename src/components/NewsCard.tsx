import { Linking, StyleSheet, Text, View } from 'react-native';

import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { NewsNode } from '@/types';
import { Button } from './ui/Button';

interface NewsCardProps {
  news: NewsNode;
  onAskAboutThis: (news: NewsNode) => void;
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function NewsCard({ news, onAskAboutThis }: NewsCardProps) {
  const Colors = useColors();
  const styles = getStyles(Colors);
  const positive = news.finbertScore > 0.15;
  const negative = news.finbertScore < -0.15;
  const badgeColor = positive ? Colors.secondary : negative ? Colors.loss : Colors.warning;

  return (
    <View style={styles.card}>
      <View style={styles.body}>
        <View style={styles.metaRow}>
          <View style={styles.sourceRow}>
            <Text style={styles.source}>{news.source}</Text>
            <Text style={styles.time}>{timeAgo(news.publishedAt)}</Text>
          </View>
          <View style={[styles.scoreBadge, { backgroundColor: `${badgeColor}1A`, borderColor: `${badgeColor}33` }]}>
            <Text style={[styles.scoreText, { color: badgeColor }]}>
              FINBERT: {news.finbertScore >= 0 ? '+' : ''}
              {news.finbertScore.toFixed(2)}
            </Text>
          </View>
        </View>
        <Text style={styles.headline}>{news.headline}</Text>
        {news.tickers.length > 0 && (
          <View style={styles.tagRow}>
            {news.tickers.slice(0, 3).map((t) => (
              <View key={t} style={styles.tag}>
                <Text style={styles.tagText}>#{t}</Text>
              </View>
            ))}
          </View>
        )}
        <View style={styles.actionRow}>
          <View style={styles.actionFlex}>
            <Button label="Ask about this" icon="ask" variant="ghost" onPress={() => onAskAboutThis(news)} />
          </View>
          {news.url && (
            <View style={styles.actionFlex}>
              <Button label="Read article" variant="ghost" onPress={() => Linking.openURL(news.url!)} />
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    card: {
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      overflow: 'hidden',
    },
    body: {
      padding: 16,
      gap: 12,
    },
    metaRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    sourceRow: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
    },
    source: {
      fontFamily: 'Inter_700Bold',
      fontSize: 10,
      color: Colors.onSurfaceVariant,
      backgroundColor: Colors.surfaceContainerHighest,
      paddingHorizontal: 8,
      paddingVertical: 2,
      borderRadius: 4,
      textTransform: 'uppercase',
    },
    time: {
      fontFamily: 'Inter_500Medium',
      fontSize: 10,
      color: Colors.outline,
    },
    scoreBadge: {
      paddingHorizontal: 8,
      paddingVertical: 3,
      borderRadius: 4,
      borderWidth: 1,
    },
    scoreText: {
      fontFamily: 'Inter_700Bold',
      fontSize: 10,
    },
    headline: {
      fontFamily: 'Inter_600SemiBold',
      fontSize: 16,
      lineHeight: 22,
      color: Colors.onSurface,
    },
    tagRow: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 8,
    },
    tag: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 4,
      backgroundColor: Colors.surfaceContainerHigh,
      borderWidth: 0.5,
      borderColor: Colors.outlineVariantAlt,
    },
    tagText: {
      fontFamily: 'Inter_600SemiBold',
      fontSize: 11,
      color: Colors.primary,
    },
    actionRow: {
      flexDirection: 'row',
      gap: 8,
      paddingTop: 8,
      borderTopWidth: 0.5,
      borderTopColor: Colors.border,
    },
    actionFlex: {
      flex: 1,
    },
  });
