'use client';

import { useState, useCallback } from 'react';
import { Reorder, useDragControls } from 'framer-motion';
import { GripVertical, Plus, Trash2, AlertTriangle } from 'lucide-react';
import type { Pick } from '@/types';
import type { ParlayLeg } from '@/types';
import CorrelationIndicator from './CorrelationIndicator';

interface ParlayBuilderProps {
  availablePicks: Pick[];
  userBankroll?: number;
}

type RiskProfile = 'conservative' | 'balanced' | 'aggressive';

const KELLY_FRACTION: Record<RiskProfile, number> = {
  conservative: 0.25,
  balanced: 0.5,
  aggressive: 1.0,
};

const RISK_LABELS: Record<RiskProfile, string> = {
  conservative: 'Conservador',
  balanced: 'Equilibrado',
  aggressive: 'Agresivo',
};

function pickToLeg(pick: Pick): ParlayLeg {
  return {
    pickId: pick.id,
    match: pick.match,
    homeTeam: pick.homeTeam,
    awayTeam: pick.awayTeam,
    prediction: pick.prediction,
    odds: pick.odds ?? 1.9,
    confidence: pick.confidence,
    market: pick.market ?? 'ML',
  };
}

function calcCombinedOdds(legs: ParlayLeg[]): number {
  if (legs.length === 0) return 1;
  return legs.reduce((acc, leg) => acc * leg.odds, 1);
}

function calcCorrelationScore(legs: ParlayLeg[]): number {
  if (legs.length < 2) return 0;
  const matchCounts: Record<string, number> = {};
  for (const leg of legs) {
    matchCounts[leg.match] = (matchCounts[leg.match] ?? 0) + 1;
  }
  const duplicates = Object.values(matchCounts).filter((c) => c > 1).length;
  const base = duplicates / legs.length;
  // Slight increase per extra leg (more legs = higher systemic correlation risk)
  return Math.min(base + legs.length * 0.04, 1);
}

function calcKellyStake(combinedOdds: number, avgConf: number, kellyFraction: number): number {
  const p = avgConf / 100;
  const b = combinedOdds - 1;
  const kelly = (b * p - (1 - p)) / b;
  return Math.max(0, kelly * kellyFraction * 100);
}

function LegItem({
  leg,
  onRemove,
}: {
  leg: ParlayLeg;
  onRemove: (id: string) => void;
}) {
  const controls = useDragControls();

  return (
    <Reorder.Item
      value={leg}
      dragListener={false}
      dragControls={controls}
      className="bg-[#111114] border border-white/[0.06] rounded-xl p-3 flex items-center gap-3 cursor-default"
    >
      <button
        type="button"
        className="text-zinc-600 hover:text-zinc-400 cursor-grab active:cursor-grabbing shrink-0 touch-none"
        onPointerDown={(e) => controls.start(e)}
        aria-label="Arrastrar"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-0.5">
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
          <span className="font-mono text-[11px] text-zinc-500">{leg.confidence}% conf.</span>
          <span className="text-zinc-700">·</span>
          <span className="font-sans text-[10px] uppercase tracking-wider text-zinc-600 font-semibold">
            {leg.market}
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={() => onRemove(leg.pickId)}
        className="text-zinc-600 hover:text-red-400 transition-colors shrink-0"
        aria-label="Eliminar selección"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </Reorder.Item>
  );
}

