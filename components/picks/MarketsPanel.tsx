'use client';

import { useState } from 'react';
import {
  ShieldCheck,
  TrendingUp,
  Goal,
  Users,
  Scale,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Lock,
} from 'lucide-react';
import type { MarketKey, MarketOutcome, Pick } from '@/types';

interface MarketsPanelProps {
  pick: Pick;
}

const SECTION_META: Record<
  MarketKey,
  { label: string; icon: typeof ShieldCheck; accent: string; description: string }
> = {
  ML: {
    label: '1X2',
    icon: TrendingUp,
    accent: 'text-indigo-300',
    description: 'Resultado final del partido (gana local / empate / gana visitante)',
  },
  DC: {
    label: 'Doble oportunidad',
    icon: ShieldCheck,
    accent: 'text-purple-300',
    description: 'Cubre dos resultados con una sola apuesta — menos riesgo, menor cuota',
  },
  OU: {
    label: 'Total de goles',
    icon: Goal,
    accent: 'text-sky-300',
    description: 'Apuesta a más/menos goles totales sobre cada línea',
  },
  BTTS: {
    label: 'Ambos anotan',
    icon: Users,
    accent: 'text-pink-300',
    description: '¿Marcan los dos equipos en el partido?',
  },
  SPREAD: {
    label: 'Hándicap (Spread)',
    icon: Scale,
    accent: 'text-orange-300',
    description: 'Compensa la diferencia de nivel con un handicap por equipo',
  },
  TEAM_TOTALS: {
    label: 'Goles por equipo',
    icon: BarChart3,
    accent: 'text-teal-300',
    description: 'Total de goles que anota cada equipo por separado',
  },
};

type MarketSection = {
  key: MarketKey;
  outcomes: MarketOutcome[];
};

export default function MarketsPanel({ pick }: MarketsPanelProps) {
  const sections: MarketSection[] = (
    [
      { key: 'OU', outcomes: pick.markets?.ou_outcomes ?? [] },
      { key: 'DC', outcomes: pick.markets?.dc_outcomes ?? [] },
      { key: 'BTTS', outcomes: pick.markets?.btts_outcomes ?? [] },
      { key: 'SPREAD', outcomes: pick.markets?.spread_outcomes ?? [] },
      { key: 'TEAM_TOTALS', outcomes: pick.markets?.team_totals_outcomes ?? [] },
    ] as MarketSection[]
  ).filter((s) => s.outcomes.length > 0);

  if (sections.length === 0) {
    return (
      <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6 text-center">
        <p className="font-sans text-[13px] text-zinc-500">
          No hay mercados secundarios disponibles para este partido.
        </p>
      </div>
    );
  }

  const lambdaTotal = pick.markets?.expected_total_goals;

  return (
    <div className="space-y-3">
      <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-sans font-bold text-[16px] text-white">Mercados disponibles</h3>
          {lambdaTotal != null && (
            <div className="font-mono text-[11px] text-zinc-500">
              Goles esperados:{' '}
              <span className="text-white font-bold">{lambdaTotal.toFixed(2)}</span>
            </div>
          )}
        </div>
        <p className="font-sans text-[12px] text-zinc-500 mb-5 leading-relaxed">
          Cuotas reales agregadas cross-bookmaker (best price). Edge = nuestra probabilidad menos
          la implícita del mercado. EV = ganancia esperada por unidad apostada.
        </p>

        <div className="space-y-3">
          {sections.map((section) => (
            <MarketSection key={section.key} section={section} />
          ))}
        </div>
      </div>
    </div>
  );
}

