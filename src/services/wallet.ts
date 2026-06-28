import { useFinanceStore } from '@/store/useFinanceStore';
import { FixedExpense, IncomeSource, Loan, RiskBand, Wallet } from '@/types';

// Local stand-ins for POST /user/income|expense|loan|wallet and
// GET /user/profile (spec section 5.2). Each writes to the persisted
// store instead of a Neo4j node, but returns the same response shape the
// real endpoints will, so swapping in app/api/endpoints/wallet.py later
// is a one-line change per call site.

export function createIncome(income: Omit<IncomeSource, 'id'>): { freeCashFlow: number } {
  useFinanceStore.getState().addIncome(income);
  return { freeCashFlow: useFinanceStore.getState().freeCashFlow() };
}

export function createExpense(expense: Omit<FixedExpense, 'id'>): { burnRateRisk: RiskBand } {
  useFinanceStore.getState().addExpense(expense);
  return { burnRateRisk: useFinanceStore.getState().burnRateRisk() };
}

export function createLoan(loan: Omit<Loan, 'id'>): { debtLoad: number } {
  useFinanceStore.getState().addLoan(loan);
  return { debtLoad: useFinanceStore.getState().totalDebt() };
}

export function createWallet(wallet: Omit<Wallet, 'id'>): { id: string } {
  useFinanceStore.getState().addWallet(wallet);
  const wallets = useFinanceStore.getState().wallets;
  return { id: wallets[wallets.length - 1]?.id ?? '' };
}

export function getProfile() {
  const state = useFinanceStore.getState();
  return {
    user: state.user,
    income: state.incomeSources,
    expenses: state.expenses,
    loans: state.loans,
    wallets: state.wallets,
    freeCashFlow: state.freeCashFlow(),
    burnRateRisk: state.burnRateRisk(),
    riskScore: state.riskScore100(),
    totalDebt: state.totalDebt(),
    totalWalletValue: state.totalWalletValue(),
  };
}
