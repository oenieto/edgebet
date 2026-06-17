import { apiFetch } from './client';

export interface BankrollBet {
  match: string;
  profit: number;
  odds: number | null;
}

export interface EquityPoint {
  date: string;
  balance: number;
}

export interface BankrollSummary {
  configured?: boolean;
  initial_capital: number;
  current_balance: number;
  currency: string;
  total_pnl: number;
  total_pnl_pct: number;
  roi: number;
  total_bets: number;
  won: number;
  lost: number;
  void: number;
  win_rate: number;
  current_streak: number;
  longest_win_streak: number;
  longest_loss_streak: number;
  avg_odds: number;
  avg_stake: number;
  best_bet: BankrollBet | null;
  worst_bet: BankrollBet | null;
  equity_log: EquityPoint[];
}

export type TxType =
  | 'deposit'
  | 'withdrawal'
  | 'bet_placed'
  | 'bet_won'
  | 'bet_lost'
  | 'bet_void'
  | 'adjustment';

export interface BankrollTransaction {
  id: number;
  type: TxType;
  amount: number;
  balance_after: number;
  reference_id: number | null;
  note: string | null;
  created_at: string;
}

export interface TransactionsPage {
  total: number;
  page: number;
  transactions: BankrollTransaction[];
}

export class BankrollNotConfigured extends Error {}

export function getBankrollSummary(token: string | null): Promise<BankrollSummary> {
  return apiFetch<BankrollSummary>('/bankroll/summary', { token });
}

export function setupBankroll(
  token: string | null,
  body: { initial_capital: number; currency: string },
): Promise<BankrollSummary> {
  return apiFetch<BankrollSummary>('/bankroll/setup', { method: 'POST', body, token });
}

export function depositBankroll(
  token: string | null,
  body: { amount: number; note?: string },
): Promise<BankrollSummary> {
  return apiFetch<BankrollSummary>('/bankroll/deposit', { method: 'POST', body, token });
}

export function withdrawBankroll(
  token: string | null,
  body: { amount: number; note?: string },
): Promise<BankrollSummary> {
  return apiFetch<BankrollSummary>('/bankroll/withdraw', { method: 'POST', body, token });
}

export function getBankrollTransactions(
  token: string | null,
  page = 1,
  limit = 20,
): Promise<TransactionsPage> {
  return apiFetch<TransactionsPage>(`/bankroll/transactions?page=${page}&limit=${limit}`, { token });
}
