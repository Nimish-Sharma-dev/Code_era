import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { ColorPalette } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';

export default function SplashScreen() {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.brandSection}>
          <View style={styles.logoMark}>
            <Icon name="wallet" size={28} color={Colors.primary} />
          </View>
          <Text style={styles.title}>SmartWallet AI</Text>
          <Text style={styles.subtitle}>Your personal financial intelligence copilot</Text>
        </View>

        <View style={styles.actions}>
          <Button label="Get started" onPress={() => router.push('/(auth)/register')} />
          <Button
            label="Sign in to existing account"
            variant="ghost"
            onPress={() => router.push('/(auth)/login')}
          />
        </View>

        <View style={styles.previewWrap}>
          <View style={styles.previewRow}>
            {[18, 34, 22, 44, 30, 50, 26].map((h, i) => (
              <View key={i} style={[styles.previewBar, { height: h }]} />
            ))}
          </View>
          <Icon name="markets" size={20} color={Colors.secondary} style={styles.previewIcon} />
        </View>
      </ScrollView>

      <Text style={styles.footer}>
        By continuing you agree to our{'\n'}Terms & Privacy Policy
      </Text>
    </SafeAreaView>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: Colors.background,
    },
    scroll: {
      flexGrow: 1,
      alignItems: 'center',
      justifyContent: 'center',
      paddingHorizontal: 32,
      paddingTop: 60,
    },
    brandSection: {
      alignItems: 'center',
      marginBottom: 56,
    },
    logoMark: {
      width: 64,
      height: 64,
      borderRadius: 18,
      backgroundColor: 'rgba(108,99,255,0.13)',
      borderWidth: 1,
      borderColor: 'rgba(108,99,255,0.3)',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 24,
    },
    title: {
      fontFamily: 'SpaceGrotesk_700Bold',
      fontSize: 26,
      color: Colors.textPrimary,
    },
    subtitle: {
      fontFamily: 'Inter_500Medium',
      fontSize: 13,
      color: Colors.muted,
      marginTop: 8,
      textAlign: 'center',
    },
    actions: {
      width: '100%',
      gap: 12,
    },
    previewWrap: {
      marginTop: 48,
      width: '100%',
      aspectRatio: 16 / 9,
      borderRadius: 16,
      overflow: 'hidden',
      borderWidth: 0.5,
      borderColor: Colors.border,
      backgroundColor: Colors.surfaceDim,
      opacity: 0.6,
    },
    previewRow: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'flex-end',
      gap: 6,
      paddingHorizontal: 16,
      paddingBottom: 16,
    },
    previewBar: {
      flex: 1,
      borderRadius: 3,
      backgroundColor: 'rgba(0,194,168,0.35)',
    },
    previewIcon: {
      position: 'absolute',
      top: 12,
      right: 12,
    },
    footer: {
      position: 'absolute',
      bottom: 40,
      left: 0,
      right: 0,
      textAlign: 'center',
      fontFamily: 'Inter_400Regular',
      fontSize: 11,
      color: Colors.mutedDark,
      lineHeight: 16,
    },
  });
