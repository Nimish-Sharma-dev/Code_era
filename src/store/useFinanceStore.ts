import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { SEED_USER } from '@/data/seed';
import {
  ChatMessage,
  FixedExpense,
  IncomeSource,
  Loan,
  Persona,
  RiskBand,
  Trade,
  User,
  Wallet,
} from '@/types';

function genId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export type ThemeMode = 'dark' | 'light';

interface FinanceState {
  hydrated: boolean;
  isAuthenticated: boolean;
  onboardingComplete: boolean;
  themeMode: ThemeMode;

  user: User;
  incomeSources: IncomeSource[];
  expenses: FixedExpense[];
  loans: Loan[];
  wallets: Wallet[];
  trades: Trade[];
  chatHistory: ChatMessage[];
  activePersona: Persona;

  setHydrated: () => void;
  login: (email: string, name?: string) => void;
  logout: () => void;
  completeOnboarding: () => void;
  setThemeMode: (mode: ThemeMode) => void;
  toggleThemeMode: () => void;

  addIncome: (income: Omit<IncomeSource, 'id'>) => void;
  removeIncome: (id: string) => void;
  addExpense: (expense: Omit<FixedExpense, 'id'>) => void;
  removeExpense: (id: string) => void;
  addLoan: (loan: Omit<Loan, 'id'>) => void;
  removeLoan: (id: string) => void;
  addWallet: (wallet: Omit<Wallet, 'id'>) => void;
  updateWallet: (id: string, patch: Partial<Omit<Wallet, 'id'>>) => void;
  removeWallet: (id: string) => void;

  setActivePersona: (persona: Persona) => void;
  addChatMessage: (message: ChatMessage) => void;
  clearChatHistory: () => void;

  importTrades: (trades: Trade[]) => void;

  // Computed selectors
  totalMonthlyIncome: () => number;
  totalMonthlyExpenses: () => number;
  freeCashFlow: () => number;
  burnRateRisk: () => RiskBand;
  totalDebt: () => number;
  highestInterestLoan: () => Loan | undefined;
  totalWalletValue: () => number;
  riskScore100: () => number;
}

export const useFinanceStore = create<FinanceState>()(
  persist(
    (set, get) => ({
      hydrated: false,
      isAuthenticated: false,
      onboardingComplete: false,
      themeMode: 'dark',

      user: SEED_USER,
      incomeSources: [],
      expenses: [],
      loans: [],
      wallets: [],
      trades: [],
      chatHistory: [],
      activePersona: 'day_trader',

      setHydrated: () => set({ hydrated: true }),

      login: (email, name) =>
        set((state) => ({
          isAuthenticated: true,
          user: { ...state.user, email, name: name ?? state.user.name },
        })),

      logout: () => set({ isAuthenticated: false }),

      completeOnboarding: () => set({ onboardingComplete: true }),

      setThemeMode: (mode) => set({ themeMode: mode }),
      toggleThemeMode: () =>
        set((state) => ({ themeMode: state.themeMode === 'dark' ? 'light' : 'dark' })),

      addIncome: (income) =>
        set((state) => ({
          incomeSources: [...state.incomeSources, { ...income, id: genId('inc') }],
        })),

      removeIncome: (id) =>
        set((state) => ({ incomeSources: state.incomeSources.filter((i) => i.id !== id) })),

      addExpense: (expense) =>
        set((state) => ({
          expenses: [...state.expenses, { ...expense, id: genId('exp') }],
        })),

      removeExpense: (id) => set((state) => ({ expenses: state.expenses.filter((e) => e.id !== id) })),

      addLoan: (loan) =>
        set((state) => ({
          loans: [...state.loans, { ...loan, id: genId('loan') }],
        })),

      removeLoan: (id) => set((state) => ({ loans: state.loans.filter((l) => l.id !== id) })),

      addWallet: (wallet) =>
        set((state) => ({
          wallets: [...state.wallets, { ...wallet, id: genId('wal') }],
        })),

      updateWallet: (id, patch) =>
        set((state) => ({
          wallets: state.wallets.map((w) => (w.id === id ? { ...w, ...patch } : w)),
        })),

      removeWallet: (id) => set((state) => ({ wallets: state.wallets.filter((w) => w.id !== id) })),

      setActivePersona: (persona) => set({ activePersona: persona }),

      addChatMessage: (message) =>
        set((state) => ({ chatHistory: [...state.chatHistory, message] })),

      clearChatHistory: () => set({ chatHistory: [] }),

      importTrades: (trades) =>
        set((state) => ({ trades: [...state.trades, ...trades] })),

      totalMonthlyIncome: () => {
        const { incomeSources } = get();
        return incomeSources.reduce((sum, i) => {
          if (i.frequency === 'monthly') return sum + i.amount;
          if (i.frequency === 'weekly') return sum + i.amount * 4.33;
          return sum + i.amount / 12;
        }, 0);
      },

      totalMonthlyExpenses: () => {
        const { expenses } = get();
        return expenses.reduce((sum, e) => sum + e.amount, 0);
      },

      freeCashFlow: () => get().totalMonthlyIncome() - get().totalMonthlyExpenses(),

      burnRateRisk: () => {
        const income = get().totalMonthlyIncome();
        const expenses = get().totalMonthlyExpenses();
        if (income <= 0) return 'MEDIUM';
        const ratio = expenses / income;
        if (ratio >= 0.75) return 'HIGH';
        if (ratio >= 0.45) return 'MEDIUM';
        return 'LOW';
      },

      totalDebt: () => get().loans.reduce((sum, l) => sum + l.balance, 0),

      highestInterestLoan: () => {
        const { loans } = get();
        if (loans.length === 0) return undefined;
        return [...loans].sort((a, b) => b.interestRate - a.interestRate)[0];
      },

      totalWalletValue: () => get().wallets.reduce((sum, w) => sum + w.balance, 0),

      riskScore100: () => Math.round(get().user.riskScore * 100),
    }),
    {
      name: 'smartwallet-finance-store',
      storage: createJSONStorage(() => AsyncStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated();
      },
    },
  ),
);
