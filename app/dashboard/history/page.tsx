'use client';

import { Clock, TrendingUp } from 'lucide-react';
import Link from 'next/link';

export default function HistoryPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="font-sans font-extrabold text-[28px] text-white tracking-tight">
          Historial
        </h1>
        <p className="font-sans text-[14px] text-zinc-400 mt-1">
          Registro de picks pasados con resultado y ROI acumulado.
        </p>
      </div>

      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-10 text-center">
        <div className="w-14 h-14 rounded-full bg-white/5 border border-white/[0.08] text-zinc-200 flex items-center justify-center mx-auto mb-4">
          <Clock className="w-6 h-6" />
        </div>
        <h2 className="font-sans font-bold text-[18px] text-white mb-2">
          Historial en construcción
        </h2>
        <p className="font-sans text-[13px] text-zinc-400 max-w-md mx-auto mb-6">
          Estamos conectando la base de datos de resultados. Cuando confirmemos un pick que
          seguiste, aparecerá aquí con PnL y ROI acumulado.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-5 h-[44px] bg-white text-[#0a0a0c] rounded-full font-sans font-bold text-[14px] hover:bg-zinc-200 transition-colors"
        >
          <TrendingUp className="w-4 h-4" />
          Ver picks de hoy
        </Link>
      </div>
    </div>
  );
}
