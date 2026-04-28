'use client';

import React, { Fragment, useMemo, useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  Crown,
  Flame,
  Globe2,
  Lock,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
  Wallet,
} from 'lucide-react';

import LeagueRail from '@/components/shell/LeagueRail';
import BankrollTracker from '@/components/bankroll/BankrollTracker';
import SmartAlerts from '@/components/bankroll/SmartAlerts';
import RankCard from '@/components/profile/RankCard';
import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';
import { getLeagues, getMetrics, getPicksToday } from '@/lib/api/picks';
import type { LeagueInfo, Metrics, Pick } from '@/types';

export default function DashboardPage() {
  const { user } = useAuth();
  const { profile } = useUserStore();
  const xp = profile?.xp ?? 0;
  const userTier = (user?.tier ?? 'free') as 'free' | 'pro' | 'vip';

  const [selectedLeague, setSelectedLeague] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [pickFilter, setPickFilter] = useState<'all' | 'high_ev' | 'divergence' | 'vip' | 'premium'>('all');
  const [selectedWeek, setSelectedWeek] = useState<'this_week' | 'next_week'>('this_week');

  const { thisWeekEnd, nextWeekStart, nextWeekEnd } = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dayOfWeek = today.getDay();
    const daysUntilSunday = dayOfWeek === 0 ? 0 : 7 - dayOfWeek;
    const endThis = new Date(today);
    endThis.setDate(today.getDate() + daysUntilSunday);
    endThis.setHours(23, 59, 59, 999);
    const startNext = new Date(endThis);
    startNext.setDate(endThis.getDate() + 1);
    startNext.setHours(0, 0, 0, 0);
    const endNext = new Date(startNext);
    endNext.setDate(startNext.getDate() + 6);
    endNext.setHours(23, 59, 59, 999);
    return { thisWeekEnd: endThis, nextWeekStart: startNext, nextWeekEnd: endNext };
  }, []);

  const { data: picks, error: picksError, isLoading: picksLoading } = useSWR('picksToday', () => getPicksToday());
  const { data: metrics, error: metricsError, isLoading: metricsLoading } = useSWR('metrics', () => getMetrics());
  const { data: leaguesData, error: leaguesError, isLoading: leaguesLoading } = useSWR('leagues', () => getLeagues());
  
  const loading = picksLoading || metricsLoading || leaguesLoading;
  const fetchError = picksError || metricsError || leaguesError;
  const error = fetchError ? "No se pudo conectar al backend. Verifica el servidor local en /python." : null;
  const leagues = leaguesData || [];

  const countsBySlug = useMemo(() => {
    const map: Record<string, number> = {};
    if (picks) for (const p of picks) {
      const slug = p.leagueSlug ?? 'unknown';
      map[slug] = (map[slug] ?? 0) + 1;
    }
    return map;
  }, [picks]);

  const tierCounts = useMemo(() => {
    const res = { vip: 0, premium: 0, free: 0 };
    if (picks) for (const p of picks) res[p.status] += 1;
    return res;
  }, [picks]);

  const filteredPicks = useMemo(() => {
    if (!picks) return [];
    let out = picks;

    if (selectedWeek === 'this_week') {
      out = out.filter(p => {
        const d = new Date(p.kickoff);
        return d <= thisWeekEnd;
      });
    } else if (selectedWeek === 'next_week') {
      out = out.filter(p => {
        const d = new Date(p.kickoff);
        return d >= nextWeekStart && d <= nextWeekEnd;
      });
    }

    if (selectedLeague !== null) out = out.filter((p) => p.leagueSlug === selectedLeague);
    if (pickFilter === 'high_ev') out = out.filter((p) => (p.evPct ?? 0) >= 8);
    if (pickFilter === 'divergence') out = out.filter((p) => Math.abs(p.edgePp ?? 0) >= 5);
    if (pickFilter === 'vip') out = out.filter((p) => p.status === 'vip');
    if (pickFilter === 'premium') out = out.filter((p) => p.status === 'premium');
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      out = out.filter(
        (p) =>
          p.homeTeam.toLowerCase().includes(q) ||
          p.awayTeam.toLowerCase().includes(q) ||
          p.league.toLowerCase().includes(q),
      );
    }
    return out;
  }, [picks, selectedLeague, pickFilter, query, selectedWeek, thisWeekEnd, nextWeekStart, nextWeekEnd]);

  const topPick = useMemo(() => {
    if (!picks || picks.length === 0) return null;
    return picks[0];
  }, [picks]);

  const highlights = useMemo(() => buildHighlights(picks ?? []), [picks]);

  return (
    <div className="max-w-[1600px] mx-auto px-4 md:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-5">
        <LeagueRail
          leagues={leagues}
          selected={selectedLeague}
          onSelect={setSelectedLeague}
          counts={countsBySlug}
          topMetrics={{
            vipCount: tierCounts.vip,
            premiumCount: tierCounts.premium,
            totalPicks: picks?.length,
          }}
        />

        <section className="flex flex-col gap-5 min-w-0">
          <SmartAlerts />
          
          <RankCard xp={xp} />

          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-zinc-500 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="search"
              placeholder="Buscar equipo, liga, evento…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full h-[48px] pl-11 pr-4 rounded-xl bg-[#111114] border border-white/[0.06] font-sans text-[14px] text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20 focus:bg-[#16161a] transition-colors"
            />
          </div>

          {/* Chip row */}
          <div className="flex gap-2 overflow-x-auto scrollbar-hide -mx-1 px-1">
            <TypeChip
              active={pickFilter === 'all'}
              onClick={() => setPickFilter('all')}
              icon={<Sparkles className="w-3.5 h-3.5" />}
              label="Todos"
            />
            <TypeChip
              icon={<Crown className="w-3.5 h-3.5" />}
              label="Pick del día"
              accent="amber"
              href="/dashboard/pick-del-dia"
            />
            <TypeChip
              active={pickFilter === 'high_ev'}
              onClick={() => setPickFilter((v) => (v === 'high_ev' ? 'all' : 'high_ev'))}
              icon={<Flame className="w-3.5 h-3.5" />}
              label="Alto EV"
            />
            <TypeChip
              active={pickFilter === 'divergence'}
              onClick={() => setPickFilter((v) => (v === 'divergence' ? 'all' : 'divergence'))}
              icon={<Zap className="w-3.5 h-3.5" />}
              label="Divergencias"
            />
            <TypeChip
              active={pickFilter === 'vip'}
              onClick={() => setPickFilter((v) => (v === 'vip' ? 'all' : 'vip'))}
              icon={<Target className="w-3.5 h-3.5" />}
              label="VIP"
              accent="amber"
              count={tierCounts.vip}
            />
            <TypeChip
              active={pickFilter === 'premium'}
              onClick={() => setPickFilter((v) => (v === 'premium' ? 'all' : 'premium'))}
              icon={<TrendingUp className="w-3.5 h-3.5" />}
              label="Premium"
              count={tierCounts.premium}
            />
          </div>

          {/* 3 promo banners */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <PromoBannerCard
              label="Bienvenida"
              title="Hasta €40 en picks VIP gratis"
              caption="Primeros 7 días con todos los picks edge ≥ 8%."
              cta="Activar"
              href="/pricing"
              tone="neutral"
              badge={<Sparkles className="w-4 h-4" />}
            />
            <PromoBannerCard
              label="Exclusivo"
              title="Pick del día"
              caption="Un único pick curado · EV ≥ 12% · histórico 68% hit rate."
              cta={userTier === 'vip' ? 'Ver pick' : 'Desbloquear'}
              href={userTier === 'vip' ? '/dashboard/pick-del-dia' : '/pricing'}
              tone="amber"
              badge={<Crown className="w-4 h-4" />}
              locked={userTier !== 'vip'}
            />
            <PromoBannerCard
              label="Upgrade"
              title="Potencia tu bankroll"
              caption="Pro €19/mes · VIP €79/mes · Kelly + alertas Telegram."
              cta="Ver planes"
              href="/pricing"
              tone="white"
              badge={<TrendingUp className="w-4 h-4" />}
            />
          </div>

          {/* Metrics row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="md:col-span-2 lg:col-span-4">
              <BankrollTracker />
            </div>
          </div>
          <MetricsRow metrics={metrics ?? null} picksCount={picks?.length} tierCounts={tierCounts} />

          {/* Featured */}
          {highlights && !loading && !error && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-white/[0.06] text-white flex items-center justify-center">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <h2 className="font-sans font-bold text-[15px] text-white tracking-tight">
                    Destacados del día
                  </h2>
                </div>
                <Link
                  href="/dashboard/pick-del-dia"
                  className="font-sans text-[12px] font-semibold text-zinc-400 hover:text-white flex items-center gap-1"
                >
                  Ver más
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
                <HighlightCard
                  label="Mayor EV"
                  value={highlights.topEv ? `+${highlights.topEv.evPct?.toFixed(1)}%` : '—'}
                  sub={highlights.topEv ? highlights.topEv.match : '—'}
                  tier={highlights.topEv?.status}
                  locked={shouldLock(highlights.topEv?.status, userTier)}
                  valueTone="emerald"
                />
                <HighlightCard
                  label="Mayor confianza"
                  value={highlights.topConfidence ? `${highlights.topConfidence.confidence}%` : '—'}
                  sub={highlights.topConfidence ? highlights.topConfidence.match : '—'}
                  tier={highlights.topConfidence?.status}
                  locked={shouldLock(highlights.topConfidence?.status, userTier)}
                />
                <HighlightCard
                  label="Mejor Cuota"
                  value={
                    highlights.topEdge?.odds
                      ? `@${highlights.topEdge.odds.toFixed(2)}`
                      : '—'
                  }
                  sub={highlights.topEdge ? highlights.topEdge.match : '—'}
                  tier={highlights.topEdge?.status}
                  locked={shouldLock(highlights.topEdge?.status, userTier)}
                />
                <HighlightCard
                  label="Stake óptimo (Kelly)"
                  value={highlights.topStake ? `${highlights.topStake.suggestedStake.toFixed(1)}%` : '—'}
                  sub={highlights.topStake ? highlights.topStake.match : '—'}
                  tier={highlights.topStake?.status}
                  locked={shouldLock(highlights.topStake?.status, userTier)}
                />
              </div>
            </div>
          )}

          {/* Tabla */}
          <div className="bg-[#111114] border border-white/[0.06] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-end justify-between gap-4">
              <div>
                <h2 className="font-sans font-bold text-[16px] text-white tracking-tight flex items-center gap-2">
                  <CalendarDays className="w-4 h-4 text-zinc-400" />
                  {selectedLeague
                    ? leagues.find((l) => l.slug === selectedLeague)?.name
                    : 'Picks por Fecha'}
                </h2>
                <p className="font-sans text-[11.5px] text-zinc-500 mt-0.5">
                  {filteredPicks.length} partido{filteredPicks.length === 1 ? '' : 's'} · ordenados por EV
                </p>
              </div>
              {topPick && (
                <div className="hidden md:flex items-center gap-2 text-[11px] font-mono text-zinc-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  LIVE UPDATING
                </div>
              )}
            </div>

            <div className="border-b border-white/[0.06] bg-black/20">
              <div className="flex gap-2 px-5 py-3">
                <button
                  onClick={() => setSelectedWeek('this_week')}
                  className={`px-4 py-2 rounded-lg font-sans text-[12px] font-semibold transition-colors ${
                    selectedWeek === 'this_week'
                      ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                      : 'bg-white/[0.03] border border-white/[0.04] text-zinc-400 hover:text-white hover:border-white/[0.1]'
                  }`}
                >
                  Esta semana
                </button>
                <button
                  onClick={() => setSelectedWeek('next_week')}
                  className={`px-4 py-2 rounded-lg font-sans text-[12px] font-semibold transition-colors ${
                    selectedWeek === 'next_week'
                      ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                      : 'bg-white/[0.03] border border-white/[0.04] text-zinc-400 hover:text-white hover:border-white/[0.1]'
                  }`}
                >
                  Próxima semana
                </button>
              </div>
            </div>

            {loading && <TableSkeleton />}

            {error && !loading && (
              <div className="p-6 flex items-start gap-4 border-l-2 border-red-500 bg-red-500/5">
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-sans font-bold text-[13px] text-red-200 mb-1">Backend no disponible</p>
                  <p className="font-sans text-[12px] text-red-300/80 font-mono">{error}</p>
                </div>
              </div>
            )}

            {!loading && !error && filteredPicks.length === 0 && (
              <div className="p-10 text-center">
                <p className="font-sans text-[13px] text-zinc-500">
                  No hay picks para este filtro.
                </p>
              </div>
            )}

            {!loading && !error && filteredPicks.length > 0 && (
              <PicksTable picks={filteredPicks} userTier={userTier} />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function shouldLock(status: Pick['status'] | undefined, userTier: 'free' | 'pro' | 'vip'): boolean {
  if (!status) return false;
  if (userTier === 'vip') return false;
  if (userTier === 'pro') return status === 'vip';
  return status !== 'free';
}

function buildHighlights(picks: Pick[]) {
  if (!picks.length) return null;
  const topEv = [...picks].sort((a, b) => (b.evPct ?? 0) - (a.evPct ?? 0))[0];
  const topConfidence = [...picks].sort((a, b) => b.confidence - a.confidence)[0];
  const topEdge = [...picks].sort((a, b) => Math.abs(b.edgePp ?? 0) - Math.abs(a.edgePp ?? 0))[0];
  const topStake = [...picks].sort((a, b) => b.suggestedStake - a.suggestedStake)[0];
  return { topEv, topConfidence, topEdge, topStake };
}

// ========== sub-components ==========

function TypeChip({
  icon,
  label,
  active = false,
  accent = 'neutral',
  count,
  href,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  accent?: 'neutral' | 'amber';
  count?: number;
  href?: string;
  onClick?: () => void;
}) {
  const base =
    'shrink-0 h-[34px] px-3.5 rounded-md flex items-center gap-1.5 font-sans text-[12px] font-semibold transition-colors';
  const activeClass =
    accent === 'amber'
      ? 'bg-amber-500/15 border border-amber-500/30 text-amber-300'
      : 'bg-white text-[#0a0a0c] border border-white';
  const idleClass =
    'bg-[#111114] border border-white/[0.08] text-zinc-300 hover:border-white/20 hover:text-white';
  const className = `${base} ${active ? activeClass : idleClass}`;

  const content = (
    <>
      {icon}
      {label}
      {count != null && count > 0 && (
        <span
          className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
            active ? 'bg-black/10' : 'bg-white/5 text-zinc-400'
          }`}
        >
          {count}
        </span>
      )}
    </>
  );

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }
  return (
    <button type="button" className={className} onClick={onClick}>
      {content}
    </button>
  );
}

function PromoBannerCard({
  label,
  title,
  caption,
  cta,
  href,
  tone,
  badge,
  locked = false,
}: {
  label: string;
  title: string;
  caption: string;
  cta: string;
  href: string;
  tone: 'neutral' | 'amber' | 'white';
  badge: React.ReactNode;
  locked?: boolean;
}) {
  const toneMap = {
    neutral: {
      bg: 'from-white/[0.04] to-transparent border-white/[0.08]',
      pill: 'bg-white/[0.08] text-white',
      btn: 'bg-white text-[#0a0a0c] hover:bg-zinc-200',
    },
    amber: {
      bg: 'from-amber-500/15 to-transparent border-amber-500/20',
      pill: 'bg-amber-500/20 text-amber-300',
      btn: 'bg-amber-400 text-[#0a0a0c] hover:bg-amber-300',
    },
    white: {
      bg: 'from-white/[0.08] via-white/[0.04] to-transparent border-white/[0.12]',
      pill: 'bg-white/[0.1] text-white',
      btn: 'bg-white text-[#0a0a0c] hover:bg-zinc-200',
    },
  }[tone];

  return (
    <div
      className={`relative rounded-xl p-4 bg-gradient-to-br ${toneMap.bg} border overflow-hidden`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-7 h-7 rounded-lg ${toneMap.pill} flex items-center justify-center`}>
          {badge}
        </div>
        <span className="font-mono text-[9px] uppercase tracking-[0.2em] font-bold text-zinc-500">
          {label}
        </span>
        {locked && (
          <span className="ml-auto flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest text-amber-300">
            <Lock className="w-3 h-3" /> VIP
          </span>
        )}
      </div>
      <div className="font-sans font-bold text-[16px] text-white tracking-tight mb-1 leading-tight">
        {title}
      </div>
      <p className="font-sans text-[12px] text-zinc-400 mb-3 leading-snug">{caption}</p>
      <Link
        href={href}
        className={`inline-flex items-center gap-1.5 h-[32px] px-3.5 rounded-md font-sans font-bold text-[12px] transition-colors ${toneMap.btn}`}
      >
        {cta}
        <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  );
}

function MetricsRow({
  metrics,
  picksCount,
  tierCounts,
}: {
  metrics: Metrics | null;
  picksCount?: number;
  tierCounts: { vip: number; premium: number; free: number };
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <MetricCard
        label="Picks abiertos"
        value={picksCount != null ? String(picksCount) : '—'}
        sub={`VIP ${tierCounts.vip} · Prem ${tierCounts.premium}`}
      />
      <MetricCard
        label="Accuracy 30d"
        value={metrics ? `${(metrics.accuracy_30d * 100).toFixed(1)}%` : '—'}
        tone="emerald"
        sub="L30 auditado"
      />
      <MetricCard
        label="ROI mensual"
        value={metrics ? `+${(metrics.roi_monthly * 100).toFixed(1)}%` : '—'}
        tone="emerald"
        sub="vs bankroll inicial"
      />
      <MetricCard
        label="Divergencias"
        value={metrics ? String(metrics.active_divergences) : '—'}
        tone="white"
        sub="activas ahora"
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
  tone = 'white',
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: 'white' | 'emerald';
}) {
  const valueClass = tone === 'emerald' ? 'text-emerald-400' : 'text-white';
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl px-4 py-3">
      <div className="font-sans text-[11px] font-medium text-zinc-500 mb-1 uppercase tracking-wider">
        {label}
      </div>
      <div className={`font-mono font-bold text-[22px] leading-tight ${valueClass}`}>{value}</div>
      {sub && <div className="font-sans text-[10px] text-zinc-600 mt-1">{sub}</div>}
    </div>
  );
}

function HighlightCard({
  label,
  value,
  sub,
  tier,
  locked = false,
  valueTone = 'white',
}: {
  label: string;
  value: string;
  sub: string;
  tier?: Pick['status'];
  locked?: boolean;
  valueTone?: 'white' | 'emerald';
}) {
  const accentMap: Record<NonNullable<Pick['status']>, string> = {
    vip: 'text-amber-300',
    premium: 'text-zinc-300',
    free: 'text-zinc-500',
  };

  const valueClass = valueTone === 'emerald' ? 'text-emerald-400' : 'text-white';

  return (
    <div className="relative bg-[#111114] border border-white/[0.06] rounded-xl p-4 hover:border-white/[0.12] transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="font-sans text-[10px] uppercase tracking-widest font-bold text-zinc-500">
          {label}
        </span>
        {tier && (
          <span
            className={`font-mono text-[9px] uppercase tracking-wider font-bold ${accentMap[tier]}`}
          >
            {tier}
          </span>
        )}
      </div>
      <div className={`font-mono font-bold text-[24px] mb-1 ${locked ? 'blur-sm select-none text-white' : valueClass}`}>
        {locked ? '•••' : value}
      </div>
      <div className="font-sans text-[11px] text-zinc-500 truncate">
        {locked ? 'Requiere upgrade' : sub}
      </div>
      {locked && (
        <Link
          href="/pricing"
          className="absolute inset-0 flex items-center justify-center bg-[#111114]/40 backdrop-blur-[2px] rounded-xl"
        >
          <span className="flex items-center gap-1.5 px-3 h-[30px] rounded-md bg-amber-400 text-[#0a0a0c] font-sans font-bold text-[11px]">
            <Lock className="w-3 h-3" />
            Desbloquear
          </span>
        </Link>
      )}
    </div>
  );
}

function PicksTable({
  picks,
  userTier,
}: {
  picks: Pick[];
  userTier: 'free' | 'pro' | 'vip';
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { suggestedStake, isOnboardingDone } = useUserStore();
  const stakeValue = suggestedStake();

  // Agrupar por fecha local
  const groupedPicks = useMemo(() => {
    // Sort by kickoff date asc, then by EV desc
    const sorted = [...picks].sort((a, b) => {
      const timeDiff = new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
      if (timeDiff !== 0) return timeDiff;
      return (b.evPct ?? 0) - (a.evPct ?? 0);
    });

    const groups: { dateLabel: string; picks: Pick[] }[] = [];
    let currentLabel = '';

    for (const p of sorted) {
      const dateObj = new Date(p.kickoff);
      // Validar fecha por si acaso (fallback si no hay)
      if (isNaN(dateObj.getTime())) {
        if (!groups.length || groups[groups.length - 1].dateLabel !== 'Próximamente') {
            groups.push({ dateLabel: 'Próximamente', picks: [] });
        }
        groups[groups.length - 1].picks.push(p);
        continue;
      }

      // Ejemplo: "Sábado, 25 abr"
      let dateLabel = dateObj.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'short' });
      dateLabel = dateLabel.charAt(0).toUpperCase() + dateLabel.slice(1);

      if (dateLabel !== currentLabel) {
        currentLabel = dateLabel;
        groups.push({ dateLabel, picks: [] });
      }
      groups[groups.length - 1].picks.push(p);
    }
    return groups;
  }, [picks]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="text-[10px] uppercase tracking-widest font-sans font-bold text-zinc-500 bg-black/30">
            <th className="px-5 py-2.5 font-medium">Partido & Hora Local</th>
            <th className="px-3 py-2.5 font-medium hidden md:table-cell">Liga</th>
            <th className="px-3 py-2.5 font-medium text-right">Predicción</th>
            <th className="px-3 py-2.5 font-medium text-right hidden sm:table-cell">Confianza</th>
            <th className="px-3 py-2.5 font-medium text-right hidden md:table-cell">Edge</th>
            <th className="px-3 py-2.5 font-medium text-right">EV</th>
            <th className="px-3 py-2.5 font-medium text-right hidden lg:table-cell">Stake</th>
            <th className="px-5 py-2.5 font-medium text-right">Cuota</th>
          </tr>
        </thead>
        {groupedPicks.map((group) => (
          <tbody key={group.dateLabel}>
            <tr>
              <td colSpan={8} className="px-5 py-2 bg-[#16161a] border-y border-white/[0.04]">
                <div className="font-sans text-[11px] font-bold tracking-widest uppercase text-amber-500/80">
                  {group.dateLabel}
                </div>
              </td>
            </tr>
            {group.picks.map((p) => {
              const locked = shouldLock(p.status, userTier);
              const isExpanded = expandedId === p.id;
              const dateObj = new Date(p.kickoff);
              const timeStr = isNaN(dateObj.getTime()) ? '' : dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
              
              const predLabel =
              p.prediction === 'home'
                ? `${p.homeTeam} gana`
                : p.prediction === 'away'
                  ? `${p.awayTeam} gana`
                  : 'Empate';

              let stakeDisplay = '—';
              if (!locked) {
                if (isOnboardingDone()) {
                  stakeDisplay = `$${stakeValue.toFixed(2)}`;
                } else {
                  stakeDisplay = 'Configura bankroll';
                }
              }

            return (
              <Fragment key={p.id}>
              <tr
                onClick={() => { if (!locked) setExpandedId(isExpanded ? null : p.id) }}
                className={`border-t border-white/[0.04] transition-colors ${!locked ? 'cursor-pointer hover:bg-white/[0.02]' : ''}`}
              >
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2.5">
                    <TierDot status={p.status} />
                    <div>
                      <div className="font-sans font-semibold text-[13px] text-white">
                        {locked ? '••• vs •••' : `${p.homeTeam} vs ${p.awayTeam}`}
                      </div>
                      <div className="font-sans text-[11px] text-zinc-500 flex items-center gap-1.5">
                        <span className="font-mono text-amber-500/80">{timeStr}</span>
                        <span className="md:hidden">· {p.league}</span>
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-3 hidden md:table-cell">
                  <span className="font-sans text-[12px] text-zinc-400">{p.league}</span>
                </td>
                <td className="px-3 py-3 text-right">
                  {locked ? (
                    <span className="font-mono text-[11px] text-zinc-600">●●●</span>
                  ) : (
                    <span className="font-sans text-[12.5px] text-white font-medium">{predLabel}</span>
                  )}
                </td>
                <td className="px-3 py-3 text-right hidden sm:table-cell">
                  <span className="font-mono text-[12.5px] font-bold text-white">
                    {p.confidence}%
                  </span>
                </td>
                <td className="px-3 py-3 text-right hidden md:table-cell">
                  <span
                    className={`font-mono text-[12.5px] font-bold ${
                      (p.edgePp ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {(p.edgePp ?? 0) >= 0 ? '+' : ''}
                    {p.edgePp?.toFixed(1) ?? '—'}pp
                  </span>
                </td>
                <td className="px-3 py-3 text-right">
                  {locked ? (
                    <span className="font-mono text-[12.5px] text-zinc-600 blur-sm select-none">+99.9%</span>
                  ) : (
                    <span className="font-mono text-[12.5px] font-bold text-amber-300">
                      +{p.evPct?.toFixed(1) ?? '—'}%
                    </span>
                  )}
                </td>
                <td className="px-3 py-3 text-right hidden lg:table-cell">
                  <div className="font-mono text-[12.5px] font-semibold text-white">
                    {isOnboardingDone() || locked ? (
                      stakeDisplay
                    ) : (
                      <Link href="/onboarding" className="text-[10px] text-amber-400 hover:underline flex items-center gap-1 justify-end">
                        {stakeDisplay} <ArrowRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </td>
                <td className="px-5 py-3 text-right">
                  {locked ? (
                    <Link
                      href="/pricing"
                      className="inline-flex items-center gap-1 h-[30px] px-3 rounded-md bg-amber-400 text-[#0a0a0c] font-sans font-bold text-[11px] hover:bg-amber-300 transition-colors"
                    >
                      <Lock className="w-3 h-3" />
                      Desbloquear
                    </Link>
                  ) : (
                    <span className="inline-flex items-center h-[30px] px-3 rounded-md bg-white/[0.06] border border-white/[0.1] font-mono font-bold text-[13px] text-white">
                      {p.odds?.toFixed(2) ?? '—'}
                    </span>
                  )}
                </td>
              </tr>
              {isExpanded && !locked && (
                <tr className="bg-black/20 border-t border-white/[0.02]">
                  <td colSpan={8} className="px-5 py-4">
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                      <div className="font-sans text-[13px] text-zinc-300 leading-relaxed max-w-4xl">
                        <span className="text-white font-semibold mr-1">Análisis IA:</span>
                        {p.aiReasoning}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
              </Fragment>
            );
          })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function TierDot({ status }: { status: Pick['status'] }) {
  const cls =
    status === 'vip'
      ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]'
      : status === 'premium'
        ? 'bg-white'
        : 'bg-zinc-600';
  return <span className={`w-2 h-2 rounded-full ${cls}`} />;
}

function TableSkeleton() {
  return (
    <div className="p-5 space-y-2.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="h-12 bg-white/[0.03] rounded-lg animate-pulse"
        />
      ))}
    </div>
  );
}
