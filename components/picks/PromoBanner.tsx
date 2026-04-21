'use client';

import Link from 'next/link';
import { Lock, Sparkles, TrendingUp } from 'lucide-react';

import type { Pick } from '@/types';

interface PromoBannerProps {
  vipPicks: Pick[];
  userTier: 'free' | 'pro' | 'vip';
}

export default function PromoBanner({ vipPicks, userTier }: PromoBannerProps) {
  if (vipPicks.length === 0) return null;
  const locked = userTier === 'free';
  const top = vipPicks[0];

  return (
    <section className="relative overflow-hidden rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-white p-6 md:p-8">
      <div className="absolute -top-20 -right-20 w-56 h-56 rounded-full bg-amber-200/30 blur-3xl pointer-events-none" />
      <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="flex-1 min-w-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-[11px] font-mono font-bold uppercase tracking-widest mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            Pick VIP del día
          </div>
          <h3 className="font-sans font-bold text-[20px] md:text-[24px] text-slate-900 leading-tight mb-1">
            {locked ? 'Edge superior detectado' : `${top.homeTeam} vs ${top.awayTeam}`}
          </h3>
          <p className="font-sans text-[13px] text-slate-600">
            {locked
              ? `${vipPicks.length} pick${vipPicks.length === 1 ? '' : 's'} con EV superior al 15% bloqueado${vipPicks.length === 1 ? '' : 's'} detrás del tier VIP.`
              : `Confianza ${top.confidence}% · EV ${top.evPct != null ? `+${top.evPct.toFixed(1)}%` : '—'} · Stake ${top.suggestedStake.toFixed(1)}%`}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {locked ? (
            <>
              <div className="hidden md:flex items-center gap-2 text-[13px] text-slate-600 font-sans">
                <Lock className="w-4 h-4" />
                Requiere VIP
              </div>
              <Link
                href="/pricing"
                className="h-[44px] px-5 bg-amber-500 hover:bg-amber-600 text-white font-sans font-semibold text-[14px] rounded-full flex items-center gap-2 transition-colors"
              >
                Desbloquear
                <TrendingUp className="w-4 h-4" />
              </Link>
            </>
          ) : (
            <div className="flex items-center gap-2 text-emerald-600 font-mono text-[18px] font-bold">
              @{top.odds?.toFixed(2)}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
