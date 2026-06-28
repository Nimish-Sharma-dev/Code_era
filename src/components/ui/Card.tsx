import { StyleSheet, View, ViewProps } from 'react-native';

import { Colors, Radii, Spacing } from '@/constants/theme';

interface CardProps extends ViewProps {
  variant?: 'default' | 'low' | 'elevated';
  borderColor?: string;
  noPadding?: boolean;
}

export function Card({ variant = 'default', borderColor, noPadding, style, ...rest }: CardProps) {
  const bg =
    variant === 'low'
      ? Colors.surfaceContainerLow
      : variant === 'elevated'
        ? Colors.elevatedCard
        : Colors.surfaceCard;

  return (
    <View
      {...rest}
      style={[
        styles.base,
        { backgroundColor: bg, borderColor: borderColor ?? Colors.border },
        !noPadding && { padding: Spacing.cardPadding },
        style,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: Radii.DEFAULT,
    borderWidth: 0.5,
  },
});
