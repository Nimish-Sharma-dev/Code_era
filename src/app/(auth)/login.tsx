import { useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { Colors, Radii } from '@/constants/theme';
import { loginRequest } from '@/services/auth';
import { useFinanceStore } from '@/store/useFinanceStore';

export default function LoginScreen() {
  const router = useRouter();
  const onboardingComplete = useFinanceStore((s) => s.onboardingComplete);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function onSubmit() {
    setError('');
    setLoading(true);
    try {
      await loginRequest(email.trim(), password);
      router.replace(onboardingComplete ? '/(tabs)' : '/(onboarding)/income');
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.content}>
          <View style={styles.iconBadge}>
            <Icon name="shieldLock" size={22} color={Colors.primaryLight} />
          </View>
          <Text style={styles.heading}>Welcome back</Text>
          <Text style={styles.subheading}>Sign in to pick up where you left off.</Text>

          <View style={styles.form}>
            <Field
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="alex@email.com"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <Field label="Password" value={password} onChangeText={setPassword} placeholder="••••••••" secureTextEntry />
          </View>

          {!!error && <Text style={styles.error}>{error}</Text>}

          <View style={styles.footer}>
            <Button label="Sign in" icon="arrowRight" onPress={onSubmit} loading={loading} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  secureTextEntry?: boolean;
  keyboardType?: 'default' | 'email-address';
  autoCapitalize?: 'none' | 'sentences';
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{props.label.toUpperCase()}</Text>
      <TextInput
        style={styles.input}
        value={props.value}
        onChangeText={props.onChangeText}
        placeholder={props.placeholder}
        placeholderTextColor={Colors.muted}
        secureTextEntry={props.secureTextEntry}
        keyboardType={props.keyboardType}
        autoCapitalize={props.autoCapitalize}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  content: { flex: 1, paddingHorizontal: 32, paddingTop: 40 },
  iconBadge: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: 'rgba(108,99,255,0.13)',
    borderWidth: 1,
    borderColor: 'rgba(108,99,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  heading: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 20,
    color: Colors.textPrimary,
  },
  subheading: {
    fontFamily: 'Inter_400Regular',
    fontSize: 13,
    color: Colors.muted,
    marginTop: 6,
    lineHeight: 18,
  },
  form: { marginTop: 32, gap: 20 },
  fieldWrap: { gap: 8 },
  fieldLabel: {
    fontFamily: 'Inter_500Medium',
    fontSize: 10,
    letterSpacing: 1,
    color: Colors.primaryLight,
  },
  input: {
    backgroundColor: Colors.surfaceCard,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radii.md,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: Colors.textPrimary,
    fontFamily: 'Inter_600SemiBold',
    fontSize: 16,
  },
  error: {
    marginTop: 16,
    color: Colors.loss,
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
  },
  footer: { marginTop: 'auto', paddingBottom: 24 },
});
