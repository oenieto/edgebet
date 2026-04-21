'use client';

import { CheckCircle2, Lock, Target } from 'lucide-react';
import type { Pick } from '@/types';

interface PickCardProps {
  pick: Pick;
  locked?: boolean;
}

const predictionLabel: Record<Pick['prediction'], string> = {
  home: 'Gana local',
  draw: 'Empate',
  away: 'Gana visitante',
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
  const mainProb =
    pick.prediction === 'home'
      ? pick.mlProb.home
      : pick.prediction === 'draw'
        ? pick.mlProb.draw
        : pick.mlProb.away;

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

      <div className="flex items-center justify-between mb-5">
        <div className="font-sans font-bold text-[18px] text-on-surface">{pick.homeTeam}</div>
        <span className="text-tertiary font-mono text-[11px]">vs</span>
        <div className="font-sans font-bold text-[18px] text-on-surface text-right">{pick.awayTeam}</div>
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
            <SourcePill label="ML" prob={mainProb} />
            {pick.polyProb && (
              <SourcePill
                label="Poly"
                prob={
                  pick.prediction === 'home'
                    ? pick.polyProb.home
                    : pick.prediction === 'draw'
                      ? pick.polyProb.draw
                      : pick.polyProb.away
                }
              />
            )}
            <SourcePill
              label="BK"
              prob={
                pick.prediction === 'home'
                  ? pick.bkProb.home
                  : pick.prediction === 'draw'
                    ? pick.bkProb.draw
                    : pick.bkProb.away
              }
            />
          </div>

          <div className="border-l-2 border-primary pl-3 mb-4">
            <p className="font-sans text-[13px] text-on-surface-variant leading-relaxed">
              {pick.aiReasoning}
            </p>
          </div>

          <div className="mt-auto pt-3 border-t border-surface-container-low flex items-center justify-between">
            <div className="flex items-center gap-2 text-tertiary">
              <CheckCircle2 className="w-4 h-4" />
              <span className="font-sans text-[12px]">Stake sugerido</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono font-bold text-[13px] text-on-surface">
                {pick.suggestedStake.toFixed(1)}%
              </span>
              {pick.odds != null && (
                <span className="font-mono font-bold text-[13px] text-secondary">
                  @{pick.odds.toFixed(2)}
                </span>
              )}
            </div>
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
