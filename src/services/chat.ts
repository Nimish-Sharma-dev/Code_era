import { hasOpenRouter } from '@/constants/config';
import { useFinanceStore } from '@/store/useFinanceStore';
import { genId } from '@/utils/id';
import { ChatMessage, Persona } from '@/types';
import { ChatTurn, openRouterChat } from './openrouter';

// Local stand-in for POST /chat/message (spec section 5.4 / 6.2). Builds
// the same "contextual subgraph extraction" the spec describes — a
// snapshot of loans, wallets and risk profile — and injects it as a
// system-prompt prefix before calling the LLM, so every reply is grounded
// in the user's actual financial picture rather than generic commentary.

const PERSONA_LABEL: Record<Persona, string> = {
  day_trader: 'Day Trader',
  swing: 'Swing Trader',
  investor: 'Long-Term Investor',
  crypto: 'Crypto Native',
};

function buildContextSnapshot(): string {
  const state = useFinanceStore.getState();
  const profile = {
    riskScore: state.riskScore100(),
    freeCashFlow: Math.round(state.freeCashFlow()),
    burnRateRisk: state.burnRateRisk(),
    loans: state.loans.map((l) => ({ label: l.label, balance: l.balance, aprPct: l.interestRate })),
    wallets: state.wallets.map((w) => ({ label: w.label, symbol: w.symbol, balanceInr: w.balance })),
    netWorth: Math.round(state.totalWalletValue() - state.totalDebt()),
  };
  return JSON.stringify(profile);
}

function localFallbackReply(message: string, persona: Persona): string {
  const state = useFinanceStore.getState();
  const debt = state.totalDebt();
  const fcf = Math.round(state.freeCashFlow());
  const loan = state.highestInterestLoan();

  if (debt > 0 && loan && /invest|buy|allocat/i.test(message)) {
    return `As your ${PERSONA_LABEL[persona]} copilot: you're carrying ₹${Math.round(loan.balance).toLocaleString('en-IN')} on "${loan.label}" at ${loan.interestRate}% APR. Before deploying new capital, weigh that guaranteed cost against any opportunity's expected return — the debt arbitrage engine on your dashboard does this comparison automatically.`;
  }
  return `As your ${PERSONA_LABEL[persona]} copilot: your free cash flow is ₹${fcf.toLocaleString('en-IN')}/mo and burn rate risk is ${state.burnRateRisk()}. Connect a live model (OPENROUTER_API_KEY) for fully generative answers — for now I can only reason from your stored profile, so ask me about your debts, wallets, or risk posture.`;
}

export async function sendChatMessage(message: string, persona: Persona): Promise<ChatMessage> {
  const state = useFinanceStore.getState();
  state.setActivePersona(persona);

  const userMessage: ChatMessage = {
    id: genId('msg'),
    role: 'user',
    content: message,
    persona,
    timestamp: new Date().toISOString(),
  };
  state.addChatMessage(userMessage);

  let replyText: string;
  if (hasOpenRouter) {
    try {
      const context = buildContextSnapshot();
      const turns: ChatTurn[] = [
        {
          role: 'system',
          content: `You are Saras AI, SmartWallet AI's financial copilot, currently in "${PERSONA_LABEL[persona]}" mode. Ground every answer in this user's actual financial context — never give generic advice that ignores it. User context (JSON): ${context}. Keep responses under 120 words, be specific with numbers from the context, and flag risk where relevant.`,
        },
        ...state.chatHistory.slice(-6).map<ChatTurn>((m) => ({
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content,
        })),
        { role: 'user', content: message },
      ];
      replyText = await openRouterChat(turns);
    } catch {
      replyText = localFallbackReply(message, persona);
    }
  } else {
    replyText = localFallbackReply(message, persona);
  }

  const assistantMessage: ChatMessage = {
    id: genId('msg'),
    role: 'assistant',
    content: replyText,
    persona,
    timestamp: new Date().toISOString(),
  };
  state.addChatMessage(assistantMessage);
  return assistantMessage;
}

export function getChatHistory(limit = 20): ChatMessage[] {
  const history = useFinanceStore.getState().chatHistory;
  return history.slice(-limit);
}
