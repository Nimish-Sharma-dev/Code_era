import { ColorPalette, DarkColors, LightColors } from '@/constants/theme';
import { useFinanceStore } from '@/store/useFinanceStore';

// Reactive color palette — subscribes to the persisted theme mode so every
// component re-renders with the right colors when the user toggles theme in
// Profile. Call this inside component bodies (not at module scope), since
// module-level `StyleSheet.create` calls are evaluated once and won't react.
export function useColors(): ColorPalette {
  const mode = useFinanceStore((s) => s.themeMode);
  return mode === 'light' ? LightColors : DarkColors;
}
