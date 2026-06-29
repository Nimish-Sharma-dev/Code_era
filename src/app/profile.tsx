import { useRouter } from 'expo-router';
import { ReactNode } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card } from '@/components/ui/Card';
import { Icon } from '@/components/ui/Icon';
import { ColorPalette } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { logoutRequest } from '@/services/auth';
import { useFinanceStore } from '@/store/useFinanceStore';

export default function ProfileScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);

  const user = useFinanceStore((s) => s.user);
  const themeMode = useFinanceStore((s) => s.themeMode);
  const toggleThemeMode = useFinanceStore((s) => s.toggleThemeMode);
  const incomeSources = useFinanceStore((s) => s.incomeSources);
  const expenses = useFinanceStore((s) => s.expenses);
  const loans = useFinanceStore((s) => s.loans);
  const wallets = useFinanceStore((s) => s.wallets);

  function onLogout() {
    Alert.alert('Log out', 'You can sign back in any time — your financial profile stays saved on this device.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log out',
        style: 'destructive',
        onPress: () => {
          logoutRequest();
          router.replace('/(auth)/splash');
        },
      },
    ]);
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable style={styles.backBtn} onPress={() => router.back()}>
          <Icon name="arrowRight" size={18} color={Colors.primary} style={styles.backIcon} />
        </Pressable>
        <Text style={styles.headerTitle}>Profile</Text>
        <View style={styles.backBtn} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.accountCard}>
          <View style={styles.avatar}>
            <Icon name="account" size={28} color={Colors.primary} />
          </View>
          <Text style={styles.name}>{user.name}</Text>
          <View style={styles.emailRow}>
            <Icon name="email" size={14} color={Colors.muted} />
            <Text style={styles.email}>{user.email || 'No email on file'}</Text>
          </View>
        </View>

        <Section title="Appearance">
          <Pressable style={styles.row} onPress={toggleThemeMode}>
            <View style={styles.rowLeft}>
              <View style={styles.rowIcon}>
                <Icon name={themeMode === 'dark' ? 'themeDark' : 'themeLight'} size={18} color={Colors.primary} />
              </View>
              <View>
                <Text style={styles.rowLabel}>Theme</Text>
                <Text style={styles.rowSublabel}>{themeMode === 'dark' ? 'Dark mode' : 'Light mode'}</Text>
              </View>
            </View>
            <View style={styles.toggleTrack}>
              <Icon name="swap" size={16} color={Colors.muted} />
            </View>
          </Pressable>
        </Section>

        <Section title="Financial profile">
          <View style={styles.statsRow}>
            <Stat label="Income" value={incomeSources.length} styles={styles} />
            <Stat label="Expenses" value={expenses.length} styles={styles} />
            <Stat label="Loans" value={loans.length} styles={styles} />
            <Stat label="Wallets" value={wallets.length} styles={styles} />
          </View>
          <Pressable style={styles.row} onPress={() => router.push('/(tabs)/portfolio')}>
            <View style={styles.rowLeft}>
              <View style={styles.rowIcon}>
                <Icon name="wallet" size={18} color={Colors.secondary} />
              </View>
              <Text style={styles.rowLabel}>Manage wallets</Text>
            </View>
            <Icon name="chevronRight" size={18} color={Colors.muted} />
          </Pressable>
          <Pressable style={styles.row} onPress={() => router.push('/(onboarding)/income')}>
            <View style={styles.rowLeft}>
              <View style={styles.rowIcon}>
                <Icon name="rupee" size={18} color={Colors.warning} />
              </View>
              <Text style={styles.rowLabel}>Update income, expenses & debt</Text>
            </View>
            <Icon name="chevronRight" size={18} color={Colors.muted} />
          </Pressable>
        </Section>

        <Section title="Account">
          <Pressable style={styles.row} onPress={onLogout}>
            <View style={styles.rowLeft}>
              <View style={[styles.rowIcon, { backgroundColor: `${Colors.loss}1A` }]}>
                <Icon name="logout" size={18} color={Colors.loss} />
              </View>
              <Text style={[styles.rowLabel, { color: Colors.loss }]}>Log out</Text>
            </View>
          </Pressable>
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const Colors = useColors();
  const styles = getStyles(Colors);
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Card noPadding style={styles.sectionCard}>
        {children}
      </Card>
    </View>
  );
}

function Stat({ label, value, styles }: { label: string; value: number; styles: ReturnType<typeof getStyles> }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: Colors.background },
    header: {
      height: 64,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 12,
      borderBottomWidth: 0.5,
      borderBottomColor: Colors.border,
    },
    backBtn: {
      width: 36,
      height: 36,
      borderRadius: 18,
      backgroundColor: Colors.surfaceContainerHigh,
      alignItems: 'center',
      justifyContent: 'center',
    },
    backIcon: { transform: [{ rotate: '180deg' }] },
    headerTitle: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 18, color: Colors.onSurface },
    scroll: { padding: 16, gap: 24, paddingBottom: 32 },
    accountCard: { alignItems: 'center', gap: 6, paddingVertical: 16 },
    avatar: {
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: `${Colors.primary}1A`,
      borderWidth: 1,
      borderColor: `${Colors.primary}33`,
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 8,
    },
    name: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 18, color: Colors.onSurface },
    emailRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    email: { fontFamily: 'Inter_500Medium', fontSize: 13, color: Colors.muted },
    section: { gap: 10 },
    sectionTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 14, color: Colors.onSurfaceVariant, paddingHorizontal: 4 },
    sectionCard: { overflow: 'hidden' },
    row: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 14,
      borderBottomWidth: 0.5,
      borderBottomColor: Colors.border,
    },
    rowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
    rowIcon: {
      width: 36,
      height: 36,
      borderRadius: 10,
      backgroundColor: Colors.surfaceContainerHigh,
      alignItems: 'center',
      justifyContent: 'center',
    },
    rowLabel: { fontFamily: 'Inter_600SemiBold', fontSize: 14, color: Colors.onSurface },
    rowSublabel: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.muted, marginTop: 1 },
    toggleTrack: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: Colors.surfaceContainerHigh,
      alignItems: 'center',
      justifyContent: 'center',
    },
    statsRow: {
      flexDirection: 'row',
      backgroundColor: Colors.surfaceCard,
      borderBottomWidth: 0.5,
      borderBottomColor: Colors.border,
      paddingVertical: 16,
    },
    stat: { flex: 1, alignItems: 'center', gap: 2 },
    statValue: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 20, color: Colors.primary },
    statLabel: { fontFamily: 'Inter_500Medium', fontSize: 11, color: Colors.muted },
  });
