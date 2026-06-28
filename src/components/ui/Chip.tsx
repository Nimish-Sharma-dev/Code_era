import { Pressable, StyleSheet, Text } from 'react-native';

import { Colors, Radii } from '@/constants/theme';

interface ChipProps {
  label: string;
  active?: boolean;
  onPress?: () => void;
}

export function Chip({ label, active, onPress }: ChipProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        active ? styles.active : styles.inactive,
        pressed && styles.pressed,
      ]}
    >
      <Text style={[styles.label, { color: active ? Colors.primaryLight : Colors.textSecondary }]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  active: {
    backgroundColor: 'rgba(108,99,255,0.13)',
    borderColor: Colors.primary,
  },
  inactive: {
    backgroundColor: Colors.surfaceContainer,
    borderColor: Colors.border,
  },
  pressed: {
    transform: [{ scale: 0.96 }],
  },
  label: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 14,
  },
});
