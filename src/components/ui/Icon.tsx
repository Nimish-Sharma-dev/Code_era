import { MaterialCommunityIcons } from '@expo/vector-icons';
import React from 'react';

// Maps the Stitch design's Material-Symbols icon names to the closest
// MaterialCommunityIcons glyph so we don't need to ship the web Material
// Symbols font for a few icon lookups.
export const IconMap = {
  home: 'home',
  markets: 'chart-line',
  chat: 'forum',
  portfolio: 'wallet',
  tradex: 'finance',
  live: 'access-point',
  analytics: 'chart-box-outline',
  trendingUp: 'trending-up',
  trendingDown: 'trending-down',
  bank: 'bank',
  wallet: 'wallet-outline',
  search: 'magnify',
  ask: 'creation',
  chevronDown: 'chevron-down',
  addCircle: 'plus-circle-outline',
  security: 'shield-check-outline',
  arrowRight: 'arrow-right',
  pieChart: 'chart-pie',
  ethereum: 'ethereum',
  bitcoin: 'bitcoin',
  solana: 'alpha-s-circle-outline',
  usdc: 'currency-usd-circle-outline',
  warning: 'alert-circle-outline',
  alert: 'alert',
  history: 'history',
  sleep: 'power-sleep',
  upload: 'tray-arrow-up',
  check: 'check-circle',
  person: 'account-circle-outline',
  mic: 'microphone-outline',
  send: 'send',
  read: 'book-open-variant',
  rupee: 'currency-inr',
  plus: 'plus',
  close: 'close',
  shieldLock: 'shield-lock-outline',
  rocket: 'rocket-launch-outline',
  calendar: 'calendar-month-outline',
  fileDocument: 'file-document-outline',
} as const;

export type IconName = keyof typeof IconMap;

interface IconProps {
  name: IconName;
  size?: number;
  color?: string;
  style?: React.ComponentProps<typeof MaterialCommunityIcons>['style'];
}

export function Icon({ name, size = 22, color = '#FFFFFF', style }: IconProps) {
  return (
    <MaterialCommunityIcons name={IconMap[name] as any} size={size} color={color} style={style} />
  );
}