function MarketSection({ section }: { section: MarketSection }) {
  const meta = SECTION_META[section.key];
  const Icon = meta.icon;

  // Por defecto colapsamos secciones de muchas filas (SPREAD/TEAM_TOTALS = 12),
  // y abrimos las cortas (DC=3, BTTS=2, OU=6).
  const [open, setOpen] = useState(section.outcomes.length <= 6);

  const verifiedCount = section.outcomes.filter((o) => o.odds != null).length;
  const topEv = section.outcomes
    .filter((o) => o.ev_pct != null)
    .sort((a, b) => (b.ev_pct ?? 0) - (a.ev_pct ?? 0))[0];

  return (
    <div className="bg-[#111114] border border-white/[0.04] rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <Icon className={`w-4 h-4 ${meta.accent} shrink-0`} />
          <div className="text-left min-w-0">
            <div className="font-sans font-bold text-[13px] text-white">{meta.label}</div>
            <div className="font-sans text-[11px] text-zinc-500 truncate">{meta.description}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <div className="font-mono text-[11px] text-zinc-500">
              {verifiedCount}/{section.outcomes.length} con cuota
            </div>
            {topEv && topEv.ev_pct != null && (
              <div
                className={`font-mono text-[11px] font-bold ${
                  topEv.ev_pct > 0 ? 'text-emerald-400' : 'text-zinc-500'
                }`}
              >
                Mejor EV: {topEv.ev_pct > 0 ? '+' : ''}
                {topEv.ev_pct.toFixed(1)}%
              </div>
            )}
          </div>
          {open ? (
            <ChevronUp className="w-4 h-4 text-zinc-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-zinc-500" />
          )}
        </div>
      </button>

      {open && (
        <div className="border-t border-white/[0.04]">
          <table className="w-full">
            <thead>
              <tr className="text-[9px] uppercase tracking-widest font-sans font-bold text-zinc-600">
                <th className="px-4 py-2 text-left font-medium">Outcome</th>
                <th className="px-3 py-2 text-right font-medium">Nuestra prob.</th>
                <th className="px-3 py-2 text-right font-medium hidden sm:table-cell">Mercado</th>
                <th className="px-3 py-2 text-right font-medium hidden md:table-cell">Edge</th>
                <th className="px-3 py-2 text-right font-medium">EV</th>
                <th className="px-4 py-2 text-right font-medium">Cuota</th>
              </tr>
            </thead>
            <tbody>
              {section.outcomes.map((o, i) => (
                <OutcomeRow key={`${o.outcome}-${i}`} outcome={o} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function OutcomeRow({ outcome }: { outcome: MarketOutcome }) {
  const hasOdds = outcome.odds != null;
  const ev = outcome.ev_pct;
  const edge = outcome.edge_pp;

  const evClass =
    ev == null
      ? 'text-zinc-600'
      : ev > 5
        ? 'text-emerald-400 font-bold'
        : ev > 0
          ? 'text-emerald-500'
          : 'text-zinc-500';

  const edgeClass =
    edge == null
      ? 'text-zinc-600'
      : edge > 3
        ? 'text-emerald-400'
        : edge > 0
          ? 'text-zinc-300'
          : 'text-zinc-500';

  return (
    <tr className="border-t border-white/[0.03]">
      <td className="px-4 py-2.5">
        <span className="font-sans text-[12.5px] text-white">{outcome.label}</span>
      </td>
      <td className="px-3 py-2.5 text-right">
        <span className="font-mono text-[12.5px] text-white">
          {outcome.our_prob_pct.toFixed(1)}%
        </span>
      </td>
      <td className="px-3 py-2.5 text-right hidden sm:table-cell">
        <span className="font-mono text-[12.5px] text-zinc-400">
          {outcome.market_prob_pct != null ? `${outcome.market_prob_pct.toFixed(1)}%` : '—'}
        </span>
      </td>
      <td className="px-3 py-2.5 text-right hidden md:table-cell">
        <span className={`font-mono text-[12.5px] ${edgeClass}`}>
          {edge != null ? `${edge > 0 ? '+' : ''}${edge.toFixed(1)}pp` : '—'}
        </span>
      </td>
      <td className="px-3 py-2.5 text-right">
        <span className={`font-mono text-[12.5px] ${evClass}`}>
          {ev != null ? `${ev > 0 ? '+' : ''}${ev.toFixed(1)}%` : '—'}
        </span>
      </td>
      <td className="px-4 py-2.5 text-right">
        {hasOdds ? (
          <span className="inline-flex items-center h-[26px] px-2.5 rounded-md bg-white/[0.06] border border-white/[0.08] font-mono font-bold text-[12.5px] text-white">
            {outcome.odds!.toFixed(2)}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-zinc-600">
            <Lock className="w-3 h-3" />
            sin cuota
          </span>
        )}
      </td>
    </tr>
  );
}
