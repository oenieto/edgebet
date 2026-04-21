'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { apiFetch, ApiError } from '@/lib/api/client';
import { useUserStore } from '@/lib/store/userStore';

export interface User {
  id: number;
  email: string;
  name: string;
  tier: 'free' | 'pro' | 'vip';
  created_at: string;
  onboarding_done?: boolean;
}

interface AuthResponse {
  token: string;
  user: User;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, name: string) => Promise<User>;
  logout: () => void;
}

const TOKEN_KEY = 'edgebet.auth.token';
const USER_KEY = 'edgebet.auth.user';

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStorage<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function readToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  const loadUserState = useCallback(async (u: User, t: string) => {
    useUserStore.getState().setUser(u as any);
    try {
      const [profile, bankroll, alertsResp] = await Promise.all([
        apiFetch<any>(`/user/${u.id}/profile`, { token: t }),
        apiFetch<any>(`/user/${u.id}/bankroll`, { token: t }),
        apiFetch<any>(`/user/${u.id}/alerts`, { token: t }),
      ]);
      useUserStore.getState().setProfile(profile);
      useUserStore.getState().updateBankroll(bankroll);
      useUserStore.getState().updateAlerts(alertsResp.alerts || [], alertsResp.weekly_used || 0);
    } catch (err) {
      console.error('Failed to load user state', err);
    }
  }, []);

  useEffect(() => {
    const storedToken = readToken();
    const storedUser = readStorage<User>(USER_KEY);
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(storedUser);
      useUserStore.getState().setUser(storedUser as any);
      // Revalida contra el backend; si falla, limpia sesión
      apiFetch<User>('/auth/me', { token: storedToken })
        .then((fresh) => {
          setUser(fresh);
          window.localStorage.setItem(USER_KEY, JSON.stringify(fresh));
          loadUserState(fresh, storedToken);
        })
        .catch(() => {
          window.localStorage.removeItem(TOKEN_KEY);
          window.localStorage.removeItem(USER_KEY);
          setToken(null);
          setUser(null);
          useUserStore.getState().resetUser();
        });
    }
    setIsHydrated(true);
  }, [loadUserState]);

  const persist = useCallback((t: string, u: User) => {
    window.localStorage.setItem(TOKEN_KEY, t);
    window.localStorage.setItem(USER_KEY, JSON.stringify(u));
    setToken(t);
    setUser(u);
    loadUserState(u, t);
  }, [loadUserState]);

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    useUserStore.getState().resetUser();
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await apiFetch<AuthResponse>('/auth/login', {
        method: 'POST',
        body: { email, password },
      });
      persist(res.token, res.user);
      return res.user;
    },
    [persist],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const res = await apiFetch<AuthResponse>('/auth/register', {
        method: 'POST',
        body: { email, password, name },
      });
      persist(res.token, res.user);
      return res.user;
    },
    [persist],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: user !== null,
      isHydrated,
      login,
      register,
      logout,
    }),
    [user, token, isHydrated, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export { ApiError };
