'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Crown, Lock, Sparkles, TrendingUp } from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { getPicksToday } from '@/lib/api/picks';
import type { Pick } from '@/types';

export default function PromosPage() {
  const { user } = useAuth();
  const [picks, setPicks] = useState<Pick[] | null>(null);

  useEffect(() => {
    getPicksToday()
      .then(setPicks)
      .catch(() => setPicks([]));
  }, []);

  const vip = (picks ?? []).filter((p) => p.status === 'vip');
  const premium = (picks ?? []).filter((p) => p.status === 'premium');
  const userTier = user?.tier ?? 'free';
  const lockedVip = userTier !== 'vip';
  const lockedPremium = userTier === 'free';

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px] font-mono font-bold uppercase tracking-widest mb-3">
          <Sparkles className="w-3 h-3" />
          Promos del día
        </div>
        <h1 className="font-sans font-extrabold text-[28px] text-white tracking-tight">
          Los picks con mayor ventaja matemática
        </h1>
        <p className="font-sans text-[14px] text-zinc-400 mt-1">
          Filtrados por EV &gt; 8% — edges altos detectados entre nuestro modelo y el mercado.
        </p>
      </div>

      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Crown className="w-5 h-5 text-amber-300" />
            <h2 className="font-sans font-bold text-[17px] text-white">VIP — edge ≥ 8%</h2>
          </div>
          {lockedVip && (
            <Link
              href="/pricing"
              className="text-[12px] font-sans font-bold text-amber-300 hover:text-amber-200"
            >
              Desbloquear
            </Link>
          )}
        </div>
        {vip.length === 0 ? (
          <EmptyPromo label="No hay picks VIP abiertos ahora mismo." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {vip.map((p) => (
              <PromoRow key={p.id} pick={p} locked={lockedVip} tierBadge="vip" />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-zinc-200" />
          <h2 className="font-sans font-bold text-[17px] text-white">Premium — edge 5-8%</h2>
        </div>
        {premium.length === 0 ? (
          <EmptyPromo label="No hay picks premium abiertos ahora mismo." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {premium.map((p) => (
              <PromoRow key={p.id} pick={p} locked={lockedPremium} tierBadge="premium" />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PromoRow({
  pick,
  locked,
  tierBadge,
}: {
  pick: Pick;
  locked: boolean;
  tierBadge: 'premium' | 'vip';
}) {
  const badgeClass =
    tierBadge === 'vip'
      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
      : 'bg-white/10 text-zinc-100 border border-white/[0.08]';

  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider ${badgeClass}`}
        >
          {tierBadge.toUpperCase()}
        </span>
        <span className="font-sans text-[11px] text-zinc-500">{pick.league}</span>
      </div>

      <div className="font-sans font-bold text-[15px] text-white">
        {locked ? '••• vs •••' : `${pick.homeTeam} vs ${pick.awayTeam}`}
      </div>

      {locked ? (
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 text-zinc-400">
              <Lock className="w-4 h-4" />
              <span className="font-sans text-[12px]">
                Requiere {tierBadge === 'vip' ? 'VIP' : 'Pro'}
              </span>
            </div>
            <div className="mt-1 text-[11px] font-mono text-zinc-500">
              EV detectado:{' '}
              <span className="text-emerald-400 font-bold">+{pick.evPct?.toFixed(1)}%</span>
            </div>
          </div>
          <Link
            href="/pricing"
            className={`px-4 h-[36px] flex items-center rounded-md font-sans font-bold text-[12px] transition-colors ${
              tierBadge === 'vip'
                ? 'bg-amber-300 text-[#0a0a0c] hover:bg-amber-200'
                : 'bg-white text-[#0a0a0c] hover:bg-zinc-200'
            }`}
          >
            Desbloquear
          </Link>
        </div>
      ) : (
        <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
          <div className="flex flex-col">
            <span className="font-sans text-[10px] text-zinc-500">EV / Stake</span>
            <span className="font-mono font-bold text-[12.5px] text-emerald-400">
              +{pick.evPct?.toFixed(1)}% · {pick.suggestedStake.toFixed(1)}%
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="font-sans text-[10px] text-zinc-500">Cuota</span>
            <span className="font-mono font-bold text-[16px] text-white">
              @{pick.odds?.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyPromo({ label }: { label: string }) {
  return (
    <div className="bg-[#111114] border border-dashed border-white/[0.06] rounded-xl p-8 text-center">
      <p className="font-sans text-[13px] text-zinc-400">{label}</p>
    </div>
  );
}
