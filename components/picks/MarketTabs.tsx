'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Pick } from '@/types';

type TabKey = '1x2' | 'ou' | 'btts' | 'dc' | 'corners';

const TAB_LABELS: Record<TabKey, string> = {
  '1x2': '1X2',
  ou: 'O/U',
  btts: 'BTTS',
  dc: 'DC',
  corners: 'Corners',
};

interface OutcomeRow {
  label: string;
  ml?: number;
  poly?: number;
  bk?: number;
  blended: number;
}

interface MarketTabsProps {
  pick: Pick;
  markets?: {
    ou_outcomes?: Array<{ outcome: string; label: string; our_prob_pct: number }>;
    dc_outcomes?: Array<{ outcome: string; label: string; our_prob_pct: number }>;
  };
  btts?: { btts_yes: number; btts_no: number };
  corners?: { expected_corners: number; over_9_5: number; under_9_5: number };
}

function ProbBar({
  label,
  value,
  colorClass = 'bg-indigo-500',
  max = 100,
}: {
  label: string;
  value: number;
  colorClass?: string;
  max?: number;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-3">
      <span className="font-sans text-[13px] text-zinc-300 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          className={`h-full rounded-full ${colorClass}`}
        />
      </div>
      <span className="font-mono text-[13px] font-bold text-white w-12 text-right">
        {value.toFixed(1)}%
      </span>
    </div>
  );
}

function SourceBlend({ ml, poly, bk }: { ml?: number; poly?: number; bk?: number }) {
  const pills = [
    { label: 'ML', value: ml },
    { label: 'Poly', value: poly },
    { label: 'BK', value: bk },
  ].filter((p) => p.value != null) as Array<{ label: string; value: number }>;

  if (pills.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {pills.map((p) => (
        <div
          key={p.label}
          className="flex items-center gap-1.5 bg-white/5 px-2.5 py-1 rounded-full border border-white/[0.06]"
        >
          <span className="font-mono font-bold text-[10px] uppercase tracking-wider text-zinc-500">
            {p.label}
          </span>
          <span className="font-mono font-bold text-[11px] text-zinc-300">
            {p.value.toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ---- Tab content components ----

function Tab1x2({ pick }: { pick: Pick }) {
  const outcomes: OutcomeRow[] = [
    {
      label: 'Local',
      ml: pick.mlProb.home != null ? pick.mlProb.home * 100 : undefined,
      poly: pick.polyProb?.home != null ? pick.polyProb.home * 100 : undefined,
      bk: pick.bkProb.home != null ? pick.bkProb.home * 100 : undefined,
      blended: (pick.blendedProb?.home ?? pick.mlProb.home ?? 0) * 100,
    },
    {
      label: 'Empate',
      ml: pick.mlProb.draw != null ? pick.mlProb.draw * 100 : undefined,
      poly: pick.polyProb?.draw != null ? pick.polyProb.draw * 100 : undefined,
      bk: pick.bkProb.draw != null ? pick.bkProb.draw * 100 : undefined,
      blended: (pick.blendedProb?.draw ?? pick.mlProb.draw ?? 0) * 100,
    },
    {
      label: 'Visitante',
      ml: pick.mlProb.away != null ? pick.mlProb.away * 100 : undefined,
      poly: pick.polyProb?.away != null ? pick.polyProb.away * 100 : undefined,
      bk: pick.bkProb.away != null ? pick.bkProb.away * 100 : undefined,
      blended: (pick.blendedProb?.away ?? pick.mlProb.away ?? 0) * 100,
    },
  ];

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        {outcomes.map((o) => (
          <div key={o.label} className="space-y-1.5">
            <ProbBar label={o.label} value={o.blended} colorClass="bg-indigo-500" />
            <SourceBlend ml={o.ml} poly={o.poly} bk={o.bk} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TabOU({
  markets,
}: {
  markets?: MarketTabsProps['markets'];
}) {
  const outcomes = markets?.ou_outcomes;

  if (!outcomes || outcomes.length === 0) {
    return (
      <p className="font-sans text-[13px] text-zinc-500 py-4">
        No hay datos de mercado O/U disponibles para este pick.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {outcomes.map((o) => (
        <ProbBar
          key={o.outcome}
          label={o.label}
          value={o.our_prob_pct}
          colorClass="bg-emerald-500"
        />
      ))}
    </div>
  );
}

function TabBTTS({ btts }: { btts?: MarketTabsProps['btts'] }) {
  if (!btts) {
    return (
      <p className="font-sans text-[13px] text-zinc-500 py-4">
        No hay datos de BTTS disponibles para este pick.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <ProbBar label="Ambos marcan" value={btts.btts_yes} colorClass="bg-emerald-500" />
      <ProbBar label="No ambos marcan" value={btts.btts_no} colorClass="bg-zinc-500" />
    </div>
  );
}

function TabDC({ markets }: { markets?: MarketTabsProps['markets'] }) {
  const outcomes = markets?.dc_outcomes;

  if (!outcomes || outcomes.length === 0) {
    return (
      <p className="font-sans text-[13px] text-zinc-500 py-4">
        No hay datos de doble oportunidad disponibles para este pick.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {outcomes.map((o) => (
        <ProbBar key={o.outcome} label={o.label} value={o.our_prob_pct} colorClass="bg-amber-500" />
      ))}
    </div>
  );
}

function TabCorners({ corners }: { corners?: MarketTabsProps['corners'] }) {
  if (!corners) {
    return (
      <p className="font-sans text-[13px] text-zinc-500 py-4">
        No hay datos de corners disponibles para este pick.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between py-2 border-b border-white/[0.06]">
        <span className="font-sans text-[13px] text-zinc-400">Corners esperados</span>
        <span className="font-mono text-[18px] font-bold text-white">
          {corners.expected_corners.toFixed(1)}
        </span>
      </div>
      <div className="space-y-3">
        <ProbBar
          label="Mas de 9.5"
          value={corners.over_9_5}
          colorClass="bg-indigo-500"
        />
        <ProbBar
          label="Menos de 9.5"
          value={corners.under_9_5}
          colorClass="bg-zinc-500"
        />
      </div>
    </div>
  );
}

export default function MarketTabs({ pick, markets, btts, corners }: MarketTabsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('1x2');

  const tabs: TabKey[] = ['1x2', 'ou', 'btts', 'dc', 'corners'];

  return (
    <div>
      {/* Tab bar */}
      <div className="flex border-b border-white/[0.06] overflow-x-auto scrollbar-hide">
        {tabs.map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`relative shrink-0 px-4 h-[40px] font-sans text-[13px] font-semibold transition-colors ${
                isActive ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {TAB_LABELS[tab]}
              {isActive && (
                <motion.span
                  layoutId="market-tab-indicator"
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-white rounded-full"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="pt-5">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
          >
            {activeTab === '1x2' && <Tab1x2 pick={pick} />}
            {activeTab === 'ou' && <TabOU markets={markets} />}
            {activeTab === 'btts' && <TabBTTS btts={btts} />}
            {activeTab === 'dc' && <TabDC markets={markets} />}
            {activeTab === 'corners' && <TabCorners corners={corners} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
