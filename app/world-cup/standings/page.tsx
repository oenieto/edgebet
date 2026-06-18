'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, Trophy, Clock } from 'lucide-react';
import { getWCStandings, type WCStandingRow } from '@/lib/api/worldcup';

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function WcStandingsPage() {
  const [standings, setStandings] = useState<Record<string, WCStandingRow[]>>({});
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshCountdown, setRefreshCountdown] = useState(60);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getWCStandings()
      .then((res) => {
        setStandings(res.groups);
        setLastUpdated(res.last_updated);
        setRefreshCountdown(60);
      })
      .catch((err) => {
        console.error('Error fetching WC standings:', err);
        setError('No se pudieron cargar las tablas del Mundial.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-refresh countdown & trigger every 60s
  useEffect(() => {
    const timer = setInterval(() => {
      setRefreshCountdown((prev) => {
        if (prev <= 1) {
          load();
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [load]);

  const groupKeys = Object.keys(standings).sort();

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-zinc-100 pb-12">
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <Link
              href="/world-cup"
              className="inline-flex items-center gap-1.5 text-xs text-[#C8A951] hover:text-[#e4c973] mb-2 transition-colors font-semibold"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Volver a Grupos
            </Link>
            <h1 className="font-sans text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
              <Trophy className="w-7 h-7 text-[#C8A951]" />
              Tablas de Posiciones — Mundial 2026
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Clasificaciones completas de los 12 grupos. Se actualizan automáticamente después de cada partido finalizado.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500 flex items-center gap-1 font-mono">
              <Clock className="w-3.5 h-3.5 text-zinc-600" /> Auto-refresco en: {refreshCountdown}s
            </span>
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-2 h-[38px] px-4 rounded-md bg-white/5 border border-white/[0.08] text-zinc-200 hover:bg-white/10 hover:text-white text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Actualizar
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-3 flex flex-wrap gap-4 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-emerald-500/20 border border-emerald-500/40 inline-block" />
            <span className="text-zinc-300">1° y 2°: Clasificado directo</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-amber-500/20 border border-amber-500/40 inline-block" />
            <span className="text-zinc-300">3°: Repesca / Posible clasificación</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-rose-500/20 border border-rose-500/40 inline-block" />
            <span className="text-zinc-300">4°: Eliminado</span>
          </span>
          {lastUpdated && (
            <span className="text-zinc-500 ml-auto font-mono text-[11px] self-center">
              Última actualización: {fmtDate(lastUpdated)}
            </span>
          )}
        </div>

        {/* Standings Grid */}
        {loading && groupKeys.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, idx) => (
              <div key={idx} className="h-56 bg-[#111114] border border-white/[0.06] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-8 text-center space-y-4">
            <p className="text-sm text-zinc-400">{error}</p>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 h-[38px] px-4 rounded-md bg-white/10 border border-white/[0.08] text-white text-sm font-semibold hover:bg-white/15 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Reintentar
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {groupKeys.map((letter) => {
              const rows = standings[letter] || [];
              return (
                <div
                  key={letter}
                  className="bg-[#111114] border border-white/[0.06] rounded-xl overflow-hidden hover:border-white/10 transition-all duration-200"
                >
                  {/* Group Title */}
                  <div className="bg-[#1a1a2e]/50 border-b border-white/[0.06] px-4 py-2.5 flex items-center justify-between">
                    <span className="font-bold text-sm text-[#C8A951] uppercase tracking-wider">
                      Grupo {letter}
                    </span>
                  </div>

                  {/* Standings Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-white/[0.04] text-left text-zinc-500 font-bold uppercase text-[9px] tracking-wider bg-white/[0.01]">
                          <th className="py-2.5 px-3 text-center w-8">#</th>
                          <th className="py-2.5 px-3">Equipo</th>
                          <th className="py-2.5 px-2 text-center w-8">PJ</th>
                          <th className="py-2.5 px-2 text-center w-8">DG</th>
                          <th className="py-2.5 px-3 text-center w-10 font-bold text-white">Pts</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, idx) => {
                          const isTop2 = idx < 2;
                          const is3rd = idx === 2;
                          const is4th = idx === 3;
                          
                          let rowClass = 'hover:bg-white/[0.01]';
                          let posClass = 'text-zinc-500';
                          if (isTop2) {
                            rowClass += ' bg-emerald-500/[0.02]';
                            posClass = 'text-emerald-400 font-bold';
                          } else if (is3rd) {
                            rowClass += ' bg-amber-500/[0.01]';
                            posClass = 'text-amber-400';
                          } else if (is4th) {
                            rowClass += ' bg-rose-500/[0.01]';
                            posClass = 'text-rose-500';
                          }

                          return (
                            <tr
                              key={row.team}
                              className={`border-b border-white/[0.04] last:border-0 ${rowClass}`}
                            >
                              {/* Position */}
                              <td className={`py-2.5 px-3 text-center font-mono ${posClass}`}>
                                {idx + 1}
                              </td>

                              {/* Flag + Name */}
                              <td className="py-2.5 px-3">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-base leading-none shrink-0">{row.flag}</span>
                                  <span className="font-semibold text-zinc-200 truncate max-w-[120px]" title={row.team}>
                                    {row.team}
                                  </span>
                                </div>
                              </td>

                              {/* Matches played */}
                              <td className="py-2.5 px-2 text-center font-mono text-zinc-400">
                                {row.played}
                              </td>

                              {/* Goal Diff */}
                              <td className={`py-2.5 px-2 text-center font-mono font-medium ${
                                row.goal_difference > 0 ? 'text-emerald-500' : row.goal_difference < 0 ? 'text-rose-500' : 'text-zinc-600'
                              }`}>
                                {row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}
                              </td>

                              {/* Points */}
                              <td className="py-2.5 px-3 text-center font-mono font-bold text-white bg-white/[0.02]">
                                {row.points}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
