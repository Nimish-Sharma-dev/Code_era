import {
  ActivityIndicator,
  Pressable,
  PressableProps,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { Icon, IconName } from './Icon';

type Variant = 'primary' | 'secondary' | 'ghost' | 'outlineWarning';

interface ButtonProps extends Omit<PressableProps, 'style'> {
  label: string;
  variant?: Variant;
  icon?: IconName;
  loading?: boolean;
  fullWidth?: boolean;
}

export function Button({
  label,
  variant = 'primary',
  icon,
  loading,
  fullWidth = true,
  disabled,
  ...rest
}: ButtonProps) {
  const Colors = useColors();
  const isDisabled = disabled || loading;
  const textColor = getTextColor(Colors);
  const variantStyles = getVariantStyles(Colors);
  const styles = getStyles();

  return (
    <Pressable
      {...rest}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        variantStyles[variant],
        fullWidth && styles.fullWidth,
        pressed && !isDisabled && styles.pressed,
        isDisabled && styles.disabled,
      ]}
    >
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator color={textColor[variant]} />
        ) : (
          <>
            <Text style={[styles.label, { color: textColor[variant] }]}>{label}</Text>
            {icon && <Icon name={icon} size={18} color={textColor[variant]} />}
          </>
        )}
      </View>
    </Pressable>
  );
}

const getTextColor = (Colors: ColorPalette): Record<Variant, string> => ({
  primary: Colors.onPrimary,
  secondary: '#06251F',
  ghost: Colors.textSecondary,
  outlineWarning: Colors.warning,
});

const getVariantStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    primary: {
      backgroundColor: Colors.primary,
    },
    secondary: {
      backgroundColor: Colors.secondary,
    },
    ghost: {
      backgroundColor: 'transparent',
      borderWidth: 0.5,
      borderColor: Colors.border,
    },
    outlineWarning: {
      backgroundColor: 'transparent',
      borderWidth: 0.5,
      borderColor: Colors.border,
    },
  });

const getStyles = () =>
  StyleSheet.create({
    base: {
      borderRadius: Radii.lg,
      paddingVertical: 14,
      alignItems: 'center',
      justifyContent: 'center',
    },
    fullWidth: {
      width: '100%',
    },
    pressed: {
      transform: [{ scale: 0.98 }],
      opacity: 0.92,
    },
    disabled: {
      opacity: 0.5,
    },
    content: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
    },
    label: {
      fontFamily: 'Inter_700Bold',
      fontSize: 15,
    },
  });
