import { StyleSheet, Text, View } from 'react-native';

import { Colors } from '@/constants/theme';

interface SentimentBarProps {
  ticker: string;
  score: number; // -1..1
}

export function SentimentBar({ ticker, score }: SentimentBarProps) {
  const positive = score >= 0;
  const color = score > 0.15 ? Colors.secondary : score < -0.15 ? Colors.loss : Colors.warning;
  const widthPct = Math.min(Math.abs(score), 1) * 100;

  return (
    <View style={styles.row}>
      <View style={styles.labelRow}>
        <Text style={styles.ticker}>{ticker}</Text>
        <Text style={[styles.score, { color }]}>
          {positive ? '+' : ''}
          {score.toFixed(2)}
        </Text>
      </View>
      <View style={styles.track}>
        <View
          style={[
            styles.fill,
            {
              width: `${widthPct}%`,
              backgroundColor: color,
              alignSelf: positive ? 'flex-start' : 'flex-end',
            },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    gap: 4,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  ticker: {
    fontFamily: 'Inter_500Medium',
    fontSize: 14,
    color: Colors.onSurface,
  },
  score: {
    fontFamily: 'Inter_700Bold',
    fontSize: 14,
  },
  track: {
    height: 6,
    width: '100%',
    backgroundColor: Colors.surfaceContainerHighest,
    borderRadius: 999,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 999,
  },
});
