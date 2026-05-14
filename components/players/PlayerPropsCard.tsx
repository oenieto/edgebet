'use client';

import { useState } from 'react';
import { ChevronDown, Plus, User } from 'lucide-react';
import type { PlayerPropLine } from '@/types';

interface PlayerData {
  name: string;
  team: string;
  props: PlayerPropLine[];
}

interface PlayerPropsCardProps {
  players: PlayerData[];
  onAddToParlay?: (prop: PlayerPropLine, selection: 'over' | 'under') => void;
}

const PROP_LABELS: Record<string, string> = {
  shots: 'Tiros',
  sot: 'Tiros a puerta',
  cards: 'Tarjetas',
  passes: 'Pases',
  goals: 'Goles',
};

export default function PlayerPropsCard({ players, onAddToParlay }: PlayerPropsCardProps) {
  const [selectedPlayer, setSelectedPlayer] = useState<string>(players[0]?.name ?? '');
  const [expandedProp, setExpandedProp] = useState<string | null>(null);

  const player = players.find((p) => p.name === selectedPlayer);

  if (players.length === 0) {
    return (
      <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-6 text-center">
        <User className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
        <p className="font-sans text-[13px] text-zinc-500">
          Sin datos de jugadores disponibles para este partido
        </p>
      </div>
    );
  }

  // Group props by type
  const propsByType: Record<string, PlayerPropLine[]> = {};
  if (player) {
    for (const p of player.props) {
      if (!propsByType[p.prop_type]) propsByType[p.prop_type] = [];
      propsByType[p.prop_type].push(p);
    }
  }

  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <h3 className="font-sans font-bold text-[15px] text-white flex items-center gap-2 mb-3">
          <User className="w-4 h-4 text-zinc-400" />
          Player props
        </h3>

        {/* Player selector */}
        <div className="relative">
          <select
            value={selectedPlayer}
            onChange={(e) => {
              setSelectedPlayer(e.target.value);
              setExpandedProp(null);
            }}
            className="w-full h-[38px] px-3 pr-8 rounded-lg bg-[#16161a] border border-white/[0.08] font-sans text-[13px] text-white appearance-none focus:outline-none focus:border-white/[0.2]"
          >
            {players.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} ({p.team})
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 text-zinc-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {player && (
        <div className="divide-y divide-white/[0.04]">
          {Object.entries(propsByType).map(([propType, lines]) => (
            <div key={propType}>
              <button
                type="button"
                onClick={() =>
                  setExpandedProp(expandedProp === propType ? null : propType)
                }
                className="w-full px-5 py-3 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
              >
                <span className="font-sans text-[13px] font-semibold text-white">
                  {PROP_LABELS[propType] ?? propType}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-zinc-500 transition-transform ${
                    expandedProp === propType ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {expandedProp === propType && (
                <div className="px-5 pb-4 space-y-3">
                  {lines.map((line) => (
                    <PropLine
                      key={`${line.prop_type}-${line.line}`}
                      line={line}
                      onAdd={onAddToParlay}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PropLine({
  line,
  onAdd,
}: {
  line: PlayerPropLine;
  onAdd?: (prop: PlayerPropLine, selection: 'over' | 'under') => void;
}) {
  const overPct = (line.over_prob * 100).toFixed(0);
  const underPct = (line.under_prob * 100).toFixed(0);

  return (
    <div className="bg-[#16161a] border border-white/[0.04] rounded-lg p-3">
      <div className="font-mono text-[11px] text-zinc-500 mb-2">
        Linea: {line.line}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onAdd?.(line, 'over')}
          className="flex-1 flex items-center justify-between px-3 py-2 rounded-md bg-emerald-500/10 border border-emerald-500/20 hover:border-emerald-500/40 transition-colors group"
        >
          <span className="font-sans text-[12px] text-emerald-300">Over {line.line}</span>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[13px] font-bold text-emerald-400">{overPct}%</span>
            {onAdd && (
              <Plus className="w-3 h-3 text-emerald-500/0 group-hover:text-emerald-400 transition-colors" />
            )}
          </div>
        </button>
        <button
          type="button"
          onClick={() => onAdd?.(line, 'under')}
          className="flex-1 flex items-center justify-between px-3 py-2 rounded-md bg-red-500/10 border border-red-500/20 hover:border-red-500/40 transition-colors group"
        >
          <span className="font-sans text-[12px] text-red-300">Under {line.line}</span>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[13px] font-bold text-red-400">{underPct}%</span>
            {onAdd && (
              <Plus className="w-3 h-3 text-red-500/0 group-hover:text-red-400 transition-colors" />
            )}
          </div>
        </button>
      </div>
    </div>
  );
}
