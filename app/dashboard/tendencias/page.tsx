'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { getRecentPredictions, type PredictionRow } from '@/lib/api/predictions';

const CARD = 'rounded-xl border border-white/[0.06] bg-[#111114] p-5';
const LABEL = 'text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-500 mb-3';

export default function TendenciasPage() {
  const [rows, setRows] = useState<PredictionRow[] | null>(null);

  useEffect(() => {
    getRecentPredictions(30, 500).then((r) => setRows(r.predictions)).catch(() => setRows([]));
  }, []);

  const byLeague = useMemo(() => {
    const map: Record<string, { count: number; evSum: number }> = {};
    for (const p of rows ?? []) {
      const lg = p.league || 'Otros';
      map[lg] = map[lg] || { count: 0, evSum: 0 };
      map[lg].count += 1;
      map[lg].evSum += p.ev ?? 0;
    }
    return Object.entries(map)
      .map(([league, v]) => ({ league, count: v.count, avgEv: v.count ? v.evSum / v.count : 0 }))
      .sort((a, b) => b.count - a.count);
  }, [rows]);

  const topMarkets = useMemo(
    () => [...(rows ?? [])].filter((p) => p.ev != null).sort((a, b) => (b.ev ?? 0) - (a.ev ?? 0)).slice(0, 3),
    [rows],
  );

  if (rows === null) {
    return <div className="max-w-[1000px] mx-auto p-8"><div className="h-64 bg-white/[0.04] rounded-xl animate-pulse" /></div>;
  }

  return (
    <div className="max-w-[1000px] mx-auto px-4 md:px-6 lg:px-8 py-8 space-y-5">
      <div>
        <h1 className="font-sans text-2xl font-bold tracking-tight">Tendencias</h1>
        <p className="text-sm text-zinc-500">Últimos 30 días</p>
      </div>

      {rows.length === 0 ? (
        <div className={`${CARD} text-center text-sm text-zinc-400 py-12`}>
          Aún no hay suficientes picks para mostrar tendencias
        </div>
      ) : (
        <>
          <div className={CARD}>
            <div className={LABEL}>Picks por liga</div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byLeague} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="league" tick={{ fill: '#71717a', fontSize: 10 }} stroke="rgba(255,255,255,0.1)" interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fill: '#71717a', fontSize: 11 }} stroke="rgba(255,255,255,0.1)" width={32} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={CARD}>
            <div className={LABEL}>Top 3 mercados por EV</div>
            <div className="space-y-2">
              {topMarkets.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-zinc-300 truncate">
                    {p.home_team} vs {p.away_team} · <span className="text-zinc-500">{p.recommended_bet}</span>
                  </span>
                  <span className="font-mono font-bold" style={{ color: 'var(--color-success)' }}>
                    {(p.ev ?? 0) >= 0 ? '+' : ''}{((p.ev ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
