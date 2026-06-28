import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { OnboardingShell } from '@/components/OnboardingShell';
import { Colors, Radii } from '@/constants/theme';
import { createExpense } from '@/services/wallet';

const CATEGORIES = [
  { key: 'rent', label: 'Rent / Housing', placeholder: '25,000' },
  { key: 'utilities', label: 'Utilities', placeholder: '3,500' },
  { key: 'subscriptions', label: 'Subscriptions', placeholder: '1,200' },
  { key: 'other', label: 'Other fixed costs', placeholder: '6,000' },
];

export default function ExpensesOnboardingScreen() {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, string>>({});

  function onContinue() {
    for (const cat of CATEGORIES) {
      const raw = values[cat.key];
      const parsed = raw ? parseFloat(raw.replace(/,/g, '')) : 0;
      if (parsed > 0) {
        createExpense({ amount: parsed, category: cat.key, label: cat.label });
      }
    }
    router.push('/(onboarding)/loans');
  }

  return (
    <OnboardingShell
      step={1}
      icon="rupee"
      iconColor={Colors.warning}
      title="Monthly expenses"
      subtitle="Your fixed obligations determine free cash flow and burn-rate risk across the dashboard."
      ctaLabel="Continue"
      onContinue={onContinue}
    >
      <View style={styles.list}>
        {CATEGORIES.map((cat) => (
          <View key={cat.key} style={styles.fieldWrap}>
            <Text style={styles.fieldLabel}>{cat.label.toUpperCase()}</Text>
            <View style={styles.inputRow}>
              <Text style={styles.rupee}>₹</Text>
              <TextInput
                style={styles.input}
                value={values[cat.key] ?? ''}
                onChangeText={(v) => setValues((prev) => ({ ...prev, [cat.key]: v }))}
                keyboardType="number-pad"
                placeholder={cat.placeholder}
                placeholderTextColor={Colors.muted}
              />
            </View>
          </View>
        ))}
      </View>
    </OnboardingShell>
  );
}

const styles = StyleSheet.create({
  list: { gap: 16 },
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
    paddingVertical: 12,
  },
  rupee: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 16,
    color: Colors.textPrimary,
  },
  input: {
    flex: 1,
    fontFamily: 'Inter_700Bold',
    fontSize: 16,
    color: Colors.textPrimary,
  },
});
