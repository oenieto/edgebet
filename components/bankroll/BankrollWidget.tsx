'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Flame, Snowflake, TrendingDown, TrendingUp, Wallet } from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { type BankrollSummary, getBankrollSummary } from '@/lib/api/bankroll';

/**
 * Widget compacto del bankroll persistido (sistema DB-backed). Distinto del
 * BankrollTracker store-based. Muestra balance/ROI/racha o un CTA si no hay
 * bankroll configurado.
 */
export default function BankrollWidget() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<BankrollSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getBankrollSummary(token)
      .then((s) => { if (!cancelled) setSummary(s); })
      .catch(() => { if (!cancelled) setSummary(null); })
      .finally(() => { if (!cancelled) setLoaded(true); });
    return () => { cancelled = true; };
  }, [token]);

  if (!loaded) {
    return <div className="h-[60px] rounded-xl border border-white/[0.06] bg-[#111114] animate-pulse" />;
  }

  // Sin bankroll configurado → CTA.
  if (!summary || summary.configured === false) {
    return (
      <div className="rounded-xl border border-white/[0.06] bg-gradient-to-br from-emerald-500/10 to-transparent p-4 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center">
            <Wallet className="w-4 h-4 text-emerald-300" />
          </div>
          <p className="text-sm text-zinc-300">
            Configura tu bankroll para rastrear el crecimiento de tus predicciones →
          </p>
        </div>
        <Link href="/dashboard/bankroll" className="shrink-0 h-9 px-4 rounded-md bg-white text-[#0a0a0c] text-sm font-semibold flex items-center">
          Comenzar
        </Link>
      </div>
    );
  }

  const s = summary;
  const up = s.current_balance >= s.initial_capital;
  const roiUp = s.roi >= 0;
  const streak = s.current_streak;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-4 flex items-center justify-between gap-4 flex-wrap">
      <div className="flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center">
            <Wallet className="w-4 h-4 text-zinc-300" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">Balance</div>
            <div className="font-mono font-bold text-lg" style={{ color: up ? 'var(--color-success)' : 'var(--color-danger)' }}>
              {new Intl.NumberFormat('es-ES', { style: 'currency', currency: s.currency, maximumFractionDigits: 2 }).format(s.current_balance)}
            </div>
          </div>
        </div>
        <Metric label="ROI">
          <span className="font-mono font-bold flex items-center gap-1" style={{ color: roiUp ? 'var(--color-success)' : 'var(--color-danger)' }}>
            {roiUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {roiUp ? '+' : ''}{s.roi.toFixed(1)}%
          </span>
        </Metric>
        <Metric label="Racha">
          <span className="font-mono font-bold flex items-center gap-1 text-zinc-100">
            {streak >= 3 && <Flame className="w-3.5 h-3.5 text-orange-400" />}
            {streak <= -3 && <Snowflake className="w-3.5 h-3.5 text-blue-300" />}
            {streak > 0 ? `${streak}W` : streak < 0 ? `${-streak}L` : '—'}
          </span>
        </Metric>
      </div>
      <Link href="/dashboard/bankroll" className="shrink-0 inline-flex items-center gap-1 text-sm font-semibold text-zinc-300 hover:text-white transition-colors">
        Ver detalle <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">{label}</div>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}
