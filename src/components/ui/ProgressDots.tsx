import { StyleSheet, View } from 'react-native';

import { Colors } from '@/constants/theme';

interface ProgressDotsProps {
  total: number;
  current: number; // 0-indexed
}

export function ProgressDots({ total, current }: ProgressDotsProps) {
  return (
    <View style={styles.row}>
      {Array.from({ length: total }).map((_, i) => (
        <View
          key={i}
          style={[
            styles.dot,
            { backgroundColor: i <= current ? Colors.primaryLight : Colors.surfaceContainer },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 6,
    width: '100%',
  },
  dot: {
    flex: 1,
    height: 4,
    borderRadius: 999,
  },
});
