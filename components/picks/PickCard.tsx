'use client';

import Link from 'next/link';
import { CheckCircle2, Lock, Target, ChevronRight } from 'lucide-react';
import type { Pick } from '@/types';
import TeamLogo from './TeamLogo';

interface PickCardProps {
  pick: Pick;
  locked?: boolean;
}

const predictionLabel: Record<string, string> = {
  home: 'Gana local',
  draw: 'Empate',
  away: 'Gana visitante',
  over_1_5: 'Más de 1.5 goles',
  under_1_5: 'Menos de 1.5 goles',
  over_2_5: 'Más de 2.5 goles',
  under_2_5: 'Menos de 2.5 goles',
  over_3_5: 'Más de 3.5 goles',
  under_3_5: 'Menos de 3.5 goles',
};

function formatKickoff(iso: string): string {
  try {
    const date = new Date(iso);
    return (
      date.toLocaleString('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: 'short',
        timeZone: 'UTC',
      }) + ' UTC'
    );
  } catch {
    return iso;
  }
}

function probPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export default function PickCard({ pick, locked = false }: PickCardProps) {
  const isLocked = locked && pick.status !== 'free';
  const mainProb = pick.mlProb[pick.prediction] ?? 0;

  return (
    <div className="bg-surface-container-lowest border border-surface-container-low rounded-2xl p-6 relative flex flex-col overflow-hidden">
      <div className="absolute top-4 right-4">
        {pick.status === 'free' && (
          <span className="bg-secondary-container text-on-secondary-container px-2 py-1 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider">
            Free
          </span>
        )}
        {pick.status === 'premium' && (
          <span className="bg-primary/10 text-primary px-2 py-1 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider">
            Premium
          </span>
        )}
        {pick.status === 'vip' && (
          <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider">
            VIP
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 mb-4 pt-2 text-tertiary">
        <Target className="w-4 h-4" />
        <span className="text-[12px] font-medium">
          {pick.league} · {formatKickoff(pick.kickoff)}
        </span>
      </div>

      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex flex-col items-center gap-2 flex-1 min-w-0">
          <TeamLogo src={pick.homeLogo} name={pick.homeTeam} size={40} />
          <div className="font-sans font-bold text-[14px] text-on-surface text-center truncate w-full" title={pick.homeTeam}>
            {pick.homeTeam}
          </div>
        </div>
        <span className="text-tertiary font-mono text-[11px] shrink-0">vs</span>
        <div className="flex flex-col items-center gap-2 flex-1 min-w-0">
          <TeamLogo src={pick.awayLogo} name={pick.awayTeam} size={40} />
          <div className="font-sans font-bold text-[14px] text-on-surface text-center truncate w-full" title={pick.awayTeam}>
            {pick.awayTeam}
          </div>
        </div>
      </div>

      {isLocked ? (
        <LockedOverlay />
      ) : (
        <>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-sans text-[13px] text-on-surface-variant">{predictionLabel[pick.prediction]}</span>
              <span className="font-mono font-bold text-[13px] text-primary">{pick.confidence}%</span>
            </div>
            <div className="h-1 w-full bg-surface-container-high rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all"
                style={{ width: `${pick.confidence}%` }}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            <SourcePill
              label="ML" 
              prob={mainProb} 
            />
            {pick.polyProb && pick.polyProb[pick.prediction] && (
              <SourcePill
                label="Poly"
                prob={pick.polyProb[pick.prediction]}
              />
            )}
            {pick.bkProb && pick.bkProb[pick.prediction] && (
              <SourcePill
                label="BK"
                prob={pick.bkProb[pick.prediction]}
              />
            )}
          </div>

          <div className="mt-auto pt-3 border-t border-surface-container-low">
            <Link
              href={`/dashboard/pick/${pick.id}`}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high transition-colors text-on-surface text-[13px] font-semibold"
            >
              Ver análisis y recomendación
              <ChevronRight className="w-4 h-4 text-tertiary" />
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function SourcePill({ label, prob }: { label: string; prob: number }) {
  return (
    <div className="flex items-center gap-1.5 bg-surface px-2.5 py-1 rounded-full border border-surface-container-low">
      <span className="font-mono font-bold text-[10px] uppercase tracking-wider text-tertiary">
        {label}
      </span>
      <span className="font-mono font-bold text-[11px] text-on-surface">{probPercent(prob)}</span>
    </div>
  );
}

function LockedOverlay() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
        <Lock className="w-5 h-5 text-primary" />
      </div>
      <p className="font-sans font-bold text-[14px] text-on-surface mb-1">Pick premium</p>
      <p className="font-sans text-[12px] text-tertiary">Upgrade a Pro para desbloquear</p>
    </div>
  );
}
