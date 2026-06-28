import { Children, ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

interface Grid2Props {
  children: ReactNode;
  gap?: number;
}

export function Grid2({ children, gap = 12 }: Grid2Props) {
  const items = Children.toArray(children);
  const rows: ReactNode[][] = [];
  for (let i = 0; i < items.length; i += 2) {
    rows.push(items.slice(i, i + 2));
  }

  return (
    <View style={{ gap }}>
      {rows.map((row, i) => (
        <View key={i} style={[styles.row, { gap }]}>
          {row.map((item, j) => (
            <View key={j} style={styles.cell}>
              {item}
            </View>
          ))}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  cell: { flex: 1 },
});
