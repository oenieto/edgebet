'use client';

import { useUserStore } from '@/lib/store/userStore';
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

export default function BankrollTracker() {
  const { profile, bankroll, weeklyUsed, weeklyUsedPct, isOverWeeklyLimit } = useUserStore();

  if (!profile || !bankroll) {
    return null;
  }

  const { current_amount, initial_amount, pnl_pct, sparkline_data } = bankroll;
  const isPositive = pnl_pct >= 0;
  const usedPct = weeklyUsedPct();

  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5 relative overflow-hidden">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center">
            <Wallet className="w-4 h-4 text-zinc-300" />
          </div>
          <span className="font-sans text-sm font-semibold text-white">Mi Bankroll</span>
        </div>
        <div
          className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-bold ${
            isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
          }`}
        >
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {isPositive ? '+' : ''}{pnl_pct.toFixed(1)}%
        </div>
      </div>

      <div className="mb-6">
        <div className="text-4xl font-mono font-bold text-white tracking-tight">
          ${current_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          Inicio del mes: ${initial_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      {sparkline_data && sparkline_data.length > 0 && (
        <div className="h-16 w-full mb-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkline_data}>
              <YAxis domain={['auto', 'auto']} hide />
              <Line
                type="monotone"
                dataKey="amount"
                stroke={isPositive ? '#10b981' : '#ef4444'}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="border-t border-white/[0.06] pt-4">
        <div className="flex justify-between text-xs mb-2">
          <span className="text-zinc-400">Riesgo semanal (Límite: ${profile.weekly_limit.toFixed(0)})</span>
          <span className={`font-mono font-bold ${isOverWeeklyLimit() ? 'text-red-400' : 'text-white'}`}>
            ${weeklyUsed.toFixed(0)} <span className="text-zinc-500">/ {usedPct.toFixed(0)}%</span>
          </span>
        </div>
        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              usedPct > 90 ? 'bg-red-500' : usedPct > 70 ? 'bg-amber-500' : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(usedPct, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
