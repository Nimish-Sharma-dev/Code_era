import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { Icon, IconName } from '@/components/ui/Icon';
import { ProgressDots } from '@/components/ui/ProgressDots';
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
];

const QUICK_ADD: Record<Wallet['assetType'], { symbol: string; label: string; icon: IconName }[]> = {
  crypto: [
    { symbol: 'BTC', label: 'Bitcoin', icon: 'bitcoin' },
    { symbol: 'ETH', label: 'Ethereum', icon: 'ethereum' },
    { symbol: 'SOL', label: 'Solana', icon: 'solana' },
    { symbol: 'USDC', label: 'USDC', icon: 'usdc' },
  ],
  stock: [
    { symbol: 'NVDA', label: 'Nvidia', icon: 'wallet' },
    { symbol: 'AAPL', label: 'Apple', icon: 'wallet' },
  ],
  mutual_fund: [{ symbol: 'NIFTY50', label: 'Index fund', icon: 'pieChart' }],
  fd: [{ symbol: 'FD', label: 'Fixed deposit', icon: 'bank' }],
  cash: [],
};

export default function WalletsOnboardingScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);
  const completeOnboarding = useFinanceStore((s) => s.completeOnboarding);
  const [assetClass, setAssetClass] = useState<Wallet['assetType']>('crypto');
  const [symbol, setSymbol] = useState('');
  const [label, setLabel] = useState('');
  const [quantity, setQuantity] = useState('');
  const [value, setValue] = useState('');
  const [added, setAdded] = useState<Wallet[]>([]);

  function addWallet() {
    const qty = parseFloat(quantity);
    const val = parseFloat(value.replace(/,/g, ''));
    if (!symbol || Number.isNaN(val) || val <= 0) return;
    const wallet: Wallet = {
      id: `draft_${added.length}`,
      assetType: assetClass,
      label: label || symbol,
      symbol,
      quantity: Number.isNaN(qty) ? 0 : qty,
      balance: val,
      changePct: 0,
    };
    setAdded((prev) => [...prev, wallet]);
    setSymbol('');
    setLabel('');
    setQuantity('');
    setValue('');
  }

  function onComplete() {
    added.forEach((w) => createWallet(w));
    completeOnboarding();
    router.replace('/(onboarding)/complete');
  }

  const total = added.reduce((s, w) => s + w.balance, 0);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.progressWrap}>
        <ProgressDots total={4} current={3} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.iconBadge}>
            <Icon name="pieChart" size={26} color={Colors.secondary} />
          </View>
          <Text style={styles.title}>Connect wallets</Text>
          <Text style={styles.subtitle}>Review your tracked assets and finalize your trading dashboard.</Text>
        </View>

        <View style={styles.chipRow}>
          {ASSET_CLASSES.map((c) => (
            <Chip key={c.key} label={c.label} active={assetClass === c.key} onPress={() => setAssetClass(c.key)} />
          ))}
        </View>

        <View style={styles.quickAddRow}>
          {QUICK_ADD[assetClass].map((q) => (
            <Pressable
              key={q.symbol}
              style={styles.quickAddChip}
              onPress={() => {
                setSymbol(q.symbol);
                setLabel(q.label);
              }}
            >
              <Icon name={q.icon} size={16} color={Colors.warning} />
              <Text style={styles.quickAddLabel}>{q.symbol}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.addForm}>
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
              value={quantity}
              onChangeText={setQuantity}
              placeholder="Quantity"
              placeholderTextColor={Colors.muted}
              keyboardType="decimal-pad"
            />
            <TextInput
              style={[styles.input, styles.flex1]}
              value={value}
              onChangeText={setValue}
              placeholder="Value (₹)"
              placeholderTextColor={Colors.muted}
              keyboardType="number-pad"
            />
          </View>
          <Button label="Add to wallet" variant="ghost" onPress={addWallet} />
        </View>

        {added.length > 0 && (
          <View style={styles.list}>
            {added.map((w) => (
              <View key={w.id} style={styles.assetRow}>
                <View style={styles.assetLeft}>
                  <View style={styles.assetIcon}>
                    <Icon name="wallet" size={18} color={Colors.warning} />
                  </View>
                  <View>
                    <Text style={styles.assetName}>{w.label}</Text>
                    <Text style={styles.assetQty}>
                      {w.quantity || ''} {w.symbol}
                    </Text>
                  </View>
                </View>
                <Text style={styles.assetValue}>₹{w.balance.toLocaleString('en-IN')}</Text>
              </View>
            ))}

            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total Value</Text>
              <Text style={styles.totalValue}>₹{total.toLocaleString('en-IN')}</Text>
            </View>
          </View>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <Button label="Complete setup" icon="arrowRight" onPress={onComplete} />
      </View>
    </SafeAreaView>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: Colors.background },
    progressWrap: { paddingHorizontal: 16, paddingTop: 8 },
    scroll: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16, gap: 20 },
    header: { alignItems: 'center', gap: 8 },
    iconBadge: {
      width: 64,
      height: 64,
      borderRadius: Radii.xl,
      backgroundColor: 'rgba(0,194,168,0.13)',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 4,
    },
    title: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 20, color: Colors.onSurface },
    subtitle: {
      fontFamily: 'Inter_400Regular',
      fontSize: 13,
      color: Colors.onSurfaceVariant,
      textAlign: 'center',
      maxWidth: 280,
    },
    chipRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
    quickAddRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
    quickAddChip: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 6,
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: Radii.pill,
      backgroundColor: Colors.surfaceContainerHigh,
      borderWidth: 0.5,
      borderColor: Colors.border,
    },
    quickAddLabel: { fontFamily: 'Inter_600SemiBold', fontSize: 12, color: Colors.onSurface },
    addForm: {
      backgroundColor: Colors.surfaceCard,
      borderWidth: 0.5,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      padding: 16,
      gap: 12,
    },
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
    list: { gap: 8 },
    assetRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: 16,
      backgroundColor: Colors.surfaceCard,
      borderRadius: Radii.lg,
      borderWidth: 0.5,
      borderColor: Colors.border,
    },
    assetLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    assetIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: 'rgba(245,158,11,0.13)',
      alignItems: 'center',
      justifyContent: 'center',
    },
    assetName: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
    assetQty: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.onSurfaceVariant },
    assetValue: { fontFamily: 'Inter_600SemiBold', fontSize: 16, color: Colors.onSurface },
    totalRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: 16,
      backgroundColor: Colors.elevatedCard,
      borderRadius: Radii.lg,
    },
    totalLabel: { fontFamily: 'Inter_500Medium', fontSize: 14, color: Colors.onSurfaceVariant },
    totalValue: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 20, color: Colors.primary },
    footer: { paddingHorizontal: 16, paddingVertical: 16, borderTopWidth: 0.5, borderTopColor: Colors.border },
  });
