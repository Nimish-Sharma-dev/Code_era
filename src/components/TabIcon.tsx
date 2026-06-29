import { StyleSheet, Text, View } from 'react-native';

import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { Icon, IconName } from './ui/Icon';

interface TabIconProps {
  name: IconName;
  label: string;
  focused: boolean;
}

export function TabIcon({ name, label, focused }: TabIconProps) {
  const Colors = useColors();
  const styles = getStyles(Colors);

  return (
    <View style={[styles.pill, focused && styles.pillActive]}>
      <Icon name={name} size={22} color={focused ? Colors.primary : Colors.outline} />
      <Text style={[styles.label, { color: focused ? Colors.primary : Colors.outline }]}>{label}</Text>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    pill: {
      alignItems: 'center',
      justifyContent: 'center',
      gap: 2,
      paddingHorizontal: 16,
      paddingVertical: 6,
      borderRadius: Radii.pill,
      minWidth: 56,
    },
    pillActive: {
      backgroundColor: Colors.surfaceContainerHighest,
    },
    label: {
      fontFamily: 'Inter_500Medium',
      fontSize: 10,
    },
  });
