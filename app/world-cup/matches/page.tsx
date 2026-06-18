'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, Filter, RefreshCw, Trophy, AlertCircle } from 'lucide-react';
import { getWCFixtures, type WCFixture } from '@/lib/api/worldcup';

const GROUPS = ['Todos', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'];
const DATE_FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'today', label: 'Hoy' },
  { value: 'upcoming', label: 'Próximos' },
  { value: 'finished', label: 'Finalizados' },
];

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-ES', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

function FormIndicator({ form }: { form: Array<'W' | 'D' | 'L'> }) {
  if (!form || form.length === 0) return <span className="text-zinc-600">—</span>;
  return (
    <div className="flex gap-0.5">
      {form.map((r, idx) => {
        const bg = r === 'W' ? 'bg-[#2ec4b6]' : r === 'D' ? 'bg-[#ff9f1c]' : 'bg-[#e71d36]';
        return (
          <span
            key={idx}
            className={`w-4 h-4 rounded-sm text-white text-[9px] font-bold inline-flex items-center justify-center`}
            style={{ backgroundColor: r === 'W' ? 'var(--color-success)' : r === 'D' ? 'var(--color-warning)' : 'var(--color-danger)' }}
          >
            {r}
          </span>
        );
      })}
    </div>
  );
}

export default function WcMatchesPage() {
  const [fixtures, setFixtures] = useState<WCFixture[]>([]);
  const [filteredFixtures, setFilteredFixtures] = useState<WCFixture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [dateFilter, setDateFilter] = useState('all');
  const [groupFilter, setGroupFilter] = useState('Todos');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getWCFixtures()
      .then((res) => {
        setFixtures(res.fixtures);
      })
      .catch((err) => {
        console.error('Error fetching fixtures:', err);
        setError('No se pudieron cargar los partidos del Mundial. Inténtalo de nuevo más tarde.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let result = [...fixtures];

    // Filter by Date
    const now = new Date();
    if (dateFilter === 'today') {
      result = result.filter((f) => {
        const d = new Date(f.match_date);
        return d.toDateString() === now.toDateString();
      });
    } else if (dateFilter === 'upcoming') {
      result = result.filter((f) => {
        return f.status === 'scheduled' || new Date(f.match_date) >= now;
      });
    } else if (dateFilter === 'finished') {
      result = result.filter((f) => f.status === 'finished');
    }

    // Filter by Group
    if (groupFilter !== 'Todos') {
      result = result.filter((f) => f.match_group === groupFilter.toUpperCase());
    }

    setFilteredFixtures(result);
  }, [fixtures, dateFilter, groupFilter]);

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
              Calendario y Partidos del Mundial
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Resultados en tiempo real, predicciones esperadas ELO/Poisson y probabilidades estimadas.
            </p>
          </div>
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

        {/* Filters Panel */}
        <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Date tabs */}
          <div className="flex gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
            {DATE_FILTERS.map((f) => {
              const active = dateFilter === f.value;
              return (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setDateFilter(f.value)}
                  className={`shrink-0 px-4 h-[34px] rounded-md text-xs font-bold transition-colors border ${
                    active
                      ? 'bg-[#C8A951] text-[#1A1A2E] border-[#C8A951]'
                      : 'bg-white/5 text-zinc-300 border-white/[0.08] hover:bg-white/10'
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          {/* Group dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-zinc-400 flex items-center gap-1 shrink-0">
              <Filter className="w-3.5 h-3.5 text-[#C8A951]" /> Filtrar Grupo:
            </span>
            <div className="flex gap-1 overflow-x-auto scrollbar-none max-w-full md:max-w-md pb-1 md:pb-0">
              {GROUPS.map((g) => {
                const active = groupFilter === g;
                return (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGroupFilter(g)}
                    className={`shrink-0 px-3 h-[30px] rounded-md text-xs font-semibold transition-colors border ${
                      active
                        ? 'bg-white text-black border-white'
                        : 'bg-white/5 text-zinc-300 border-white/[0.08] hover:bg-white/10'
                    }`}
                  >
                    {g}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Fixtures List */}
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-32 bg-[#111114] border border-white/[0.06] rounded-xl animate-pulse" />
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
        ) : filteredFixtures.length === 0 ? (
          <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-12 text-center text-zinc-400">
            <AlertCircle className="w-10 h-10 mx-auto text-zinc-600 mb-3" />
            <p className="text-sm">No se encontraron partidos para los filtros seleccionados.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredFixtures.map((f) => {
              const isLive = f.status === 'live' || f.status === 'in_progress';
              const isFinished = f.status === 'finished';
              
              return (
                <div
                  key={f.id}
                  className={`bg-[#111114] border rounded-xl p-4 transition-all duration-200 hover:border-white/10 relative overflow-hidden flex flex-col justify-between ${
                    isLive ? 'border-[#E63946]/50 shadow-[0_0_15px_rgba(230,57,70,0.15)]' : 'border-white/[0.06]'
                  }`}
                >
                  {/* Card Top Header */}
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 bg-white/5 px-2 py-0.5 rounded">
                      {f.tournament_phase === 'group' ? `Grupo ${f.match_group}` : f.tournament_phase}
                    </span>
                    
                    {isLive ? (
                      <span className="flex items-center gap-1 bg-[#E63946]/10 border border-[#E63946]/30 px-2 py-0.5 rounded text-[#E63946] text-[10px] font-bold">
                        <span className="relative inline-flex w-1.5 h-1.5">
                          <span className="absolute inline-flex w-full h-full rounded-full bg-[#E63946] opacity-75 animate-ping" />
                          <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-[#E63946]" />
                        </span>
                        EN VIVO
                      </span>
                    ) : isFinished ? (
                      <span className="text-[10px] font-semibold text-zinc-500 uppercase">
                        Finalizado
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold text-zinc-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-[#C8A951]" /> {fmtDate(f.match_date)}
                      </span>
                    )}
                  </div>

                  {/* Teams Score Area */}
                  <div className="flex items-center justify-between gap-4 py-2 border-b border-white/[0.04] mb-3">
                    {/* Home Team */}
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-2xl leading-none shrink-0">{f.home_flag}</span>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-zinc-100 truncate">{f.home_team}</p>
                        <div className="mt-1"><FormIndicator form={f.home_form} /></div>
                      </div>
                    </div>

                    {/* Score display */}
                    <div className="flex items-center gap-3 shrink-0 px-2 py-1 bg-white/5 rounded-lg border border-white/[0.06]">
                      {isFinished || isLive ? (
                        <div className="flex items-center gap-2 text-lg font-black font-mono">
                          <span className="text-white">{f.home_goals ?? 0}</span>
                          <span className="text-zinc-600">:</span>
                          <span className="text-white">{f.away_goals ?? 0}</span>
                        </div>
                      ) : (
                        <span className="text-xs font-bold text-zinc-500 uppercase px-1">VS</span>
                      )}
                    </div>

                    {/* Away Team */}
                    <div className="flex items-center gap-2 flex-1 min-w-0 flex-row-reverse text-right">
                      <span className="text-2xl leading-none shrink-0">{f.away_flag}</span>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-zinc-100 truncate">{f.away_team}</p>
                        <div className="mt-1 flex justify-end"><FormIndicator form={f.away_form} /></div>
                      </div>
                    </div>
                  </div>

                  {/* Expected Score / Predictions Details */}
                  <div className="space-y-2 mt-1">
                    <div className="flex justify-between items-center bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
                      <span className="text-xs text-zinc-400">Resultado esperado:</span>
                      <span className="text-xs font-bold text-[#C8A951] bg-[#C8A951]/10 px-2 py-0.5 rounded font-mono border border-[#C8A951]/20">
                        {f.predicted_most_likely_score}
                      </span>
                    </div>

                    {/* Probs chart */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] font-semibold text-zinc-400">
                        <span>L: {(f.prob_home * 100).toFixed(0)}%</span>
                        <span>E: {(f.prob_draw * 100).toFixed(0)}%</span>
                        <span>V: {(f.prob_away * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden flex bg-zinc-800">
                        <div className="h-full bg-emerald-500" style={{ width: `${f.prob_home * 100}%` }} title="Local" />
                        <div className="h-full bg-amber-500" style={{ width: `${f.prob_draw * 100}%` }} title="Empate" />
                        <div className="h-full bg-rose-500" style={{ width: `${f.prob_away * 100}%` }} title="Visitante" />
                      </div>
                    </div>

                    {/* Odds */}
                    {(f.best_odds_home || f.best_odds_draw || f.best_odds_away) && (
                      <div className="flex gap-2 pt-2 border-t border-white/[0.04] justify-between text-xs">
                        <span className="text-zinc-500 text-[10px] uppercase font-bold self-center">Cuotas:</span>
                        <div className="flex gap-1.5">
                          <span className="bg-[#1a1a2e] border border-[#C8A951]/20 rounded px-2 py-0.5 text-zinc-300 font-mono text-[11px]">
                            1: <strong className="text-white font-bold">{f.best_odds_home?.toFixed(2) ?? '—'}</strong>
                          </span>
                          <span className="bg-[#1a1a2e] border border-[#C8A951]/20 rounded px-2 py-0.5 text-zinc-300 font-mono text-[11px]">
                            X: <strong className="text-white font-bold">{f.best_odds_draw?.toFixed(2) ?? '—'}</strong>
                          </span>
                          <span className="bg-[#1a1a2e] border border-[#C8A951]/20 rounded px-2 py-0.5 text-zinc-300 font-mono text-[11px]">
                            2: <strong className="text-white font-bold">{f.best_odds_away?.toFixed(2) ?? '—'}</strong>
                          </span>
                        </div>
                      </div>
                    )}
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
