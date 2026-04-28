'use client';

import { Calendar, Gift, Lock, Percent, Sparkles, Star, Zap } from 'lucide-react';
import type { Reward, RewardKind } from '@/lib/ranking/rewards';
import { REWARDS } from '@/lib/ranking/rewards';
import { RANKS, type RankId } from '@/lib/ranking/tiers';

const ICONS: Record<RewardKind, JSX.Element> = {
  free_pick: <Gift className="w-4 h-4" />,
  discount: <Percent className="w-4 h-4" />,
  priority: <Zap className="w-4 h-4" />,
  event: <Calendar className="w-4 h-4" />,
  beta: <Sparkles className="w-4 h-4" />,
};

interface Props {
  currentRankId: RankId;
}

export default function RewardsList({ currentRankId }: Props) {
  const allIds = RANKS.map((r) => r.id);
  const currentIdx = allIds.indexOf(currentRankId);

  const items = REWARDS.map((r) => {
    const reqIdx = allIds.indexOf(r.rankRequired);
    const reqRank = RANKS.find((x) => x.id === r.rankRequired)!;
    const unlocked = reqIdx <= currentIdx;
    return { reward: r, reqRank, unlocked };
  });

  const unlockedCount = items.filter((i) => i.unlocked).length;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#111114] p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-sans font-bold text-[16px] text-white">Recompensas</h3>
          <p className="font-sans text-[12px] text-zinc-400 mt-0.5">
            {unlockedCount} de {items.length} desbloqueadas
          </p>
        </div>
        <Star className="w-4 h-4 text-amber-300" />
      </div>

      <ul className="flex flex-col gap-2">
        {items.map(({ reward, reqRank, unlocked }) => (
          <li
            key={reward.id}
            className={`flex items-start gap-3 rounded-xl border p-3 transition-colors ${
              unlocked
                ? 'border-white/[0.08] bg-white/[0.02]'
                : 'border-white/[0.04] bg-black/20 opacity-70'
            }`}
          >
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              style={{
                background: unlocked ? `${reqRank.color}22` : 'rgba(255,255,255,0.04)',
                color: unlocked ? reqRank.color : '#71717a',
              }}
            >
              {unlocked ? ICONS[reward.kind] : <Lock className="w-3.5 h-3.5" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-sans font-semibold text-[13px] text-white">
                  {reward.title}
                </span>
                <span
                  className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded"
                  style={{
                    background: `${reqRank.color}1a`,
                    color: reqRank.color,
                  }}
                >
                  {reqRank.name}
                </span>
              </div>
              <p className="font-sans text-[12px] text-zinc-400">{reward.description}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
