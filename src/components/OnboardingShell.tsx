import { ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Colors, Radii } from '@/constants/theme';
import { Button } from './ui/Button';
import { Icon, IconName } from './ui/Icon';
import { ProgressDots } from './ui/ProgressDots';

interface OnboardingShellProps {
  step: number;
  totalSteps?: number;
  icon: IconName;
  iconColor?: string;
  title: string;
  subtitle: string;
  children: ReactNode;
  ctaLabel: string;
  onContinue: () => void;
  ctaLoading?: boolean;
}

export function OnboardingShell({
  step,
  totalSteps = 4,
  icon,
  iconColor = Colors.primaryLight,
  title,
  subtitle,
  children,
  ctaLabel,
  onContinue,
  ctaLoading,
}: OnboardingShellProps) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.progressWrap}>
        <ProgressDots total={totalSteps} current={step} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.iconBadge}>
          <Icon name={icon} size={22} color={iconColor} />
        </View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>

        <View style={styles.body}>{children}</View>

        <View style={styles.securityCard}>
          <View style={styles.securityIcon}>
            <Icon name="security" size={18} color={Colors.secondary} />
          </View>
          <View style={styles.securityTextWrap}>
            <Text style={styles.securityTitle}>TRADEX SECURITY</Text>
            <Text style={styles.securityBody}>
              Your data is encrypted using institutional-grade protocols for total privacy.
            </Text>
          </View>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Button label={ctaLabel} icon="arrowRight" onPress={onContinue} loading={ctaLoading} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  progressWrap: { paddingHorizontal: 16, paddingTop: 8 },
  scroll: { paddingHorizontal: 16, paddingTop: 24, paddingBottom: 16 },
  iconBadge: {
    width: 48,
    height: 48,
    borderRadius: Radii.lg,
    backgroundColor: 'rgba(108,99,255,0.13)',
    borderWidth: 1,
    borderColor: 'rgba(108,99,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 20,
    color: Colors.textPrimary,
  },
  subtitle: {
    fontFamily: 'Inter_400Regular',
    fontSize: 13,
    color: Colors.muted,
    marginTop: 4,
    lineHeight: 18,
  },
  body: { marginTop: 24, gap: 24 },
  securityCard: {
    marginTop: 32,
    backgroundColor: Colors.elevatedCard,
    borderWidth: 0.5,
    borderColor: Colors.border,
    borderRadius: Radii.lg,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  securityIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
  },
  securityTextWrap: { flex: 1, gap: 2 },
  securityTitle: {
    fontFamily: 'Inter_700Bold',
    fontSize: 11,
    letterSpacing: 0.4,
    color: Colors.onSurface,
  },
  securityBody: {
    fontFamily: 'Inter_400Regular',
    fontSize: 12,
    color: Colors.muted,
    lineHeight: 16,
  },
  footer: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingTop: 8,
  },
});
