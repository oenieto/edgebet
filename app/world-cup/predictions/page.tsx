'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, Trophy, AlertTriangle, Zap, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { getWCPredictions, type WCPrediction } from '@/lib/api/worldcup';

const FLAG_MAP: Record<string, string> = {
  "Mexico": "🇲🇽", "Croatia": "🇭🇷", "Ecuador": "🇪🇨", "Saudi Arabia": "🇸🇦",
  "Canada": "🇨🇦", "Belgium": "🇧🇪", "Morocco": "🇲🇦", "Qatar": "🇶🇦",
  "USA": "🇺🇸", "Switzerland": "🇨🇭", "Uruguay": "🇺🇾", "South Korea": "🇰🇷",
  "Argentina": "🇦🇷", "Norway": "🇳🇴", "Tunisia": "🇹🇳", "Australia": "🇦🇺",
  "France": "🇫🇷", "Senegal": "🇸🇳", "Japan": "🇯🇵", "Paraguay": "🇵🇾",
  "Spain": "🇪🇸", "Egypt": "🇪🇬", "Iran": "🇮🇷", "Costa Rica": "🇨🇷",
  "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Colombia": "🇨🇴", "Ivory Coast": "🇨🇮", "New Zealand": "🇳🇿",
  "Brazil": "🇧🇷", "Netherlands": "🇳🇱", "Algeria": "🇩🇿", "Jordan": "🇯🇴",
  "Portugal": "🇵🇹", "Nigeria": "🇳🇬", "Panama": "🇵🇦", "Uzbekistan": "🇺🇿",
  "Germany": "🇩🇪", "Poland": "🇵🇱", "Ghana": "🇬🇭", "Venezuela": "🇻🇪",
  "Italy": "🇮🇹", "Serbia": "🇷🇸", "Cameroon": "🇨🇲", "Iraq": "🇮🇶",
  "Denmark": "🇩🇰", "Ukraine": "🇺🇦", "South Africa": "🇿🇦", "Curacao": "🇨🇼"
};

function getFlag(teamName: string): string {
  return FLAG_MAP[teamName] || "⚽";
}

function FormIndicator({ form }: { form: Array<'W' | 'D' | 'L'> }) {
  if (!form || form.length === 0) return <span className="text-zinc-600">—</span>;
  return (
    <div className="flex gap-0.5 inline-flex">
      {form.map((r, idx) => {
        let bg = 'bg-zinc-700';
        if (r === 'W') bg = 'bg-emerald-500';
        else if (r === 'D') bg = 'bg-amber-500';
        else if (r === 'L') bg = 'bg-rose-500';
        return (
          <span
            key={idx}
            className={`w-4 h-4 rounded-sm text-white text-[9px] font-bold inline-flex items-center justify-center ${bg}`}
          >
            {r}
          </span>
        );
      })}
    </div>
  );
}