export default function ParlayBuilder({ availablePicks, userBankroll = 1000 }: ParlayBuilderProps) {
  const [legs, setLegs] = useState<ParlayLeg[]>([]);
  const [risk, setRisk] = useState<RiskProfile>('balanced');
  const [stake, setStake] = useState<number>(0);

  const MAX_LEGS = 6;

  const addLeg = useCallback(
    (pick: Pick) => {
      if (legs.length >= MAX_LEGS) return;
      if (legs.some((l) => l.pickId === pick.id)) return;
      setLegs((prev) => [...prev, pickToLeg(pick)]);
    },
    [legs],
  );

  const removeLeg = useCallback((id: string) => {
    setLegs((prev) => prev.filter((l) => l.pickId !== id));
  }, []);

  const combinedOdds = calcCombinedOdds(legs);
  const avgConf = legs.length > 0 ? legs.reduce((a, l) => a + l.confidence, 0) / legs.length : 0;
  const kellyPct = calcKellyStake(combinedOdds, avgConf, KELLY_FRACTION[risk]);
  const suggestedStake = (kellyPct / 100) * userBankroll;
  const potentialPayout = stake > 0 ? stake * combinedOdds : suggestedStake * combinedOdds;
  const correlationScore = calcCorrelationScore(legs);

  const correlationLegs = legs.map((l) => ({
    pickId: l.pickId,
    prediction: l.prediction,
    match: l.match,
  }));

  const availableToAdd = availablePicks.filter(
    (p) => !legs.some((l) => l.pickId === p.id),
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
      {/* Left: available picks */}
      <div>
        <h3 className="font-sans text-[13px] font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Picks disponibles
        </h3>

        {availableToAdd.length === 0 && availablePicks.length > 0 && (
          <p className="font-sans text-[13px] text-zinc-500">
            Todos los picks disponibles han sido añadidos al parlay.
          </p>
        )}

        {availablePicks.length === 0 && (
          <p className="font-sans text-[13px] text-zinc-500">No hay picks disponibles.</p>
        )}

        <div className="space-y-2">
          {availableToAdd.map((pick) => {
            const isMaxed = legs.length >= MAX_LEGS;
            return (
              <div
                key={pick.id}
                className="bg-[#111114] border border-white/[0.06] rounded-xl p-3 flex items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className="font-sans text-[13px] font-semibold text-white truncate">
                      {pick.homeTeam} vs {pick.awayTeam}
                    </span>
                    {pick.odds != null && (
                      <span className="font-mono text-[13px] font-bold text-indigo-400 shrink-0">
                        @{pick.odds.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-sans text-[11px] text-zinc-500">{pick.prediction}</span>
                    <span className="text-zinc-700">·</span>
                    <span className="font-mono text-[11px] text-zinc-500">
                      {pick.confidence}% conf.
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => addLeg(pick)}
                  disabled={isMaxed}
                  className="flex items-center gap-1.5 px-3 h-[30px] rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-sans text-[12px] font-semibold transition-colors shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Añadir
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right: slip */}
      <div className="space-y-4">
        <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-sans text-[14px] font-bold text-white">Parlay slip</h3>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-zinc-500">
                {legs.length}/{MAX_LEGS}
              </span>
              {legs.length >= MAX_LEGS && (
                <span className="flex items-center gap-1 text-amber-400 font-sans text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Máximo
                </span>
              )}
            </div>
          </div>

          {legs.length === 0 ? (
            <div className="py-8 text-center">
              <p className="font-sans text-[13px] text-zinc-600">
                Añade picks desde la lista para armar tu parlay.
              </p>
            </div>
          ) : (
            <Reorder.Group axis="y" values={legs} onReorder={setLegs} className="space-y-2 mb-4">
              {legs.map((leg) => (
                <LegItem key={leg.pickId} leg={leg} onRemove={removeLeg} />
              ))}
            </Reorder.Group>
          )}

          {/* Combined odds */}
          {legs.length >= 2 && (
            <div className="pt-3 border-t border-white/[0.06]">
              <div className="flex items-center justify-between">
                <span className="font-sans text-[13px] text-zinc-400">Cuotas combinadas</span>
                <span className="font-mono text-[20px] font-bold text-white">
                  {combinedOdds.toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Risk slider */}
        {legs.length >= 2 && (
          <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-4">
            <h4 className="font-sans text-[13px] font-semibold text-zinc-400 mb-3">
              Perfil de riesgo
            </h4>
            <div className="flex gap-2">
              {(['conservative', 'balanced', 'aggressive'] as RiskProfile[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRisk(r)}
                  className={`flex-1 h-[32px] rounded-lg font-sans text-[12px] font-semibold transition-colors border ${
                    risk === r
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-white/5 border-white/[0.08] text-zinc-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {RISK_LABELS[r]}
                </button>
              ))}
            </div>
            <p className="mt-2 font-sans text-[11px] text-zinc-600">
              Kelly {(KELLY_FRACTION[risk] * 100).toFixed(0)}% fracción
            </p>
          </div>
        )}

        {/* Stake calculator */}
        {legs.length >= 2 && (
          <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-4 space-y-4">
            <h4 className="font-sans text-[13px] font-semibold text-zinc-400">
              Calculadora de apuesta
            </h4>

            <div>
              <label className="font-sans text-[12px] text-zinc-500 mb-1.5 block">
                Apuesta (€)
              </label>
              <input
                type="number"
                min={0}
                step={1}
                value={stake || ''}
                onChange={(e) => setStake(Number(e.target.value))}
                placeholder={suggestedStake.toFixed(2)}
                className="w-full h-[40px] bg-[#0a0a0c] border border-white/[0.08] rounded-xl px-3 font-mono text-[14px] text-white placeholder:text-zinc-700 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <p className="mt-1 font-sans text-[11px] text-zinc-600">
                Kelly sugiere:{' '}
                <span className="font-mono text-zinc-400">
                  €{suggestedStake.toFixed(2)} ({kellyPct.toFixed(1)}% bankroll)
                </span>
              </p>
            </div>

            <div className="pt-3 border-t border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-sans text-[13px] text-zinc-400">Apuesta</span>
                <span className="font-mono text-[14px] text-white font-semibold">
                  €{(stake || suggestedStake).toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-sans text-[13px] text-zinc-400">Pago potencial</span>
                <span className="font-mono text-[16px] font-bold text-emerald-400">
                  €{potentialPayout.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-sans text-[13px] text-zinc-400">Beneficio neto</span>
                <span className="font-mono text-[14px] font-semibold text-emerald-400">
                  +€{(potentialPayout - (stake || suggestedStake)).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Correlation indicator */}
        {legs.length >= 2 && (
          <CorrelationIndicator legs={correlationLegs} correlationScore={correlationScore} />
        )}

        {/* Add to slip CTA */}
        {legs.length >= 2 && (
          <button
            type="button"
            className="w-full h-[44px] rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-sans text-[14px] font-bold transition-colors"
          >
            Confirmar parlay
          </button>
        )}
      </div>
    </div>
  );
}
