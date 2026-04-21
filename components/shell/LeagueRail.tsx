'use client';

import Link from 'next/link';
import { Crown, Flame, Globe2, Layers, Star, TrendingUp, TrendingDown, LogOut, Settings, Wallet, User } from 'lucide-react';
import type { LeagueInfo } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';

interface LeagueRailProps {
  leagues: LeagueInfo[];
  selected: string | null;
  onSelect: (slug: string | null) => void;
  counts?: Record<string, number>;
  topMetrics?: {
    vipCount?: number;
    premiumCount?: number;
    totalPicks?: number;
  };
}

export default function LeagueRail({
  leagues,
  selected,
  onSelect,
  counts,
  topMetrics,
}: LeagueRailProps) {
  const { user, logout } = useAuth();
  const { bankroll } = useUserStore();
  const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : null;
  const sortedLeagues = [...leagues].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <aside className="bg-[#111114] border border-white/[0.06] rounded-xl sticky top-[80px] overflow-y-auto scrollbar-hide flex flex-col h-[calc(100vh-104px)]">
      {/* Pick del día — top feature */}
      <Link
        href="/dashboard/pick-del-dia"
        className="block p-3 border-b border-white/[0.06] bg-gradient-to-br from-amber-500/10 to-transparent hover:from-amber-500/20 group transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-300 to-amber-500 flex items-center justify-center shadow-[0_0_14px_rgba(251,191,36,0.25)]">
            <Crown className="w-4 h-4 text-[#0a0a0c]" strokeWidth={2.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-sans text-[12px] font-bold text-amber-300 tracking-tight">
              Pick del día
            </div>
            <div className="font-mono text-[9px] uppercase tracking-widest text-amber-500/70">
              Exclusivo · VIP
            </div>
          </div>
          <span className="font-mono text-[10px] text-amber-300 group-hover:translate-x-0.5 transition-transform">
            →
          </span>
        </div>
      </Link>

      {/* Populares */}
      <div className="p-3">
        <div className="px-2 pb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] font-sans font-bold text-zinc-500">
          <Flame className="w-3 h-3" />
          Populares
        </div>
        <ul className="flex flex-col gap-0.5">
          <RailButton
            active={selected === null}
            onClick={() => onSelect(null)}
            icon={<Globe2 className="w-3.5 h-3.5" />}
            label="Todos los picks"
            count={total ?? undefined}
          />
          {topMetrics?.vipCount != null && topMetrics.vipCount > 0 && (
            <RailButton
              active={false}
              onClick={() => onSelect(null)}
              icon={<Crown className="w-3.5 h-3.5 text-amber-400" />}
              label="VIP (edge ≥ 8%)"
              count={topMetrics.vipCount}
              accent="amber"
            />
          )}
          {topMetrics?.premiumCount != null && topMetrics.premiumCount > 0 && (
            <RailButton
              active={false}
              onClick={() => onSelect(null)}
              icon={<Star className="w-3.5 h-3.5 text-zinc-300" />}
              label="Premium (5-8%)"
              count={topMetrics.premiumCount}
            />
          )}
          <RailButton
            active={false}
            onClick={() => onSelect(null)}
            icon={<TrendingUp className="w-3.5 h-3.5 text-emerald-400" />}
            label="Mayor EV"
          />
        </ul>
      </div>

      {/* A-Z ligas */}
      <div className="p-3 border-t border-white/[0.06]">
        <div className="px-2 pb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] font-sans font-bold text-zinc-500">
          <Layers className="w-3 h-3" />
          Ligas A-Z
        </div>
        <ul className="flex flex-col gap-0.5">
          {sortedLeagues.map((lg) => {
            const active = selected === lg.slug;
            const count = counts?.[lg.slug];
            return (
              <RailButton
                key={lg.slug}
                active={active}
                onClick={() => onSelect(lg.slug)}
                label={lg.name}
                count={count}
                icon={<span className="font-mono text-[9px] text-zinc-500">{lg.code}</span>}
              />
            );
          })}
        </ul>
      </div>

      {/* Account Control */}
      {user && (
        <div className="p-3 border-t border-white/[0.06] mt-auto">
          <div className="px-2 pb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] font-sans font-bold text-zinc-500">
            <User className="w-3 h-3" />
            Mi Cuenta
          </div>
          
          <div className="flex flex-col gap-2 px-2 py-2 mb-2 rounded-md bg-white/[0.02] border border-white/[0.04]">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white text-[#0a0a0c] flex items-center justify-center font-mono text-[12px] font-bold shrink-0">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col flex-1 min-w-0">
                <span className="font-sans text-[12.5px] font-semibold text-white truncate">
                  {user.name}
                </span>
                <span
                  className={`font-mono text-[9px] uppercase tracking-widest ${
                    user.tier === 'vip'
                      ? 'text-amber-300'
                      : user.tier === 'pro'
                        ? 'text-white'
                        : 'text-zinc-500'
                  }`}
                >
                  Plan {user.tier}
                </span>
              </div>
            </div>
            
            {bankroll && (
              <div className="mt-1 pt-2 border-t border-white/[0.06] flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-mono">Bankroll</span>
                  <span className="text-[13px] font-mono font-bold text-white">${bankroll.current_amount.toLocaleString()}</span>
                </div>
                {bankroll.pnl_pct !== 0 && (
                  <div className={`flex items-center gap-0.5 text-[10px] font-bold ${bankroll.pnl_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {bankroll.pnl_pct > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {bankroll.pnl_pct > 0 ? '+' : ''}{bankroll.pnl_pct.toFixed(1)}%
                  </div>
                )}
              </div>
            )}
          </div>
          
          <ul className="flex flex-col gap-0.5">
            <RailButton
              active={false}
              onClick={() => {}}
              icon={<Wallet className="w-3.5 h-3.5 text-emerald-400" />}
              label="Gestión de Bank"
            />
            <RailButton
              active={false}
              onClick={() => {}}
              icon={<Settings className="w-3.5 h-3.5 text-zinc-400" />}
              label="Configuración"
            />
            <RailButton
              active={false}
              onClick={logout}
              icon={<LogOut className="w-3.5 h-3.5 text-red-400" />}
              label="Cerrar sesión"
            />
          </ul>
        </div>
      )}
    </aside>
  );
}

function RailButton({
  active,
  onClick,
  icon,
  label,
  count,
  accent = 'neutral',
}: {
  active: boolean;
  onClick: () => void;
  icon?: React.ReactNode;
  label: string;
  count?: number;
  accent?: 'neutral' | 'amber';
}) {
  const activeClass =
    accent === 'amber' ? 'bg-amber-500/15 text-amber-300' : 'bg-white/10 text-white';

  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`w-full flex items-center justify-between gap-2 px-2 h-[32px] rounded-md text-left transition-colors ${
          active ? activeClass : 'text-zinc-300 hover:bg-white/5 hover:text-white'
        }`}
      >
        <span className="flex items-center gap-2 font-sans text-[12.5px] font-medium truncate">
          {icon}
          <span className="truncate">{label}</span>
        </span>
        {count != null && (
          <span
            className={`font-mono text-[10px] shrink-0 px-1.5 py-0.5 rounded ${
              active ? 'bg-white/10' : 'bg-white/5 text-zinc-500'
            }`}
          >
            {count}
          </span>
        )}
      </button>
    </li>
  );
}
