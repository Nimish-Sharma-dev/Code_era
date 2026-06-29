import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { useFinanceStore } from '@/store/useFinanceStore';

export default function SetupCompleteScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);
  const freeCashFlow = useFinanceStore((s) => s.freeCashFlow());
  const riskScore = useFinanceStore((s) => s.riskScore100());
  const totalDebt = useFinanceStore((s) => s.totalDebt());

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <View style={styles.successWrap}>
          <View style={styles.successCircle}>
            <Icon name="check" size={32} color="#FFFFFF" />
          </View>
        </View>
        <Text style={styles.title}>You're all set!</Text>
        <Text style={styles.subtitle}>
          Your financial profile has been initialized. SmartWallet AI is now personalizing
          recommendations against your real numbers.
        </Text>

        <View style={styles.summary}>
          <SummaryRow
            icon="wallet"
            iconColor={Colors.secondary}
            label="Free Cash Flow"
            sublabel="Available liquidity"
            value={`₹${Math.round(freeCashFlow).toLocaleString('en-IN')}`}
            valueColor={Colors.secondary}
            styles={styles}
          />
          <SummaryRow
            icon="warning"
            iconColor={Colors.warning}
            label="Risk Score"
            sublabel="Computed volatility tolerance"
            value={`${riskScore}/100`}
            valueColor={Colors.warning}
            styles={styles}
          />
          <SummaryRow
            icon="bank"
            iconColor={Colors.loss}
            label="Active Debt"
            sublabel="Tracked loans & cards"
            value={`₹${Math.round(totalDebt).toLocaleString('en-IN')}`}
            valueColor={Colors.loss}
            styles={styles}
          />
        </View>
      </View>

      <View style={styles.footer}>
        <Button label="Go to dashboard" icon="arrowRight" onPress={() => router.replace('/(tabs)')} />
      </View>
    </SafeAreaView>
  );
}

function SummaryRow({
  icon,
  iconColor,
  label,
  sublabel,
  value,
  valueColor,
  styles,
}: {
  icon: 'wallet' | 'warning' | 'bank';
  iconColor: string;
  label: string;
  sublabel: string;
  value: string;
  valueColor: string;
  styles: ReturnType<typeof getStyles>;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <View style={[styles.rowIcon, { backgroundColor: `${iconColor}1A` }]}>
          <Icon name={icon} size={18} color={iconColor} />
        </View>
        <View>
          <Text style={styles.rowLabel}>{label}</Text>
          <Text style={styles.rowSublabel}>{sublabel}</Text>
        </View>
      </View>
      <Text style={[styles.rowValue, { color: valueColor }]}>{value}</Text>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: Colors.background },
    content: { flex: 1, paddingHorizontal: 32, paddingTop: 64, alignItems: 'center' },
    successWrap: { marginBottom: 24 },
    successCircle: {
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: 'rgba(0,224,150,0.13)',
      borderWidth: 1,
      borderColor: 'rgba(0,224,150,0.27)',
      alignItems: 'center',
      justifyContent: 'center',
    },
    title: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 20, color: Colors.textPrimary },
    subtitle: {
      fontFamily: 'Inter_400Regular',
      fontSize: 13,
      color: Colors.muted,
      textAlign: 'center',
      marginTop: 8,
      lineHeight: 18,
    },
    summary: { width: '100%', gap: 12, marginTop: 32 },
    row: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      padding: 16,
    },
    rowLeft: { flexDirection: 'row', alignItems: 'center', gap: 16 },
    rowIcon: {
      width: 40,
      height: 40,
      borderRadius: 10,
      alignItems: 'center',
      justifyContent: 'center',
    },
    rowLabel: { fontFamily: 'Inter_500Medium', fontSize: 14, color: Colors.onSurfaceVariant },
    rowSublabel: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.muted },
    rowValue: { fontFamily: 'Inter_600SemiBold', fontSize: 16 },
    footer: { paddingHorizontal: 32, paddingBottom: 32 },
  });
