import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';

import { ColorPalette } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { Icon } from './ui/Icon';

interface TopBarProps {
  title?: string;
  live?: boolean;
  showBack?: boolean;
}

export function TopBar({ title = 'SmartWallet AI', live = true, showBack = false }: TopBarProps) {
  const router = useRouter();
  const Colors = useColors();
  const styles = getStyles(Colors);

  return (
    <View style={styles.header}>
      <View style={styles.left}>
        {showBack ? (
          <Pressable onPress={() => router.back()} style={styles.avatar}>
            <Icon name="arrowRight" size={18} color={Colors.primary} style={{ transform: [{ rotate: '180deg' }] }} />
          </Pressable>
        ) : (
          <Pressable onPress={() => router.push('/profile')} style={styles.avatar}>
            <Icon name="person" size={18} color={Colors.primary} />
          </Pressable>
        )}
        <Text style={styles.title}>{title}</Text>
      </View>
      {live && (
        <View style={styles.liveWrap}>
          <Icon name="live" size={20} color={Colors.primary} />
        </View>
      )}
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    header: {
      height: 64,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: Colors.border,
      backgroundColor: Colors.surface,
    },
    left: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
    },
    avatar: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: Colors.surfaceContainerHigh,
      alignItems: 'center',
      justifyContent: 'center',
    },
    title: {
      fontFamily: 'SpaceGrotesk_700Bold',
      fontSize: 16,
      color: Colors.primary,
    },
    liveWrap: {
      width: 40,
      height: 40,
      alignItems: 'center',
      justifyContent: 'center',
    },
  });
