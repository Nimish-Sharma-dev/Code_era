import { StyleSheet, Text, View } from 'react-native';

import { ColorPalette, Radii } from '@/constants/theme';
import { useColors } from '@/hooks/useColors';
import { ChatMessage } from '@/types';

const PERSONA_LABEL: Record<string, string> = {
  day_trader: 'Day Trader',
  swing: 'Swing Trader',
  investor: 'Long-Term Investor',
  crypto: 'Crypto Native',
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

export function ChatBubble({ message }: { message: ChatMessage }) {
  const Colors = useColors();
  const styles = getStyles(Colors);
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <View style={styles.userWrap}>
        <View style={styles.userBubble}>
          <Text style={styles.userText}>{message.content}</Text>
        </View>
        <Text style={styles.timeRight}>{formatTime(message.timestamp)}</Text>
      </View>
    );
  }

  return (
    <View style={styles.aiWrap}>
      <Text style={styles.aiLabel}>
        Saras AI · {PERSONA_LABEL[message.persona ?? 'day_trader']} mode
      </Text>
      <View style={styles.aiBubble}>
        <Text style={styles.aiText}>{message.content}</Text>
      </View>
      <Text style={styles.timeLeft}>{formatTime(message.timestamp)}</Text>
    </View>
  );
}

const getStyles = (Colors: ColorPalette) =>
  StyleSheet.create({
    userWrap: { alignSelf: 'flex-end', maxWidth: '85%', gap: 6 },
    userBubble: {
      backgroundColor: Colors.primary,
      borderRadius: Radii.lg,
      padding: 14,
    },
    userText: { fontFamily: 'Inter_400Regular', fontSize: 15, color: '#FFFFFF', lineHeight: 21 },
    timeRight: { fontFamily: 'Inter_400Regular', fontSize: 10, color: Colors.outline, textAlign: 'right', marginRight: 4 },
    aiWrap: { alignSelf: 'flex-start', maxWidth: '85%', gap: 6 },
    aiLabel: { fontFamily: 'Inter_600SemiBold', fontSize: 12, color: Colors.primaryLight, marginLeft: 4 },
    aiBubble: {
      backgroundColor: Colors.surface,
      borderWidth: 1,
      borderColor: Colors.border,
      borderRadius: Radii.lg,
      padding: 14,
    },
    aiText: { fontFamily: 'Inter_400Regular', fontSize: 15, color: Colors.onSurface, lineHeight: 21 },
    timeLeft: { fontFamily: 'Inter_400Regular', fontSize: 10, color: Colors.outline, marginLeft: 4 },
  });
