'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { BarChart3, Crown, Flame, Globe2, History, Layers, Layers3, Star, TrendingUp, TrendingDown, LogOut, Settings, Wallet, User } from 'lucide-react';
import type { LeagueInfo } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';
import { getBankrollSummary, type BankrollSummary } from '@/lib/api/bankroll';

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
  const { user, logout, token } = useAuth();
  const { bankroll } = useUserStore();
  const [summary, setSummary] = useState<BankrollSummary | null>(null);
  const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : null;

  useEffect(() => {
    if (!user) return;
    getBankrollSummary(token).then(setSummary).catch(() => setSummary(null));
  }, [user, token]);

  const bankrollConfigured = summary?.configured !== false && summary != null;
  const sortedLeagues = [...leagues].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <aside className="bg-[#111114] border border-white/[0.06] rounded-xl sticky top-[80px] overflow-y-auto custom-scrollbar flex flex-col h-[calc(100vh-104px)]">
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
          <RailButton active={false} href="/dashboard/tendencias" icon={<TrendingUp className="w-3.5 h-3.5 text-emerald-400" />} label="Tendencias" />
          <RailButton active={false} href="/dashboard/estadisticas" icon={<BarChart3 className="w-3.5 h-3.5 text-sky-400" />} label="Estadísticas" />
          <RailButton active={false} href="/dashboard/historial" icon={<History className="w-3.5 h-3.5 text-zinc-300" />} label="Historial" />
          <RailButton active={false} href="/dashboard/parlays" icon={<Layers3 className="w-3.5 h-3.5 text-purple-300" />} label="Parlays" />
          <RailButton active={false} href="/dashboard/favoritos" icon={<Star className="w-3.5 h-3.5 text-amber-400" />} label="Favoritos" />
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
                icon={
                  lg.logo ? (
                    <img src={lg.logo} alt={lg.code} className="w-3.5 h-3.5 object-contain" />
                  ) : (
                    <span className="font-mono text-[9px] text-zinc-500">{lg.code}</span>
                  )
                }
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
            
            {bankrollConfigured && summary ? (
              <div className="mt-1 pt-2 border-t border-white/[0.06] space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-mono">Bankroll</span>
                    <span className="text-[13px] font-mono font-bold" style={{ color: summary.current_balance >= summary.initial_capital ? 'var(--color-success)' : 'var(--color-danger)' }}>
                      ${summary.current_balance.toLocaleString()}
                    </span>
                  </div>
                  <div className={`flex items-center gap-0.5 text-[10px] font-bold ${summary.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {summary.roi >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {summary.roi >= 0 ? '+' : ''}{summary.roi.toFixed(1)}%
                    <span className="ml-1 text-zinc-500">{summary.current_streak > 0 ? `🔥${summary.current_streak}G` : summary.current_streak < 0 ? `❄️${-summary.current_streak}P` : ''}</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-1 text-center">
                  <MiniStat label="Picks" value={`${summary.total_bets}`} />
                  <MiniStat label="Acierto" value={`${summary.win_rate.toFixed(0)}%`} />
                  <MiniStat label="Racha" value={`${summary.longest_win_streak}`} />
                </div>
              </div>
            ) : summary?.configured === false ? (
              <div className="mt-1 pt-2 border-t border-white/[0.06]">
                <Link href="/dashboard/bankroll" className="text-[11px] text-emerald-300 hover:text-emerald-200">Configura tu bankroll →</Link>
              </div>
            ) : bankroll ? (
              <div className="mt-1 pt-2 border-t border-white/[0.06] flex items-center justify-between">
                <span className="text-[13px] font-mono font-bold text-white">${bankroll.current_amount.toLocaleString()}</span>
              </div>
            ) : null}
          </div>
          
          <ul className="flex flex-col gap-0.5">
            <RailButton
              active={false}
              href="/dashboard/bankroll"
              icon={<Wallet className="w-3.5 h-3.5 text-emerald-400" />}
              label="Mi Bankroll completo"
            />
            <RailButton
              active={false}
              href="/dashboard/estadisticas"
              icon={<BarChart3 className="w-3.5 h-3.5 text-sky-400" />}
              label="Estadísticas"
            />
            <RailButton
              active={false}
              href="/dashboard/historial"
              icon={<History className="w-3.5 h-3.5 text-zinc-300" />}
              label="Historial de picks"
            />
            <RailButton
              active={false}
              href="/dashboard/configuracion"
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

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.03] py-1">
      <div className="text-[12px] font-mono font-bold text-white leading-none">{value}</div>
      <div className="text-[8px] uppercase tracking-wider text-zinc-500 mt-0.5">{label}</div>
    </div>
  );
}

function RailButton({
  active,
  onClick,
  href,
  icon,
  label,
  count,
  accent = 'neutral',
}: {
  active: boolean;
  onClick?: () => void;
  href?: string;
  icon?: React.ReactNode;
  label: string;
  count?: number;
  accent?: 'neutral' | 'amber';
}) {
  const activeClass =
    accent === 'amber' ? 'bg-amber-500/15 text-amber-300' : 'bg-white/10 text-white';

  const content = (
    <>
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
    </>
  );

  const className = `w-full flex items-center justify-between gap-2 px-2 h-[32px] rounded-md text-left transition-colors ${
    active ? activeClass : 'text-zinc-300 hover:bg-white/5 hover:text-white'
  }`;

  return (
    <li>
      {href ? (
        <Link href={href} className={className}>
          {content}
        </Link>
      ) : (
        <button type="button" onClick={onClick} className={className}>
          {content}
        </button>
      )}
    </li>
  );
}
