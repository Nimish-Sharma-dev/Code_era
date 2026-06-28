import { Redirect } from 'expo-router';

import { useFinanceStore } from '@/store/useFinanceStore';

export default function Index() {
  const isAuthenticated = useFinanceStore((s) => s.isAuthenticated);
  const onboardingComplete = useFinanceStore((s) => s.onboardingComplete);

  if (!isAuthenticated) {
    return <Redirect href="/(auth)/splash" />;
  }
  if (!onboardingComplete) {
    return <Redirect href="/(onboarding)/income" />;
  }
  return <Redirect href="/(tabs)" />;
}
