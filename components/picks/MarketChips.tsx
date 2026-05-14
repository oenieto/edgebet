'use client';

import { Sparkles, ShieldCheck, TrendingUp, Goal, Users, Scale, BarChart3 } from 'lucide-react';
import type { Pick, RiskProfile } from '@/types';
import {
  riskTone,
  selectSafePick,
  topPickPerMarket,
  type MarketBest,
  type SelectedMarket,
} from '@/lib/picks/safe-pick';

const MARKET_LABEL: Record<SelectedMarket, string> = {
  ML: '1X2',
  DC: 'Doble oportunidad',
  OU: 'Goles',
  BTTS: 'Ambos anotan',
  SPREAD: 'Hándicap',
  TEAM_TOTALS: 'Goles por equipo',
};

const MARKET_ICON: Record<SelectedMarket, typeof ShieldCheck> = {
  ML: TrendingUp,
  DC: ShieldCheck,
  OU: Goal,
  BTTS: Users,
  SPREAD: Scale,
  TEAM_TOTALS: BarChart3,
};

const TONE_STYLES = {
  safe: {
    chip: 'border-emerald-500/40 bg-emerald-500/10',
    label: 'text-emerald-300',
    prob: 'text-emerald-400',
    dot: 'bg-emerald-400',
  },
  medium: {
    chip: 'border-amber-500/40 bg-amber-500/10',
    label: 'text-amber-300',
    prob: 'text-amber-400',
    dot: 'bg-amber-400',
  },
  risky: {
    chip: 'border-rose-500/40 bg-rose-500/10',
    label: 'text-rose-300',
    prob: 'text-rose-400',
    dot: 'bg-rose-400',
  },
} as const;

interface MarketChipsProps {
  pick: Pick;
  profile?: RiskProfile;
}

export default function MarketChips({ pick, profile = 'balanced' }: MarketChipsProps) {
  const safe = selectSafePick(pick, profile);
  const all = topPickPerMarket(pick);

  if (all.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
        <span className="font-sans text-[11px] font-bold uppercase tracking-widest text-zinc-500">
          Mercados disponibles
        </span>
        <span className="font-sans text-[10px] text-zinc-600">
          · Recomendado para perfil {profileLabel(profile)}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {all.map((m) => {
          const isSafe = m.market === safe.market && m.outcome === safe.outcome;
          return <MarketChip key={`${m.market}-${m.outcome}`} chip={m} highlighted={isSafe} />;
        })}
      </div>
    </div>
  );
}

function MarketChip({ chip, highlighted }: { chip: MarketBest; highlighted: boolean }) {
  const tone = riskTone(chip.probability);
  const styles = TONE_STYLES[tone];
  const Icon = MARKET_ICON[chip.market];

  return (
    <div
      className={`relative rounded-xl border p-3 transition-colors ${
        highlighted
          ? 'border-indigo-500/60 bg-indigo-500/10 shadow-[0_0_18px_rgba(99,102,241,0.18)]'
          : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]'
      }`}
    >
      {highlighted && (
        <span className="absolute -top-2 left-3 flex items-center gap-1 px-1.5 h-[18px] rounded-full bg-indigo-500 text-white font-mono text-[9px] font-bold uppercase tracking-widest">
          <Sparkles className="w-2.5 h-2.5" />
          Para ti
        </span>
      )}

      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon className="w-3.5 h-3.5 text-zinc-500" />
        <span className="font-mono text-[9px] font-bold uppercase tracking-widest text-zinc-500">
          {MARKET_LABEL[chip.market]}
        </span>
      </div>

      <div className="font-sans text-[13px] font-semibold text-white leading-tight mb-2 truncate">
        {chip.label}
      </div>

      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${styles.chip}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />
          <span className={`font-mono text-[10px] font-bold uppercase tracking-wider ${styles.label}`}>
            {toneWord(tone)}
          </span>
        </div>
        <span className={`font-mono text-[15px] font-bold ${styles.prob}`}>
          {chip.probability.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

function toneWord(tone: 'safe' | 'medium' | 'risky'): string {
  if (tone === 'safe') return 'Seguro';
  if (tone === 'medium') return 'Medio';
  return 'Riesgo';
}

function profileLabel(profile: RiskProfile): string {
  if (profile === 'conservative') return 'conservador';
  if (profile === 'aggressive') return 'agresivo';
  return 'equilibrado';
}
