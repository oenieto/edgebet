'use client';

import { useMemo, useState } from 'react';
import { Sparkles, Target, ShieldCheck, TrendingUp, Flame, Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { Parlay, ParlayRiskProfile, Pick } from '@/types';
import {
  RISK_BANDS,
  RISK_DESCRIPTIONS,
  RISK_LABELS,
  buildParlay,
} from '@/lib/parlays/generator';

interface ParlayGeneratorProps {
  availablePicks: Pick[];
}

const PROFILE_ORDER: ParlayRiskProfile[] = ['seguro', 'moderado', 'arriesgado', 'muy_arriesgado'];

const PROFILE_ICONS: Record<ParlayRiskProfile, typeof ShieldCheck> = {
  seguro: ShieldCheck,
  moderado: TrendingUp,
  arriesgado: Flame,
  muy_arriesgado: Zap,
};

function formatBand(profile: ParlayRiskProfile): string {
  const b = RISK_BANDS[profile];
  return b.max === Infinity ? `${b.min.toFixed(2)}+` : `${b.min.toFixed(2)} – ${b.max.toFixed(2)}`;
}

export default function ParlayGenerator({ availablePicks }: ParlayGeneratorProps) {
  const [riskProfile, setRiskProfile] = useState<ParlayRiskProfile>('moderado');
  const [targetOdds, setTargetOdds] = useState<string>('4.00');
  const [parlay, setParlay] = useState<Parlay | null>(null);

  const eligibleCount = useMemo(() => {
    const band = RISK_BANDS[riskProfile];
    return availablePicks.filter(
      (p) =>
        typeof p.odds === 'number' &&
        (p.odds as number) >= band.min &&
        (p.odds as number) < (band.max === Infinity ? Number.POSITIVE_INFINITY : band.max),
    ).length;
  }, [availablePicks, riskProfile]);

  const targetNum = Number(targetOdds);
  const targetValid = !Number.isNaN(targetNum) && targetNum >= 1.1 && targetNum <= 100;

  function handleGenerate() {
    if (!targetValid) return;
    const result = buildParlay(availablePicks, riskProfile, targetNum);
    setParlay(result);
  }

  return (
    <div className="space-y-4">
      {/* Step 1: risk profile */}
      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="font-mono text-[11px] text-indigo-400 font-bold">01</span>
          <h3 className="font-sans text-[14px] font-bold text-white">Perfil de riesgo</h3>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {PROFILE_ORDER.map((p) => {
            const Icon = PROFILE_ICONS[p];
            const active = riskProfile === p;
            return (
              <button
                key={p}
                type="button"
                onClick={() => {
                  setRiskProfile(p);
                  setParlay(null);
                }}
                className={`text-left p-3 rounded-xl border transition-colors ${
                  active
                    ? 'bg-indigo-500/10 border-indigo-500/40'
                    : 'bg-white/[0.02] border-white/[0.06] hover:border-white/[0.12]'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <Icon className={`w-4 h-4 ${active ? 'text-indigo-400' : 'text-zinc-500'}`} />
                  <span
                    className={`font-sans text-[13px] font-semibold ${
                      active ? 'text-white' : 'text-zinc-300'
                    }`}
                  >
                    {RISK_LABELS[p]}
                  </span>
                </div>
                <p className="font-mono text-[11px] text-zinc-500 mb-1">{formatBand(p)}</p>
                <p className="font-sans text-[11px] text-zinc-600 leading-snug">
                  {RISK_DESCRIPTIONS[p]}
                </p>
              </button>
            );
          })}
        </div>

        <p className="mt-3 font-sans text-[11px] text-zinc-500">
          Picks disponibles en esta banda:{' '}
          <span className="font-mono text-zinc-300">{eligibleCount}</span>
        </p>
      </div>

      {/* Step 2: target odds */}
      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="font-mono text-[11px] text-indigo-400 font-bold">02</span>
          <h3 className="font-sans text-[14px] font-bold text-white">Momio objetivo</h3>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <label className="font-sans text-[12px] text-zinc-500 mb-1.5 block">
              Cuota final deseada
            </label>
            <div className="relative">
              <Target className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <input
                type="number"
                min={1.1}
                max={100}
                step={0.1}
                value={targetOdds}
                onChange={(e) => {
                  setTargetOdds(e.target.value);
                  setParlay(null);
                }}
                className="w-full h-[44px] bg-[#0a0a0c] border border-white/[0.08] rounded-xl pl-10 pr-3 font-mono text-[15px] text-white focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <p className="mt-1.5 font-sans text-[11px] text-zinc-600">
              La IA combinará picks de la banda elegida hasta acercarse a este momio (±5%).
            </p>
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!targetValid || eligibleCount < 2}
            className="h-[44px] px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-sans text-[14px] font-bold transition-colors flex items-center justify-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Generar parlay
          </button>
        </div>

        {eligibleCount < 2 && (
          <p className="mt-3 font-sans text-[12px] text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            No hay picks suficientes en esta banda. Cambia el perfil de riesgo.
          </p>
        )}
      </div>

      {/* Step 3: result */}
      {parlay && <ParlayResult parlay={parlay} />}
    </div>
  );
}

function ParlayResult({ parlay }: { parlay: Parlay }) {
  const ok = parlay.withinTolerance;
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-indigo-400 font-bold">03</span>
          <h3 className="font-sans text-[14px] font-bold text-white">Parlay generado</h3>
        </div>
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-sans font-semibold ${
            ok
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
          }`}
        >
          {ok ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              Dentro del objetivo
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5" />
              Aproximación más cercana
            </>
          )}
        </div>
      </div>

      {parlay.legs.length === 0 ? (
        <p className="font-sans text-[13px] text-zinc-500">
          No hay picks disponibles dentro del perfil seleccionado.
        </p>
      ) : (
        <>
          <div className="space-y-2 mb-4">
            {parlay.legs.map((leg) => (
              <div
                key={leg.pickId}
                className="bg-[#0a0a0c] border border-white/[0.06] rounded-xl p-3"
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-sans text-[13px] font-semibold text-white truncate">
                    {leg.homeTeam} vs {leg.awayTeam}
                  </span>
                  <span className="font-mono text-[13px] font-bold text-indigo-400 shrink-0">
                    @{leg.odds.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-sans text-[11px] text-zinc-500">{leg.prediction}</span>
                  <span className="text-zinc-700">·</span>
                  <span className="font-mono text-[11px] text-zinc-500">
                    {leg.confidence}% conf.
                  </span>
                  <span className="text-zinc-700">·</span>
                  <span className="font-sans text-[10px] uppercase tracking-wider text-zinc-600 font-semibold">
                    {leg.market}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-white/[0.06] grid grid-cols-3 gap-3">
            <div>
              <p className="font-sans text-[11px] text-zinc-500 mb-0.5">Cuotas combinadas</p>
              <p className="font-mono text-[20px] font-bold text-white">
                {parlay.combinedOdds.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="font-sans text-[11px] text-zinc-500 mb-0.5">Confianza combinada</p>
              <p className="font-mono text-[20px] font-bold text-emerald-400">
                {parlay.combinedConfidence.toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="font-sans text-[11px] text-zinc-500 mb-0.5">Objetivo</p>
              <p className="font-mono text-[20px] font-bold text-zinc-400">
                {parlay.targetOdds.toFixed(2)}
              </p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-white/[0.06]">
            <p className="font-sans text-[12px] text-zinc-500 font-semibold mb-1.5 uppercase tracking-wider">
              Análisis
            </p>
            <p className="font-sans text-[13px] text-zinc-300 leading-relaxed">
              {parlay.rationale}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
