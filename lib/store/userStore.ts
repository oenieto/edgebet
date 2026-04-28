import { create } from 'zustand';

export interface User {
  id: string;
  email: string;
  name: string;
  tier: string;
  onboarding_done?: boolean;
}

export interface UserProfile {
  risk_profile: 'conservative' | 'balanced' | 'aggressive';
  bankroll: number;
  horizon: string;
  stake_pct: number;
  weekly_limit: number;
  daily_limit: number;
  favorite_leagues: string[];
  xp?: number;
}

export interface BankrollData {
  current_amount: number;
  initial_amount: number;
  pnl_total: number;
  pnl_pct: number;
  sparkline_data: { date: string; amount: number }[];
}

export interface AlertStatus {
  id: string;
  alert_type: string;
  enabled: boolean;
  threshold_pct: number;
  triggered_at?: string;
}

interface UserStore {
  user: User | null;
  profile: UserProfile | null;
  bankroll: BankrollData | null;
  alerts: AlertStatus[];
  weeklyUsed: number;
  isLoading: boolean;

  setUser: (user: User) => void;
  setProfile: (profile: UserProfile) => void;
  updateBankroll: (data: BankrollData) => void;
  updateAlerts: (alerts: AlertStatus[], weeklyUsed: number) => void;
  completeOnboarding: () => void;
  resetUser: () => void;

  suggestedStake: () => number;
  weeklyUsedPct: () => number;
  isOverWeeklyLimit: () => boolean;
  isOnboardingDone: () => boolean;
}

export const useUserStore = create<UserStore>((set, get) => ({
  user: null,
  profile: null,
  bankroll: null,
  alerts: [],
  weeklyUsed: 0,
  isLoading: false,

  setUser: (user) => set({ user }),
  setProfile: (profile) => set({ profile }),
  updateBankroll: (data) => set({ bankroll: data }),
  updateAlerts: (alerts, weeklyUsed) => set({ alerts, weeklyUsed }),
  completeOnboarding: () => set((state) => ({ user: state.user ? { ...state.user, onboarding_done: true } : null })),
  resetUser: () => set({ user: null, profile: null, bankroll: null, alerts: [], weeklyUsed: 0 }),

  suggestedStake: () => {
    const { profile } = get();
    if (!profile || profile.bankroll <= 0) return 0;
    return profile.bankroll * (profile.stake_pct / 100);
  },
  
  weeklyUsedPct: () => {
    const { profile, weeklyUsed } = get();
    if (!profile || profile.weekly_limit <= 0) return 0;
    return (weeklyUsed / profile.weekly_limit) * 100;
  },
  
  isOverWeeklyLimit: () => {
    const { profile, weeklyUsed } = get();
    if (!profile || profile.weekly_limit <= 0) return false;
    return weeklyUsed >= profile.weekly_limit;
  },
  
  isOnboardingDone: () => {
    const { user } = get();
    return !!user?.onboarding_done;
  }
}));
