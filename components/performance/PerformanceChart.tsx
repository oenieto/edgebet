'use client';

import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, BarChart3, TrendingUp } from 'lucide-react';
import { getPerformance } from '@/lib/api/picks';
import type { PerformanceData } from '@/types';

type TabId = 'accuracy' | 'roi' | 'leagues';

export default function PerformanceChart() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('accuracy');
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    getPerformance(days)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <ChartSkeleton />;
  if (!data) return null;

  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="font-sans font-bold text-[16px] text-white tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            Rendimiento
          </h2>
          <p className="font-sans text-[11.5px] text-zinc-500 mt-0.5">
            {data.summary.total_picks} picks resueltos en {data.period_days} dias
          </p>
        </div>

        {/* Period selector */}
        <div className="flex gap-1.5">
          {[7, 14, 30, 60].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDays(d)}
              className={`h-[28px] px-2.5 rounded-md font-mono text-[11px] font-bold transition-colors ${
                days === d
                  ? 'bg-white text-[#0a0a0c]'
                  : 'bg-white/[0.04] text-zinc-400 hover:text-white hover:bg-white/[0.08]'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/[0.04]">
        <SummaryCell
          label="Accuracy promedio"
          value={`${(data.summary.avg_accuracy * 100).toFixed(1)}%`}
          tone="emerald"
        />
        <SummaryCell
          label="ROI acumulado"
          value={`+${(data.summary.total_roi * 100).toFixed(1)}%`}
          tone="emerald"
        />
        <SummaryCell
          label="Mejor dia"
          value={formatShortDate(data.summary.best_day)}
          tone="white"
        />
        <SummaryCell
          label="Peor dia"
          value={formatShortDate(data.summary.worst_day)}
          tone="white"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-white/[0.06]">
        <TabButton
          id="accuracy"
          active={activeTab}
          onClick={setActiveTab}
          icon={<Activity className="w-3.5 h-3.5" />}
          label="Accuracy"
        />
        <TabButton
          id="roi"
          active={activeTab}
          onClick={setActiveTab}
          icon={<TrendingUp className="w-3.5 h-3.5" />}
          label="ROI"
        />
        <TabButton
          id="leagues"
          active={activeTab}
          onClick={setActiveTab}
          icon={<BarChart3 className="w-3.5 h-3.5" />}
          label="Por liga"
        />
      </div>

      {/* Chart area */}
      <div className="p-5">
        {activeTab === 'accuracy' && <AccuracyChart series={data.accuracy_series} />}
        {activeTab === 'roi' && <RoiChart series={data.roi_series} />}
        {activeTab === 'leagues' && <LeagueChart breakdown={data.league_breakdown} />}
      </div>
    </div>
  );
}

function AccuracyChart({ series }: { series: PerformanceData['accuracy_series'] }) {
  const chartData = series.map((p) => ({
    date: formatShortDate(p.date),
    accuracy: +(p.accuracy * 100).toFixed(1),
    picks: p.picks_resolved,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[45, 80]}
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip content={<AccTooltip />} />
        <Area
          type="monotone"
          dataKey="accuracy"
          stroke="#34d399"
          strokeWidth={2}
          fill="url(#accGrad)"
          dot={false}
          activeDot={{ r: 4, fill: '#34d399', stroke: '#111114', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function RoiChart({ series }: { series: PerformanceData['roi_series'] }) {
  const chartData = series.map((p) => ({
    date: formatShortDate(p.date),
    roi: +(p.cumulative_roi * 100).toFixed(2),
    daily: +(p.daily_roi * 100).toFixed(2),
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="roiGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip content={<RoiTooltip />} />
        <Area
          type="monotone"
          dataKey="roi"
          stroke="#fbbf24"
          strokeWidth={2}
          fill="url(#roiGrad)"
          dot={false}
          activeDot={{ r: 4, fill: '#fbbf24', stroke: '#111114', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function LeagueChart({ breakdown }: { breakdown: PerformanceData['league_breakdown'] }) {
  const chartData = breakdown.map((l) => ({
    name: l.name.replace('League', '').trim(),
    accuracy: +(l.accuracy * 100).toFixed(1),
    picks: l.picks_resolved,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'sans-serif' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[50, 70]}
          tick={{ fontSize: 10, fill: '#71717a', fontFamily: 'JetBrains Mono, monospace' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip content={<LeagueTooltip />} />
        <Bar dataKey="accuracy" fill="#6366f1" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Tooltips
function AccTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#1a1a1f] border border-white/[0.1] rounded-lg px-3 py-2 shadow-xl">
      <p className="font-mono text-[10px] text-zinc-400 mb-1">{d.date}</p>
      <p className="font-mono font-bold text-[13px] text-emerald-400">{d.accuracy}%</p>
      <p className="font-sans text-[10px] text-zinc-500">{d.picks} picks resueltos</p>
    </div>
  );
}

function RoiTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#1a1a1f] border border-white/[0.1] rounded-lg px-3 py-2 shadow-xl">
      <p className="font-mono text-[10px] text-zinc-400 mb-1">{d.date}</p>
      <p className="font-mono font-bold text-[13px] text-amber-300">+{d.roi}% acum.</p>
      <p className="font-sans text-[10px] text-zinc-500">+{d.daily}% hoy</p>
    </div>
  );
}

function LeagueTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#1a1a1f] border border-white/[0.1] rounded-lg px-3 py-2 shadow-xl">
      <p className="font-sans text-[11px] text-white font-semibold mb-1">{d.name}</p>
      <p className="font-mono font-bold text-[13px] text-indigo-400">{d.accuracy}%</p>
      <p className="font-sans text-[10px] text-zinc-500">{d.picks} picks</p>
    </div>
  );
}

// Sub-components
function SummaryCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'emerald' | 'white';
}) {
  const valueClass = tone === 'emerald' ? 'text-emerald-400' : 'text-white';
  return (
    <div className="bg-[#111114] px-4 py-3">
      <div className="font-sans text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className={`font-mono font-bold text-[18px] ${valueClass}`}>{value}</div>
    </div>
  );
}

function TabButton({
  id,
  active,
  onClick,
  icon,
  label,
}: {
  id: TabId;
  active: TabId;
  onClick: (id: TabId) => void;
  icon: React.ReactNode;
  label: string;
}) {
  const isActive = active === id;
  return (
    <button
      type="button"
      onClick={() => onClick(id)}
      className={`flex items-center gap-1.5 px-4 py-2.5 font-sans text-[12px] font-semibold transition-colors border-b-2 ${
        isActive
          ? 'text-white border-white'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function ChartSkeleton() {
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-5">
      <div className="h-5 w-32 bg-white/[0.04] rounded animate-pulse mb-4" />
      <div className="h-[240px] bg-white/[0.02] rounded-lg animate-pulse" />
    </div>
  );
}

function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  } catch {
    return iso;
  }
}
