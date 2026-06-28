import { StyleSheet, Text, View } from 'react-native';

import { Colors, Radii } from '@/constants/theme';

export type BadgeTone = 'gain' | 'loss' | 'warning' | 'primary' | 'neutral';

const TONE_COLOR: Record<BadgeTone, string> = {
  gain: Colors.secondary,
  loss: Colors.loss,
  warning: Colors.warning,
  primary: Colors.primary,
  neutral: Colors.onSurfaceVariant,
};

interface BadgeProps {
  label: string;
  tone?: BadgeTone;
  uppercase?: boolean;
}

export function Badge({ label, tone = 'neutral', uppercase = true }: BadgeProps) {
  const color = TONE_COLOR[tone];
  return (
    <View style={[styles.base, { backgroundColor: `${color}1A`, borderColor: `${color}4D` }]}>
      <Text style={[styles.text, { color }, uppercase && styles.uppercase]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: Radii.pill,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  text: {
    fontFamily: 'Inter_700Bold',
    fontSize: 10,
    letterSpacing: 0.4,
  },
  uppercase: {
    textTransform: 'uppercase',
  },
});
