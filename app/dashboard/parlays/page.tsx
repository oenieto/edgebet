'use client';

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Layers, Lock, Sparkles } from 'lucide-react';
import Link from 'next/link';
import ParlayGenerator from '@/components/parlays/ParlayGenerator';
import { getPicksToday } from '@/lib/api/picks';
import { useUserStore } from '@/lib/store/userStore';
import type { Pick } from '@/types';

const PAID_TIERS = new Set(['pro', 'vip']);

export default function ParlaysPage() {
  const [picks, setPicks] = useState<Pick[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useUserStore();

  const tier = (user?.tier ?? 'free').toLowerCase();
  const hasAccess = PAID_TIERS.has(tier);

  useEffect(() => {
    if (!hasAccess) {
      setLoading(false);
      return;
    }
    getPicksToday()
      .then((data) => setPicks(data.filter((p) => p.odds != null)))
      .catch(() => setPicks([]))
      .finally(() => setLoading(false));
  }, [hasAccess]);

  return (
    <div className="max-w-[1100px] mx-auto px-4 md:px-6 lg:px-8 py-6">
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-zinc-400 hover:text-white font-sans text-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </Link>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center">
          <Layers className="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <h1 className="font-sans font-bold text-[22px] text-white tracking-tight">
            Parlays con IA
          </h1>
          <p className="font-sans text-[13px] text-zinc-500">
            Elige el nivel de riesgo y el momio objetivo. La IA arma el parlay con picks ya analizados.
          </p>
        </div>
      </div>

      {!hasAccess ? (
        <LockedTeaser />
      ) : loading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : picks.length < 2 ? (
        <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-8 text-center">
          <p className="font-sans text-[14px] text-zinc-400">
            No hay picks suficientes para generar parlays. Vuelve cuando haya jornada activa.
          </p>
        </div>
      ) : (
        <ParlayGenerator availablePicks={picks} />
      )}
    </div>
  );
}

function LockedTeaser() {
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-8 text-center max-w-[640px] mx-auto">
      <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center mb-4">
        <Lock className="w-6 h-6 text-indigo-400" />
      </div>
      <h2 className="font-sans text-[20px] font-bold text-white mb-2">
        Parlays con IA — Pro / VIP
      </h2>
      <p className="font-sans text-[14px] text-zinc-400 leading-relaxed mb-6">
        La IA arma parlays a partir de los picks ya analizados por el motor de 3 capas. Tú eliges el nivel de riesgo y el momio objetivo; el sistema hace el resto.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-6 text-left">
        {[
          { label: 'Seguro', range: '1.10 – 1.30' },
          { label: 'Moderado', range: '1.30 – 1.60' },
          { label: 'Arriesgado', range: '1.60 – 2.00' },
          { label: 'Muy arriesgado', range: '2.00+' },
        ].map((p) => (
          <div
            key={p.label}
            className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3 flex items-center justify-between"
          >
            <span className="font-sans text-[13px] text-zinc-300">{p.label}</span>
            <span className="font-mono text-[12px] text-zinc-500">{p.range}</span>
          </div>
        ))}
      </div>

      <Link
        href="/pricing"
        className="inline-flex items-center gap-2 h-[44px] px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-sans text-[14px] font-bold transition-colors"
      >
        <Sparkles className="w-4 h-4" />
        Desbloquear con Pro
      </Link>
    </div>
  );
}
