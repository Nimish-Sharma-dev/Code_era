import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { DonutChart } from '@/components/charts/DonutChart';
import { TopBar } from '@/components/TopBar';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Icon, IconName } from '@/components/ui/Icon';
import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { createWallet } from '@/services/wallet';
import { useFinanceStore } from '@/store/useFinanceStore';
import { Wallet } from '@/types';

const ASSET_CLASSES: { key: Wallet['assetType']; label: string }[] = [
  { key: 'crypto', label: 'Crypto' },
  { key: 'stock', label: 'Stocks' },
  { key: 'mutual_fund', label: 'Mutual funds' },
  { key: 'fd', label: 'FD' },
  { key: 'cash', label: 'Cash' },
];

const getAssetTypeMeta = (Colors: ColorPalette): Record<Wallet['assetType'], { color: string; icon: IconName; label: string }> => ({
  crypto: { color: Colors.warning, icon: 'bitcoin', label: 'Crypto' },
  stock: { color: Colors.primary, icon: 'wallet', label: 'Stocks' },
  mutual_fund: { color: Colors.secondary, icon: 'pieChart', label: 'Mutual funds' },
  fd: { color: Colors.outline, icon: 'bank', label: 'Fixed deposits' },
  cash: { color: Colors.muted, icon: 'rupee', label: 'Cash' },
});

