'use client';

import { Award } from 'lucide-react';
import type { Rank } from '@/lib/ranking/tiers';

interface Props {
  rank: Rank;
  size?: 'sm' | 'md' | 'lg';
}

export default function RankBadge({ rank, size = 'md' }: Props) {
  const dims = size === 'sm' ? 'h-6 px-2 text-[10px]' : size === 'lg' ? 'h-9 px-4 text-[13px]' : 'h-7 px-3 text-[11px]';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-sans font-bold uppercase tracking-widest ${dims}`}
      style={{
        background: `${rank.color}1f`,
        color: rank.color,
        border: `1px solid ${rank.color}33`,
      }}
    >
      <Award className="w-3.5 h-3.5" />
      {rank.name}
    </span>
  );
}
