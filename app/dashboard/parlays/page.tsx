'use client';

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Layers } from 'lucide-react';
import Link from 'next/link';
import ParlayBuilder from '@/components/parlays/ParlayBuilder';
import { getPicksToday } from '@/lib/api/picks';
import { useUserStore } from '@/lib/store/userStore';
import type { Pick } from '@/types';

export default function ParlaysPage() {
  const [picks, setPicks] = useState<Pick[]>([]);
  const [loading, setLoading] = useState(true);
  const { profile } = useUserStore();
  const bankroll = profile?.bankroll ?? 1000;

  useEffect(() => {
    getPicksToday()
      .then((data) => setPicks(data.filter((p) => p.status === 'free' || p.odds != null)))
      .catch(() => setPicks([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-6">
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
            Parlay Builder
          </h1>
          <p className="font-sans text-[13px] text-zinc-500">
            Arma tu parlay con picks del dia y calcula Kelly optimo
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : picks.length === 0 ? (
        <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-8 text-center">
          <p className="font-sans text-[14px] text-zinc-400">
            No hay picks disponibles para construir parlays. Vuelve cuando haya jornada activa.
          </p>
        </div>
      ) : (
        <ParlayBuilder availablePicks={picks} userBankroll={bankroll} />
      )}
    </div>
  );
}
