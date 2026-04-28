'use client';

import { ChevronRight } from 'lucide-react';
import { RANKS, getProgressToNext } from '@/lib/ranking/tiers';
import RankBadge from './RankBadge';

interface Props {
  xp: number;
}

export default function RankCard({ xp }: Props) {
  const { current, next, pct, xpInLevel, xpNeeded } = getProgressToNext(xp);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-[#111114] p-6">
      <div
        className={`absolute -top-32 -right-24 w-72 h-72 rounded-full bg-gradient-to-br ${current.glow} blur-3xl pointer-events-none`}
        style={{ opacity: 0.7 }}
      />

      <div className="relative">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <div className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold mb-2">
              Tu rango
            </div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="font-sans font-extrabold text-[28px] text-white tracking-tight" style={{ color: current.color }}>
                {current.name}
              </h3>
              <span className="font-mono text-[11px] text-zinc-500">Nivel {current.level}</span>
            </div>
            <p className="font-sans text-[13px] text-zinc-400 max-w-md">{current.tagline}</p>
          </div>
          <RankBadge rank={current} size="md" />
        </div>

        {next ? (
          <div className="border-t border-white/[0.06] pt-5">
            <div className="flex items-end justify-between mb-2">
              <div>
                <div className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold">
                  Siguiente: {next.name}
                </div>
                <div className="font-mono text-[14px] text-white mt-1">
                  {xpInLevel} <span className="text-zinc-500">/ {xpNeeded} XP</span>
                </div>
              </div>
              <div className="font-mono text-[24px] font-bold" style={{ color: next.color }}>
                {pct}%
              </div>
            </div>
            <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full rounded-full transition-[width] duration-700"
                style={{
                  width: `${pct}%`,
                  background: `linear-gradient(90deg, ${current.color}, ${next.color})`,
                }}
              />
            </div>
            <p className="font-sans text-[12px] text-zinc-500 mt-3">
              Te faltan <span className="text-white font-mono">{xpNeeded - xpInLevel}</span> XP. Ganas 
              <span className="text-white font-mono"> 10 XP</span> por jugar y 
              <span className="text-emerald-400 font-mono"> +50 XP</span> extra si la apuesta es ganadora.
            </p>
          </div>
        ) : (
          <div className="border-t border-white/[0.06] pt-5">
            <p className="font-sans text-[13px] text-zinc-300">
              Has alcanzado el rango máximo. Mantenelo apostando con disciplina.
            </p>
          </div>
        )}

        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold">
              Ladder de rangos
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
          </div>
          <div className="flex gap-1.5">
            {RANKS.map((r) => {
              const reached = xp >= r.minXp;
              const isCurrent = r.id === current.id;
              return (
                <div
                  key={r.id}
                  className="flex-1 h-2 rounded-full transition-colors"
                  style={{
                    backgroundColor: reached ? r.color : 'rgba(255,255,255,0.06)',
                    boxShadow: isCurrent ? `0 0 8px ${r.color}` : undefined,
                  }}
                  title={`${r.name} · ${r.minXp} XP`}
                />
              );
            })}
          </div>
          <div className="flex gap-1.5 mt-2">
            {RANKS.map((r) => (
              <div key={`l-${r.id}`} className="flex-1 text-center">
                <span
                  className="font-mono text-[9px]"
                  style={{ color: xp >= r.minXp ? r.color : '#52525b' }}
                >
                  {r.level}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
