'use client';

import { useState } from 'react';
import { AlertTriangle, Info, CheckCircle } from 'lucide-react';

interface CorrelationLeg {
  pickId: string;
  prediction: string;
  match: string;
}

interface CorrelationIndicatorProps {
  legs: CorrelationLeg[];
  correlationScore: number; // 0 to 1
}

function getLevel(score: number): 'low' | 'medium' | 'high' {
  if (score < 0.35) return 'low';
  if (score < 0.65) return 'medium';
  return 'high';
}

const levelConfig = {
  low: {
    label: 'Correlación baja',
    color: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    bgColor: 'bg-emerald-500/10',
    barColor: 'bg-emerald-500',
    Icon: CheckCircle,
  },
  medium: {
    label: 'Correlación media',
    color: 'text-amber-400',
    borderColor: 'border-amber-500/30',
    bgColor: 'bg-amber-500/10',
    barColor: 'bg-amber-500',
    Icon: Info,
  },
  high: {
    label: 'Correlación alta',
    color: 'text-red-400',
    borderColor: 'border-red-500/30',
    bgColor: 'bg-red-500/10',
    barColor: 'bg-red-500',
    Icon: AlertTriangle,
  },
};

const levelMessages = {
  low: 'Las selecciones son independientes entre sí. El parlay es estadísticamente sólido.',
  medium:
    'Algunas selecciones pueden estar relacionadas. El rendimiento del parlay puede verse afectado si los resultados comparten factores comunes.',
  high: 'Varias selecciones provienen del mismo partido u están fuertemente correlacionadas. Esto puede inflar artificialmente las cuotas combinadas sin aumentar el valor real.',
};

export default function CorrelationIndicator({ legs, correlationScore }: CorrelationIndicatorProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const level = getLevel(correlationScore);
  const config = levelConfig[level];
  const { Icon } = config;

  // Detect same-match legs
  const matchCounts: Record<string, number> = {};
  for (const leg of legs) {
    matchCounts[leg.match] = (matchCounts[leg.match] ?? 0) + 1;
  }
  const duplicateMatches = Object.entries(matchCounts)
    .filter(([, count]) => count > 1)
    .map(([match]) => match);

  if (legs.length < 2) return null;

  return (
    <div
      className={`rounded-xl border ${config.borderColor} ${config.bgColor} p-4`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 shrink-0 ${config.color}`} />
          <span className={`font-sans text-[13px] font-semibold ${config.color}`}>
            {config.label}
          </span>
        </div>

        {/* Tooltip trigger */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setTooltipOpen((v) => !v)}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            aria-label="Qué es la correlación"
          >
            <Info className="w-4 h-4" />
          </button>
          {tooltipOpen && (
            <div className="absolute right-0 top-6 z-20 w-64 bg-[#1a1a1e] border border-white/[0.08] rounded-xl p-3 shadow-lg">
              <p className="font-sans text-[12px] text-zinc-300 leading-relaxed">
                La <span className="text-white font-semibold">correlación</span> mide cuánto
                dependen unas selecciones de otras. Cuando dos picks provienen del mismo partido,
                sus resultados están vinculados y el valor real del parlay es menor del que indican
                las cuotas combinadas.
              </p>
              <button
                type="button"
                onClick={() => setTooltipOpen(false)}
                className="mt-2 text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                Cerrar
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Score bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-sans text-[11px] text-zinc-500">Índice de correlación</span>
          <span className={`font-mono text-[12px] font-bold ${config.color}`}>
            {Math.round(correlationScore * 100)}%
          </span>
        </div>
        <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${config.barColor}`}
            style={{ width: `${Math.round(correlationScore * 100)}%` }}
          />
        </div>
      </div>

      {/* Warning message */}
      <p className="mt-3 font-sans text-[12px] text-zinc-400 leading-relaxed">
        {levelMessages[level]}
      </p>

      {/* Same-match warnings */}
      {duplicateMatches.length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-1">
          {duplicateMatches.map((match) => (
            <div key={match} className="flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              <span className="font-sans text-[12px] text-red-400">
                Tienes {matchCounts[match]} selecciones del mismo partido:{' '}
                <span className="font-semibold text-white">{match}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
