/**
 * SmartWallet AI design tokens — sourced from the Stitch design system
 * (smartwallet_ai_tradex/DESIGN.md) and the product spec's brand section.
 * Dark-first fintech aesthetic only — there is no light theme variant.
 */

export const Colors = {
  // Core surfaces
  background: '#0A0B0F',
  surface: '#13121b',
  surfaceDim: '#0D0F16',
  surfaceContainerLowest: '#0e0d16',
  surfaceContainerLow: '#1b1b24',
  surfaceContainer: '#1f1f28',
  surfaceContainerHigh: '#2a2933',
  surfaceContainerHighest: '#35343e',
  surfaceCard: '#12141A',
  elevatedCard: '#1C1F2A',
  surfaceBright: '#393842',

  // Brand
  primary: '#6C63FF',
  primaryLight: '#9B95FF',
  primaryContainer: '#8781ff',
  onPrimary: '#FFFFFF',
  secondary: '#00C2A8',
  secondaryAlt: '#41ddc2',

  // Semantic
  gain: '#00E096',
  loss: '#FF4D4D',
  error: '#ffb4ab',
  warning: '#F59E0B',

  // Text
  textPrimary: '#FFFFFF',
  onSurface: '#e4e1ee',
  onSurfaceVariant: '#c7c4d8',
  textSecondary: '#9CA3AF',
  outline: '#918fa1',
  outlineVariant: '#2A2D3A',
  outlineVariantAlt: '#464555',
  muted: '#6B7280',
  mutedDark: '#374151',

  border: '#2A2D3A',
  navBorder: '#1E2130',
} as const;

export const Typography = {
  headlineXl: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 32, lineHeight: 40 },
  headlineLg: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 24, lineHeight: 32 },
  headlineLgMobile: { fontFamily: 'SpaceGrotesk_700Bold', fontSize: 20, lineHeight: 28 },
  cardTitle: { fontFamily: 'Inter_600SemiBold', fontSize: 18, lineHeight: 24 },
  bodyMain: { fontFamily: 'Inter_400Regular', fontSize: 16, lineHeight: 24 },
  labelMd: { fontFamily: 'Inter_500Medium', fontSize: 14, lineHeight: 20 },
  dataTabular: { fontFamily: 'Inter_600SemiBold', fontSize: 16, lineHeight: 20 },
  badgeSm: { fontFamily: 'Inter_600SemiBold', fontSize: 12, lineHeight: 16 },
} as const;

export const Radii = {
  sm: 4,
  md: 10,
  DEFAULT: 12,
  lg: 16,
  xl: 24,
  pill: 999,
  badge: 8,
} as const;

export const Spacing = {
  stackSm: 8,
  stackMd: 16,
  stackLg: 24,
  gutter: 16,
  cardPadding: 16,
  safeArea: 32,
} as const;

export const BottomTabHeight = 80;