export default function PortfolioScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);
  const assetTypeMeta = getAssetTypeMeta(Colors);
  const wallets = useFinanceStore((s) => s.wallets);
  const loans = useFinanceStore((s) => s.loans);
  const removeWallet = useFinanceStore((s) => s.removeWallet);
  const removeLoan = useFinanceStore((s) => s.removeLoan);
  const totalValue = useFinanceStore((s) => s.totalWalletValue());
  const totalDebt = useFinanceStore((s) => s.totalDebt());

  const [showAddForm, setShowAddForm] = useState(false);
  const [assetClass, setAssetClass] = useState<Wallet['assetType']>('crypto');
  const [label, setLabel] = useState('');
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [value, setValue] = useState('');

  const byType = wallets.reduce<Record<string, number>>((acc, w) => {
    acc[w.assetType] = (acc[w.assetType] ?? 0) + w.balance;
    return acc;
  }, {});

  const slices = Object.entries(byType).map(([type, value]) => ({
    value,
    color: assetTypeMeta[type as Wallet['assetType']].color,
  }));

  function resetForm() {
    setLabel('');
    setSymbol('');
    setQuantity('');
    setValue('');
  }

  function onAddWallet() {
    const val = parseFloat(value.replace(/,/g, ''));
    if (!symbol.trim() || Number.isNaN(val) || val <= 0) {
      Alert.alert('Missing details', 'Enter at least a symbol and a value greater than 0.');
      return;
    }
    const qty = parseFloat(quantity);
    createWallet({
      assetType: assetClass,
      label: label.trim() || symbol.trim().toUpperCase(),
      symbol: symbol.trim().toUpperCase(),
      quantity: Number.isNaN(qty) ? 0 : qty,
      balance: val,
      changePct: 0,
    });
    resetForm();
    setShowAddForm(false);
  }

  function onRemoveWallet(w: Wallet) {
    Alert.alert('Remove wallet', `Remove ${w.label} from your portfolio?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => removeWallet(w.id) },
    ]);
  }

  function onRemoveLoan(label: string, id: string) {
    Alert.alert('Remove loan', `Remove ${label} from tracked debt?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => removeLoan(id) },
    ]);
  }

  return (
    <View style={styles.screen}>
      <TopBar title="Portfolio" />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {wallets.length === 0 ? (
          <Card style={styles.emptyCard}>
            <Icon name="wallet" size={28} color={Colors.outline} />
            <Text style={styles.emptyTitle}>No wallets tracked yet</Text>
            <Text style={styles.emptyBody}>
              Wallets you add during onboarding (or below) will appear here with allocation and value.
            </Text>
          </Card>
        ) : (
          <Card style={styles.allocationCard}>
            <Text style={styles.cardTitle}>Asset Allocation</Text>
            <View style={styles.donutRow}>
              <DonutChart slices={slices} />
              <View style={styles.legend}>
                {Object.entries(byType).map(([type, value]) => {
                  const meta = assetTypeMeta[type as Wallet['assetType']];
                  const pct = totalValue > 0 ? Math.round((value / totalValue) * 100) : 0;
                  return (
                    <View key={type} style={styles.legendRow}>
                      <View style={[styles.legendDot, { backgroundColor: meta.color }]} />
                      <Text style={styles.legendLabel}>{meta.label}</Text>
                      <Text style={styles.legendValue}>{pct}%</Text>
                    </View>
                  );
                })}
              </View>
            </View>
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total Value</Text>
              <Text style={styles.totalValue}>₹{Math.round(totalValue).toLocaleString('en-IN')}</Text>
            </View>
          </Card>
        )}

        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>Wallets</Text>
            <Pressable style={styles.addBtn} onPress={() => setShowAddForm((v) => !v)}>
              <Icon name={showAddForm ? 'close' : 'plus'} size={16} color={Colors.primary} />
              <Text style={styles.addBtnLabel}>{showAddForm ? 'Cancel' : 'Add wallet'}</Text>
            </Pressable>
          </View>

          {showAddForm && (
            <View style={styles.addForm}>
              <View style={styles.chipRow}>
                {ASSET_CLASSES.map((c) => (
                  <Chip key={c.key} label={c.label} active={assetClass === c.key} onPress={() => setAssetClass(c.key)} />
                ))}
              </View>
              <TextInput
                style={styles.input}
                value={label}
                onChangeText={setLabel}
                placeholder="Asset name (e.g. Bitcoin)"
                placeholderTextColor={Colors.muted}
              />
              <View style={styles.row}>
                <TextInput
                  style={[styles.input, styles.flex1]}
                  value={symbol}
                  onChangeText={setSymbol}
                  placeholder="Symbol (e.g. BTC)"
                  placeholderTextColor={Colors.muted}
                  autoCapitalize="characters"
                />
                <TextInput
                  style={[styles.input, styles.flex1]}
                  value={quantity}
                  onChangeText={setQuantity}
                  placeholder="Quantity"
                  placeholderTextColor={Colors.muted}
                  keyboardType="decimal-pad"
                />
              </View>
              <TextInput
                style={styles.input}
                value={value}
                onChangeText={setValue}
                placeholder="Value (₹)"
                placeholderTextColor={Colors.muted}
                keyboardType="number-pad"
              />
              <Button label="Add to wallet" onPress={onAddWallet} />
            </View>
          )}

          {wallets.map((w) => {
            const meta = assetTypeMeta[w.assetType];
            return (
              <View key={w.id} style={styles.walletRow}>
                <Pressable style={styles.walletMain} onPress={() => router.push(`/asset/${w.symbol}`)}>
                  <View style={styles.walletLeft}>
                    <View style={[styles.walletIcon, { backgroundColor: `${meta.color}22` }]}>
                      <Icon name={meta.icon} size={18} color={meta.color} />
                    </View>
                    <View>
                      <Text style={styles.walletName}>{w.label}</Text>
                      <Text style={styles.walletQty}>
                        {w.quantity ? `${w.quantity} ${w.symbol}` : meta.label}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.walletRight}>
                    <Text style={styles.walletValue}>₹{Math.round(w.balance).toLocaleString('en-IN')}</Text>
                    <Text style={[styles.walletChange, { color: w.changePct >= 0 ? Colors.secondary : Colors.loss }]}>
                      {w.changePct >= 0 ? '+' : ''}
                      {w.changePct}%
                    </Text>
                  </View>
                </Pressable>
                <Pressable style={styles.deleteBtn} onPress={() => onRemoveWallet(w)}>
                  <Icon name="close" size={16} color={Colors.muted} />
                </Pressable>
              </View>
            );
          })}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Debt Breakdown</Text>
          {loans.length === 0 ? (
            <Card style={styles.emptyCard}>
              <Icon name="bank" size={24} color={Colors.outline} />
              <Text style={styles.emptyTitle}>No active loans</Text>
              <Text style={styles.emptyBody}>You're debt-free — every recommendation defaults to growth.</Text>
            </Card>
          ) : (
            loans.map((loan) => {
              const widthPct = totalDebt > 0 ? (loan.balance / totalDebt) * 100 : 0;
              return (
                <View key={loan.id} style={styles.loanCard}>
                  <View style={styles.loanHeader}>
                    <Text style={styles.loanLabel}>{loan.label}</Text>
                    <View style={styles.loanHeaderRight}>
                      <Text style={styles.loanApr}>{loan.interestRate}% APR</Text>
                      <Pressable onPress={() => onRemoveLoan(loan.label, loan.id)}>
                        <Icon name="close" size={14} color={Colors.muted} />
                      </Pressable>
                    </View>
                  </View>
                  <View style={styles.loanTrack}>
                    <View style={[styles.loanFill, { width: `${widthPct}%` }]} />
                  </View>
                  <Text style={styles.loanBalance}>₹{Math.round(loan.balance).toLocaleString('en-IN')} outstanding</Text>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: Colors.background },
    scroll: { paddingHorizontal: 16, paddingTop: 20, paddingBottom: 32, gap: 24 },
    cardTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface, marginBottom: 16 },
    allocationCard: {},
    donutRow: { flexDirection: 'row', alignItems: 'center', gap: 20 },
    legend: { flex: 1, gap: 10 },
    legendRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    legendDot: { width: 10, height: 10, borderRadius: 5 },
    legendLabel: { flex: 1, fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.onSurfaceVariant },
    legendValue: { fontFamily: 'Inter_700Bold', fontSize: 13, color: Colors.onSurface },
    totalRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginTop: 20,
      paddingTop: 16,
      borderTopWidth: 0.5,
      borderTopColor: Colors.border,
    },
    totalLabel: { fontFamily: 'Inter_500Medium', fontSize: 14, color: Colors.onSurfaceVariant },
    totalValue: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 18, color: Colors.primary },
    section: { gap: 12 },
    sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 4 },
    sectionTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 18, color: Colors.onSurface },
    addBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 4,
      paddingHorizontal: 10,
      paddingVertical: 6,
      borderRadius: Radii.pill,
      backgroundColor: `${Colors.primary}1A`,
    },
    addBtnLabel: { fontFamily: 'Inter_600SemiBold', fontSize: 12, color: Colors.primary },
    addForm: {
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      padding: 16,
      gap: 12,
    },
    chipRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
    row: { flexDirection: 'row', gap: 12 },
    flex1: { flex: 1 },
    input: {
      backgroundColor: Colors.surfaceContainer,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.md,
      paddingHorizontal: 14,
      paddingVertical: 12,
      color: Colors.textPrimary,
      fontFamily: 'Inter_600SemiBold',
      fontSize: 14,
    },
    walletRow: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
    },
    walletMain: {
      flex: 1,
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: 16,
    },
    deleteBtn: { paddingHorizontal: 16, paddingVertical: 16 },
    walletLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    walletIcon: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
    walletName: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
    walletQty: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.onSurfaceVariant },
    walletRight: { alignItems: 'flex-end' },
    walletValue: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
    walletChange: { fontFamily: 'Inter_700Bold', fontSize: 12, marginTop: 2 },
    loanCard: {
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      padding: 16,
      gap: 10,
    },
    loanHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    loanHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    loanLabel: { fontFamily: 'Inter_600SemiBold', fontSize: 14, color: Colors.onSurface },
    loanApr: { fontFamily: 'Inter_700Bold', fontSize: 12, color: Colors.loss },
    loanTrack: { height: 8, borderRadius: 999, backgroundColor: Colors.surfaceContainerHighest, overflow: 'hidden' },
    loanFill: { height: '100%', backgroundColor: Colors.loss, borderRadius: 999 },
    loanBalance: { fontFamily: 'Inter_500Medium', fontSize: 12, color: Colors.onSurfaceVariant },
    emptyCard: { alignItems: 'center', gap: 8, paddingVertical: 24 },
    emptyTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 14, color: Colors.onSurface },
    emptyBody: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.muted, textAlign: 'center', maxWidth: 260 },
  });
