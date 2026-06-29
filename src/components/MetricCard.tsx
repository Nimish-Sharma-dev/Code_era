import { StyleSheet, Text, View } from 'react-native';

import { ColorPalette } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { Badge, BadgeTone } from './ui/Badge';
import { Card } from './ui/Card';

interface MetricCardProps {
  label: string;
  value: string;
  sublabel?: string;
  badge?: { label: string; tone: BadgeTone };
  variant?: 'default' | 'low';
}

export function MetricCard({ label, value, sublabel, badge, variant = 'default' }: MetricCardProps) {
  const Colors = useColors();
  const styles = getStyles(Colors);

  return (
    <Card variant={variant} style={styles.card}>
      <View style={styles.headRow}>
        <Text style={styles.label}>{label}</Text>
        {badge && <Badge label={badge.label} tone={badge.tone} />}
      </View>
      <Text style={styles.value}>{value}</Text>
      {sublabel && <Text style={styles.sublabel}>{sublabel}</Text>}
    </Card>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    card: {
      flex: 1,
      gap: 6,
    },
    headRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
    },
    label: {
      fontFamily: 'Inter_500Medium',
      fontSize: 14,
      color: Colors.onSurfaceVariant,
    },
    value: {
      fontFamily: 'Inter_600SemiBold',
      fontSize: 16,
      color: Colors.onSurface,
    },
    sublabel: {
      fontFamily: 'Inter_600SemiBold',
      fontSize: 12,
      color: Colors.secondary,
    },
  });