export default function WcPredictionsPage() {
  const [predictions, setPredictions] = useState<WCPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getWCPredictions()
      .then((data) => {
        // Sort by EV% descending
        const sorted = [...data].sort((a, b) => (b.evPct || 0) - (a.evPct || 0));
        setPredictions(sorted);
      })
      .catch((err) => {
        console.error('Error fetching WC predictions:', err);
        setError('No se pudieron cargar las predicciones del Mundial. Asegúrate de que el backend está corriendo.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
              Predicciones de Valor (EV+)
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Selecciones sugeridas por el motor ELO/Poisson ordenadas por valor esperado (EV%).
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

        {/* Info Banner */}
        <div className="rounded-xl border border-[#C8A951]/20 bg-[#1A1A2E]/60 p-4 text-sm leading-snug flex items-start gap-3">
          <Zap className="w-5 h-5 text-[#C8A951] shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-[#C8A951] mb-1">Modelo de Predicción Blended</p>
            <p className="text-zinc-300 text-xs">
              Mundial 2026 utiliza una ponderación de 65% Poisson Histórico/ELO y 35% cuotas implícitas de casas de apuestas. 
              Para proteger tu bankroll, el valor esperado (EV%) está limitado visualmente a un máximo de 60%.
            </p>
          </div>
        </div>

        {/* Predictions List */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-64 bg-[#111114] border border-white/[0.06] rounded-xl animate-pulse" />
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
        ) : predictions.length === 0 ? (
          <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-12 text-center text-zinc-400">
            <p className="text-sm">No hay predicciones generadas para hoy.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {predictions.map((p) => {
              const ev = p.evPct ?? 0;
              const evCapped = p.ev_capped;
              const evRaw = p.ev_raw ?? ev;

              // Build chart data
              const chartData = [
                { name: 'Local', value: Math.round((p.mlProb?.home ?? 0.33) * 100) },
                { name: 'Empate', value: Math.round((p.mlProb?.draw ?? 0.34) * 100) },
                { name: 'Visita', value: Math.round((p.mlProb?.away ?? 0.33) * 100) },
              ];

              return (
                <div
                  key={p.id}
                  className="bg-[#111114] border border-white/[0.06] rounded-xl p-5 flex flex-col justify-between hover:border-white/10 transition-all duration-200"
                >
                  <div>
                    {/* Header */}
                    <div className="flex justify-between items-start gap-4 mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xl">{getFlag(p.homeTeam)}</span>
                          <span className="font-bold text-zinc-200 text-sm md:text-base">{p.homeTeam}</span>
                          <span className="text-zinc-500 font-mono text-xs">vs</span>
                          <span className="text-xl">{getFlag(p.awayTeam)}</span>
                          <span className="font-bold text-zinc-200 text-sm md:text-base">{p.awayTeam}</span>
                        </div>
                        <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">
                          {p.market} · FIFA World Cup 2026
                        </p>
                      </div>

                      {/* EV Circle Badge */}
                      <div className="text-right shrink-0">
                        <div className={`px-3 py-1.5 rounded-lg border font-mono flex flex-col items-center justify-center ${
                          ev >= 20 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-[#C8A951]/10 border-[#C8A951]/30 text-[#C8A951]'
                        }`}>
                          <span className="text-xs uppercase font-bold tracking-wider opacity-85 leading-none mb-1">EV+</span>
                          <span className="text-base font-black leading-none">{ev.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* EV Cap warning banner if capped */}
                    {evCapped && (
                      <div className="mb-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 flex items-center gap-2 text-amber-300 text-xs">
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                        <span>
                          <strong>Cuota atípica:</strong> Limitado a 60.0% (EV Real: {evRaw.toFixed(1)}%)
                        </span>
                      </div>
                    )}

                    {/* Details row */}
                    <div className="grid grid-cols-2 gap-4 bg-white/[0.02] border border-white/[0.04] rounded-lg p-3 mb-4">
                      <div>
                        <span className="text-[10px] text-zinc-500 uppercase font-bold block mb-1">
                          Recomendación
                        </span>
                        <span className="text-sm font-bold text-white flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          {p.prediction === 'home' ? p.homeTeam : p.prediction === 'away' ? p.awayTeam : 'Empate'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-500 uppercase font-bold block mb-1">
                          Cuota sugerida / Stake
                        </span>
                        <span className="text-sm font-bold text-zinc-200">
                          {p.odds ? `@${p.odds.toFixed(2)}` : '—'} <span className="text-zinc-500 font-normal">({p.suggestedStake}% Stake)</span>
                        </span>
                      </div>
                    </div>

                    {/* Stats comparison */}
                    <div className="grid grid-cols-2 gap-4 mb-4 text-xs">
                      <div>
                        <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-1">Forma {p.homeTeam}</span>
                        <FormIndicator form={p.home_form} />
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-1">Forma {p.awayTeam}</span>
                        <FormIndicator form={p.away_form} />
                      </div>
                    </div>

                    {/* Reasoning Section */}
                    <div className="mb-4">
                      <span className="text-[10px] text-zinc-500 font-bold uppercase block mb-1">Análisis IA</span>
                      <p className="text-xs text-zinc-400 leading-relaxed bg-white/[0.01] border border-white/[0.03] p-3 rounded-lg italic">
                        "{p.aiReasoning}"
                      </p>
                    </div>

                    {/* Chart section */}
                    <div className="space-y-2">
                      <span className="text-[10px] text-zinc-500 font-bold uppercase block">Distribución de Probabilidades (Modelo Blended)</span>
                      <div className="h-28 w-full bg-white/[0.01] border border-white/[0.03] rounded-lg p-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={chartData} layout="vertical" margin={{ left: -10, right: 10, top: 5, bottom: 5 }}>
                            <XAxis type="number" domain={[0, 100]} hide />
                            <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={11} width={60} />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={12}>
                              {chartData.map((entry, idx) => {
                                const colors = ['#10b981', '#f59e0b', '#f43f5e'];
                                return <Cell key={`cell-${idx}`} fill={colors[idx]} />;
                              })}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 pt-4 border-t border-white/[0.04] flex justify-between items-center text-xs">
                    <span className="text-zinc-500">Modelo: {p.modelSource ?? 'ELO/Poisson'}</span>
                    <Link
                      href={`/dashboard/pick/${p.id}`}
                      className="text-[#C8A951] hover:text-[#e4c973] font-bold flex items-center gap-1 transition-colors"
                    >
                      Ver Análisis Completo →
                    </Link>
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
