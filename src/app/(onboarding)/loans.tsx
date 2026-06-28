import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { OnboardingShell } from '@/components/OnboardingShell';
import { Icon } from '@/components/ui/Icon';
import { Colors, Radii } from '@/constants/theme';
import { createLoan } from '@/services/wallet';
import { genId } from '@/utils/id';

interface LoanDraft {
  id: string;
  label: string;
  balance: string;
  interestRate: string;
}

export default function LoansOnboardingScreen() {
  const router = useRouter();
  const [loans, setLoans] = useState<LoanDraft[]>([
    { id: genId('draft'), label: 'HDFC Credit Card', balance: '85,000', interestRate: '18' },
  ]);
  const [hasDebt, setHasDebt] = useState(true);

  function updateLoan(id: string, patch: Partial<LoanDraft>) {
    setLoans((prev) => prev.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  }

  function addLoan() {
    setLoans((prev) => [...prev, { id: genId('draft'), label: '', balance: '', interestRate: '' }]);
  }

  function onContinue() {
    if (hasDebt) {
      for (const loan of loans) {
        const balance = parseFloat(loan.balance.replace(/,/g, ''));
        const rate = parseFloat(loan.interestRate);
        if (loan.label && balance > 0 && !Number.isNaN(rate)) {
          createLoan({ balance, interestRate: rate, label: loan.label });
        }
      }
    }
    router.push('/(onboarding)/wallets');
  }

  return (
    <OnboardingShell
      step={2}
      icon="bank"
      iconColor={Colors.loss}
      title="Outstanding debt"
      subtitle="This is what the debt-vs-investment arbitrage engine compares against market yield."
      ctaLabel="Continue"
      onContinue={onContinue}
    >
      <Pressable style={styles.noDebtToggle} onPress={() => setHasDebt((v) => !v)}>
        <View style={[styles.checkbox, hasDebt && styles.checkboxOff]}>
          {!hasDebt && <Icon name="check" size={14} color={Colors.background} />}
        </View>
        <Text style={styles.noDebtLabel}>I have no active loans or credit card debt</Text>
      </Pressable>

      {hasDebt && (
        <View style={styles.list}>
          {loans.map((loan) => (
            <View key={loan.id} style={styles.loanCard}>
              <TextInput
                style={styles.labelInput}
                value={loan.label}
                onChangeText={(v) => updateLoan(loan.id, { label: v })}
                placeholder="Loan / card name"
                placeholderTextColor={Colors.muted}
              />
              <View style={styles.row}>
                <View style={styles.fieldWrap}>
                  <Text style={styles.fieldLabel}>BALANCE (₹)</Text>
                  <TextInput
                    style={styles.input}
                    value={loan.balance}
                    onChangeText={(v) => updateLoan(loan.id, { balance: v })}
                    keyboardType="number-pad"
                    placeholder="0"
                    placeholderTextColor={Colors.muted}
                  />
                </View>
                <View style={styles.fieldWrap}>
                  <Text style={styles.fieldLabel}>APR (%)</Text>
                  <TextInput
                    style={styles.input}
                    value={loan.interestRate}
                    onChangeText={(v) => updateLoan(loan.id, { interestRate: v })}
                    keyboardType="decimal-pad"
                    placeholder="0"
                    placeholderTextColor={Colors.muted}
                  />
                </View>
              </View>
            </View>
          ))}

          <Pressable style={styles.addRow} onPress={addLoan}>
            <Icon name="addCircle" size={18} color={Colors.mutedDark} />
            <Text style={styles.addRowLabel}>Add another loan</Text>
          </Pressable>
        </View>
      )}
    </OnboardingShell>
  );
}

const styles = StyleSheet.create({
  noDebtToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: Colors.border,
  },
  checkboxOff: {
    backgroundColor: Colors.secondary,
    borderColor: Colors.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  noDebtLabel: {
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
    color: Colors.onSurfaceVariant,
    flex: 1,
  },
  list: { gap: 16, marginTop: 8 },
  loanCard: {
    backgroundColor: Colors.surfaceCard,
    borderWidth: 0.5,
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    padding: 16,
    gap: 12,
  },
  labelInput: {
    fontFamily: 'Inter_700Bold',
    fontSize: 16,
    color: Colors.textPrimary,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.border,
    paddingBottom: 8,
  },
  row: { flexDirection: 'row', gap: 12 },
  fieldWrap: { flex: 1, gap: 6 },
  fieldLabel: {
    fontFamily: 'Inter_500Medium',
    fontSize: 10,
    letterSpacing: 0.6,
    color: Colors.muted,
  },
  input: {
    fontFamily: 'Inter_700Bold',
    fontSize: 16,
    color: Colors.textPrimary,
  },
  addRow: {
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    paddingVertical: 16,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  addRowLabel: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 14,
    color: Colors.mutedDark,
  },
});
