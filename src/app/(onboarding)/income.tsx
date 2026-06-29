import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { OnboardingShell } from '@/components/OnboardingShell';
import { Chip } from '@/components/ui/Chip';
import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { createIncome } from '@/services/wallet';
import { IncomeSource } from '@/types';

const TYPES: { key: IncomeSource['type']; label: string }[] = [
  { key: 'salaried', label: 'Salaried' },
  { key: 'freelance', label: 'Freelance' },
  { key: 'business', label: 'Business' },
  { key: 'multiple', label: 'Multiple' },
];

export default function IncomeOnboardingScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);
  const [amount, setAmount] = useState('85000');
  const [type, setType] = useState<IncomeSource['type']>('salaried');

  function onContinue() {
    const parsed = parseFloat(amount.replace(/,/g, ''));
    if (!Number.isNaN(parsed) && parsed > 0) {
      createIncome({
        amount: parsed,
        frequency: 'monthly',
        sourceName: TYPES.find((t) => t.key === type)?.label ?? 'Income',
        type,
      });
    }
    router.push('/(onboarding)/expenses');
  }

  return (
    <OnboardingShell
      step={0}
      icon="rupee"
      title="Your income"
      subtitle="Tell us about your monthly income to personalize your financial risk assessment and trading limits."
      ctaLabel="Continue"
      onContinue={onContinue}
    >
      <View style={styles.fieldWrap}>
        <Text style={styles.fieldLabel}>MONTHLY TAKE-HOME INCOME</Text>
        <View style={styles.inputRow}>
          <Text style={styles.rupee}>₹</Text>
          <TextInput
            style={styles.input}
            value={amount}
            onChangeText={setAmount}
            keyboardType="number-pad"
            placeholder="0"
            placeholderTextColor={Colors.muted}
          />
        </View>
      </View>

      <View style={styles.chipSection}>
        <Text style={styles.chipLabel}>Income source type</Text>
        <View style={styles.chipRow}>
          {TYPES.map((t) => (
            <Chip key={t.key} label={t.label} active={type === t.key} onPress={() => setType(t.key)} />
          ))}
        </View>
      </View>
    </OnboardingShell>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    fieldWrap: { gap: 8 },
    fieldLabel: {
      fontFamily: 'Inter_500Medium',
      fontSize: 10,
      letterSpacing: 1,
      color: Colors.primaryLight,
    },
    inputRow: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
      backgroundColor: Colors.surfaceCard,
      borderWidth: 1,
      borderColor: Colors.border,
      borderRadius: Radii.md,
      paddingHorizontal: 16,
      paddingVertical: 14,
    },
    rupee: {
      fontFamily: 'Inter_600SemiBold',
      fontSize: 20,
      color: Colors.textPrimary,
    },
    input: {
      flex: 1,
      fontFamily: 'Inter_700Bold',
      fontSize: 20,
      color: Colors.textPrimary,
    },
    chipSection: { gap: 12 },
    chipLabel: {
      fontFamily: 'Inter_500Medium',
      fontSize: 14,
      color: Colors.onSurfaceVariant,
    },
    chipRow: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 12,
    },
  });
