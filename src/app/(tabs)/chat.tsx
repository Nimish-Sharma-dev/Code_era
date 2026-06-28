import { useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ChatBubble } from '@/components/ChatBubble';
import { Icon } from '@/components/ui/Icon';
import { Colors, Radii } from '@/constants/theme';
import { sendChatMessage } from '@/services/chat';
import { useFinanceStore } from '@/store/useFinanceStore';
import { Persona } from '@/types';

const PERSONAS: { key: Persona; label: string }[] = [
  { key: 'day_trader', label: 'Day Trader' },
  { key: 'swing', label: 'Swing Trader' },
  { key: 'investor', label: 'Investor' },
  { key: 'crypto', label: 'Crypto Native' },
];

export default function ChatScreen() {
  const params = useLocalSearchParams<{ prefill?: string }>();
  const chatHistory = useFinanceStore((s) => s.chatHistory);
  const activePersona = useFinanceStore((s) => s.activePersona);
  const setActivePersona = useFinanceStore((s) => s.setActivePersona);
  const totalWalletValue = useFinanceStore((s) => s.totalWalletValue());
  const totalDebt = useFinanceStore((s) => s.totalDebt());
  const riskScore = useFinanceStore((s) => s.riskScore100());

  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    if (params.prefill) setInput(params.prefill);
  }, [params.prefill]);

  useEffect(() => {
    scrollRef.current?.scrollToEnd({ animated: true });
  }, [chatHistory.length]);

  function cyclePersona() {
    const idx = PERSONAS.findIndex((p) => p.key === activePersona);
    setActivePersona(PERSONAS[(idx + 1) % PERSONAS.length].key);
  }

  async function onSend() {
    const message = input.trim();
    if (!message || sending) return;
    setInput('');
    setSending(true);
    try {
      await sendChatMessage(message, activePersona);
    } finally {
      setSending(false);
    }
  }

  const netWorth = totalWalletValue - totalDebt;
  const personaLabel = PERSONAS.find((p) => p.key === activePersona)?.label ?? 'Day Trader';

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.avatar}>
            <Icon name="person" size={18} color={Colors.primary} />
          </View>
          <View>
            <Text style={styles.headerTitle}>Saras AI</Text>
            <Text style={styles.headerSubtitle}>Advanced Trading Copilot</Text>
          </View>
        </View>
        <Pressable style={styles.personaPill} onPress={cyclePersona}>
          <Text style={styles.personaPillText}>{personaLabel}</Text>
          <Icon name="chevronDown" size={16} color={Colors.primary} />
        </Pressable>
      </View>

      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.chipsRow}>
            <ContextChip icon="bank" color={Colors.secondary} label={`Net worth: ₹${Math.round(netWorth).toLocaleString('en-IN')}`} />
            <ContextChip icon="trendingDown" color={Colors.loss} label={`Debt: ₹${Math.round(totalDebt).toLocaleString('en-IN')}`} />
            <ContextChip icon="security" color={Colors.primary} label={`Risk: ${riskScore}/100`} />
          </View>

          <View style={styles.messages}>
            {chatHistory.length === 0 && (
              <Text style={styles.emptyState}>
                Ask Saras about your debts, wallets, or what to do with your free cash flow.
              </Text>
            )}
            {chatHistory.map((m) => (
              <ChatBubble key={m.id} message={m} />
            ))}
            {sending && (
              <View style={styles.typingRow}>
                <ActivityIndicator size="small" color={Colors.outline} />
              </View>
            )}
          </View>
        </ScrollView>

        <View style={styles.inputBar}>
          <Pressable style={styles.inputBtn}>
            <Icon name="addCircle" size={20} color={Colors.outline} />
          </Pressable>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Message Saras AI..."
            placeholderTextColor={Colors.outline}
            multiline
          />
          <Pressable style={styles.inputBtn}>
            <Icon name="mic" size={20} color={Colors.outline} />
          </Pressable>
          <Pressable style={styles.sendBtn} onPress={onSend} disabled={sending}>
            <Icon name="send" size={18} color="#FFFFFF" />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function ContextChip({ icon, color, label }: { icon: 'bank' | 'trendingDown' | 'security'; color: string; label: string }) {
  return (
    <View style={[styles.contextChip, { borderColor: color, backgroundColor: `${color}0D` }]}>
      <Icon name={icon} size={16} color={color} />
      <Text style={[styles.contextChipText, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
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
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.surfaceContainer,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: { fontFamily: 'Inter_700Bold', fontSize: 14, color: Colors.onSurface },
  headerSubtitle: { fontFamily: 'Inter_400Regular', fontSize: 12, color: Colors.outline },
  personaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: Colors.surfaceContainerHigh,
    borderWidth: 0.5,
    borderColor: Colors.border,
  },
  personaPillText: { fontFamily: 'Inter_600SemiBold', fontSize: 13, color: Colors.primary },
  scroll: { padding: 16, paddingBottom: 24, gap: 20 },
  chipsRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  contextChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  contextChipText: { fontFamily: 'Inter_600SemiBold', fontSize: 12 },
  messages: { gap: 20 },
  emptyState: {
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
    color: Colors.muted,
    textAlign: 'center',
    paddingVertical: 32,
  },
  typingRow: { paddingLeft: 4 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.surfaceContainer,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 999,
    padding: 6,
    margin: 16,
  },
  inputBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  input: {
    flex: 1,
    color: Colors.onSurface,
    fontFamily: 'Inter_400Regular',
    fontSize: 15,
    maxHeight: 100,
    paddingHorizontal: 4,
  },
  sendBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
