import { StyleSheet, Text, View } from 'react-native';

import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { ActionableOpportunity } from '@/types';
import { Button } from './ui/Button';
import { Icon } from './ui/Icon';

interface OpportunityCardProps {
  opportunity: ActionableOpportunity;
  onPress?: () => void;
}

const getCategoryMeta = (Colors: ColorPalette) => ({
  MARKET_TRADE: { icon: 'trendingUp' as const, color: Colors.primary, label: 'MARKET TRADE' },
  DEBT_STRATEGY: { icon: 'bank' as const, color: Colors.warning, label: 'DEBT STRATEGY' },
  CASH_OPTIMIZATION: { icon: 'wallet' as const, color: Colors.secondary, label: 'CASH OPTIMIZATION' },
});

const getPriorityBg = (Colors: ColorPalette) => ({
  HIGH: Colors.primary,
  MEDIUM: Colors.warning,
  LOW: Colors.surfaceContainerHigh,
});

export function OpportunityCard({ opportunity, onPress }: OpportunityCardProps) {
  const Colors = useColors();
  const styles = getStyles(Colors);
  const meta = getCategoryMeta(Colors)[opportunity.category];
  const isHighPriorityTrade = opportunity.category === 'MARKET_TRADE' && opportunity.priority === 'HIGH';

  if (isHighPriorityTrade) {
    return (
      <View style={styles.gradientBorder}>
        <View style={styles.gradientInner}>
          <Header meta={meta} priority={opportunity.priority} Colors={Colors} styles={styles} />
          <Text style={styles.title}>{opportunity.title}</Text>
          {opportunity.parameters && (
            <View style={styles.paramRow}>
              <Param label="ENTRY" value={`₹${opportunity.parameters.entry?.toLocaleString('en-IN')}`} styles={styles} />
              <Param
                label="TARGET"
                value={`₹${opportunity.parameters.target?.toLocaleString('en-IN')}`}
                color={Colors.secondary}
                styles={styles}
              />
            </View>
          )}
          <Button label={opportunity.ctaLabel} onPress={onPress} />
        </View>
      </View>
    );
  }

  const borderAccent = opportunity.priority === 'MEDIUM' ? meta.color : undefined;

  return (
    <View
      style={[
        styles.card,
        borderAccent && { borderLeftWidth: 4, borderLeftColor: borderAccent },
      ]}
    >
      <Header meta={meta} priority={opportunity.priority} Colors={Colors} styles={styles} />
      <Text style={styles.cardTitleSm}>{opportunity.title}</Text>
      {opportunity.rationale && <Text style={styles.rationale}>{opportunity.rationale}</Text>}
      {opportunity.annualizedImpact != null && (
        <Text style={[styles.rationale, { color: Colors.secondary }]}>
          Projected annual gain: ₹{opportunity.annualizedImpact.toLocaleString('en-IN')}
        </Text>
      )}
      <Button label={opportunity.ctaLabel} variant="ghost" onPress={onPress} />
    </View>
  );
}

function Header({
  meta,
  priority,
  Colors,
  styles,
}: {
  meta: { icon: 'trendingUp' | 'bank' | 'wallet'; color: string; label: string };
  priority: ActionableOpportunity['priority'];
  Colors: ColorPalette;
  styles: ReturnType<typeof getStyles>;
}) {
  const priorityBg = getPriorityBg(Colors)[priority];
  return (
    <View style={styles.headerRow}>
      <View style={styles.headerLeft}>
        <Icon name={meta.icon} size={16} color={meta.color} />
        <Text style={[styles.headerLabel, { color: meta.color }]}>{meta.label}</Text>
      </View>
      <View style={[styles.priorityPill, { backgroundColor: priorityBg }]}>
        <Text
          style={[
            styles.priorityText,
            { color: priority === 'LOW' ? Colors.onSurfaceVariant : '#0A0B0F' },
          ]}
        >
          {priority} PRIORITY
        </Text>
      </View>
    </View>
  );
}

function Param({
  label,
  value,
  color,
  styles,
}: {
  label: string;
  value: string;
  color?: string;
  styles: ReturnType<typeof getStyles>;
}) {
  return (
    <View style={styles.param}>
      <Text style={styles.paramLabel}>{label}</Text>
      <Text style={[styles.paramValue, color && { color }]}>{value}</Text>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    gradientBorder: {
      borderRadius: Radii.lg,
      padding: 1,
      backgroundColor: Colors.primary,
    },
    gradientInner: {
      backgroundColor: Colors.surface,
      borderRadius: Radii.lg,
      padding: 16,
      gap: 16,
    },
    card: {
      backgroundColor: Colors.surfaceContainer,
      borderRadius: Radii.lg,
      borderWidth: 0.5,
      borderColor: Colors.border,
      padding: 16,
      gap: 12,
    },
    headerRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    headerLeft: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 6,
    },
    headerLabel: {
      fontFamily: 'Inter_700Bold',
      fontSize: 10,
      letterSpacing: 1,
    },
    priorityPill: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 6,
    },
    priorityText: {
      fontFamily: 'Inter_700Bold',
      fontSize: 10,
    },
    title: {
      fontFamily: 'SpaceGrotesk_700Bold',
      fontSize: 18,
      color: Colors.onSurface,
    },
    cardTitleSm: {
      fontFamily: 'Inter_700Bold',
      fontSize: 14,
      color: Colors.onSurface,
    },
    rationale: {
      fontFamily: 'Inter_500Medium',
      fontSize: 12,
      color: Colors.onSurfaceVariant,
      lineHeight: 16,
    },
    paramRow: {
      flexDirection: 'row',
      gap: 8,
    },
    param: {
      flex: 1,
      backgroundColor: Colors.surfaceContainer,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: 10,
      padding: 8,
    },
    paramLabel: {
      fontFamily: 'Inter_500Medium',
      fontSize: 10,
      color: Colors.onSurfaceVariant,
    },
    paramValue: {
      fontFamily: 'Inter_700Bold',
      fontSize: 14,
      color: Colors.onSurface,
    },
  });
