'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ProbMap } from '@/types';

interface PolymarketChartProps {
  mlProb: ProbMap;
  polyProb?: ProbMap | null;
  bkProb: ProbMap;
  prediction: string;
  homeTeam: string;
  awayTeam: string;
}

const COLORS = {
  ml: '#6366f1',
  poly: '#8b5cf6',
  bk: '#f59e0b',
};

const outcomeLabels: Record<string, string> = {
  home: 'Local',
  draw: 'Empate',
  away: 'Visitante',
};

/**
 * Comparative bar chart showing probabilities from the 3 sources
 * (ML model, Polymarket, Bookmaker) for each outcome.
 * Used in Pick Detail to visualize probability divergences.
 */
export default function PolymarketChart({
  mlProb,
  polyProb,
  bkProb,
  prediction,
  homeTeam,
  awayTeam,
}: PolymarketChartProps) {
  const outcomes = ['home', 'draw', 'away'];

  const chartData = outcomes.map((outcome) => ({
    outcome: outcome === 'home' ? homeTeam : outcome === 'away' ? awayTeam : outcomeLabels[outcome],
    ML: +((mlProb[outcome] ?? 0) * 100).toFixed(1),
    Polymarket: +((polyProb?.[outcome] ?? 0) * 100).toFixed(1),
    Bookmaker: +((bkProb[outcome] ?? 0) * 100).toFixed(1),
    isSelected: outcome === prediction,
  }));

  const hasPolyData = polyProb && Object.values(polyProb).some((v) => v > 0);

  return (
    <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-sans font-bold text-[16px] text-white flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-purple-500/20 flex items-center justify-center">
            <span className="font-mono text-[9px] font-bold text-purple-300">P</span>
          </div>
          Comparativa de fuentes
        </h3>
        <div className="flex items-center gap-3">
          <Legend color={COLORS.ml} label="ML" />
          {hasPolyData && <Legend color={COLORS.poly} label="Poly" />}
          <Legend color={COLORS.bk} label="BK" />
        </div>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="outcome"
            tick={{ fontSize: 11, fill: '#a1a1aa', fontFamily: 'sans-serif' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip content={<SourceTooltip />} />
          <Bar dataKey="ML" fill={COLORS.ml} radius={[3, 3, 0, 0]} />
          {hasPolyData && <Bar dataKey="Polymarket" fill={COLORS.poly} radius={[3, 3, 0, 0]} />}
          <Bar dataKey="Bookmaker" fill={COLORS.bk} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Divergence indicator */}
      {hasPolyData && (
        <DivergenceRow mlProb={mlProb} polyProb={polyProb!} bkProb={bkProb} prediction={prediction} />
      )}
    </div>
  );
}

function DivergenceRow({
  mlProb,
  polyProb,
  bkProb,
  prediction,
}: {
  mlProb: ProbMap;
  polyProb: ProbMap;
  bkProb: ProbMap;
  prediction: string;
}) {
  const mlVal = (mlProb[prediction] ?? 0) * 100;
  const polyVal = (polyProb[prediction] ?? 0) * 100;
  const bkVal = (bkProb[prediction] ?? 0) * 100;

  const maxDiv = Math.max(Math.abs(mlVal - polyVal), Math.abs(mlVal - bkVal));
  const divergenceLevel = maxDiv > 10 ? 'alta' : maxDiv > 5 ? 'media' : 'baja';
  const divColor =
    divergenceLevel === 'alta'
      ? 'text-red-400'
      : divergenceLevel === 'media'
        ? 'text-amber-400'
        : 'text-emerald-400';

  return (
    <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between">
      <span className="font-sans text-[11px] text-zinc-500">
        Divergencia entre fuentes para la prediccion seleccionada
      </span>
      <span className={`font-mono text-[12px] font-bold ${divColor}`}>
        {maxDiv.toFixed(1)}pp ({divergenceLevel})
      </span>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
      <span className="font-mono text-[10px] text-zinc-400 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function SourceTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#1a1a1f] border border-white/[0.1] rounded-lg px-3 py-2 shadow-xl">
      <p className="font-sans text-[11px] text-white font-semibold mb-1.5">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mb-0.5">
          <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: p.fill }} />
          <span className="font-mono text-[11px] text-zinc-300">
            {p.dataKey}: {p.value}%
          </span>
        </div>
      ))}
    </div>
  );
}
