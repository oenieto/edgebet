'use client';

import React, { Fragment, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Crown,
  Flame,
  Globe2,
  Lock,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
  LayoutGrid,
  List,
} from 'lucide-react';

import { getTeamFlag } from '@/lib/team-flags';

import LeagueRail from '@/components/shell/LeagueRail';
import BankrollWidget from '@/components/bankroll/BankrollWidget';
import SmartAlerts from '@/components/bankroll/SmartAlerts';
import PerformanceChart from '@/components/performance/PerformanceChart';
import OddsSparkline from '@/components/picks/OddsSparkline';
import TeamLogo from '@/components/picks/TeamLogo';
import PicksEmptyState from '@/components/picks/PicksEmptyState';
import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';
import { getLeagues, getMetrics, getPicksToday } from '@/lib/api/picks';
import { selectSafePick, type SelectedMarket } from '@/lib/picks/safe-pick';
import type { LeagueInfo, Metrics, Pick } from '@/types';

export default function DashboardPage() {
  const { user } = useAuth();
  const userTier = (user?.tier ?? 'free') as 'free' | 'pro' | 'vip';

  const [picks, setPicks] = useState<Pick[] | null>(null);
  const [leagues, setLeagues] = useState<LeagueInfo[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  useEffect(() => {
    const saved = localStorage.getItem('edgebet_picks_view');
    if (saved === 'grid' || saved === 'list') {
      setViewMode(saved);
    }
  }, []);

  const handleViewChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    localStorage.setItem('edgebet_picks_view', mode);
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([getPicksToday(), getMetrics(), getLeagues()])
      .then(([picksResult, metricsResult, leaguesResult]) => {
        if (cancelled) return;
        setPicks(picksResult);
        setMetrics(metricsResult);
        setLeagues(leaguesResult);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        console.error('API fetch failed', err);
        setError(
          'No se pudo conectar al backend. Arranca FastAPI con `uvicorn api.main:app --reload` desde /python.',
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
    if (selectedLeague !== null) out = out.filter((p) => p.leagueSlug === selectedLeague);
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
  }, [picks, selectedLeague, query]);

  const topPick = useMemo(() => {
    if (!picks || picks.length === 0) return null;
    return picks[0];
  }, [picks]);

  const highlights = useMemo(() => buildHighlights(picks ?? []), [picks]);

  // Mejor pick de hoy: mayor EV (priorizando market-verified).
  const bestPick = useMemo(() => {
    const pool = picks ?? [];
    if (pool.length === 0) return null;
    return [...pool].sort((a, b) => {
      const va = (a.marketVerified ? 1000 : 0) + (a.evPct ?? -999);
      const vb = (b.marketVerified ? 1000 : 0) + (b.evPct ?? -999);
      return vb - va;
    })[0];
  }, [picks]);

  // Próximos partidos del Mundial (para el strip).
  const wcPicks = useMemo(
    () =>
      (picks ?? [])
        .filter((p) => p.leagueSlug === 'fifa-world-cup')
        .sort((a, b) => (a.kickoff || '').localeCompare(b.kickoff || ''))
        .slice(0, 3),
    [picks],
  );

  // Ventana del Mundial 2026 (11 jun – 19 jul).
  const inWcWindow = useMemo(() => {
    const now = new Date();
    return now >= new Date('2026-06-11') && now <= new Date('2026-07-20');
  }, []);

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

        <section className="flex flex-col gap-8 min-w-0">
          {/* SECCIÓN 1 — Mejor pick de hoy */}
          <div>
            <SectionLabel>Mejor pick de hoy</SectionLabel>
            <HeroBestPick pick={bestPick} loading={loading} />
          </div>

          {/* SECCIÓN 2 — Bankroll (widget compacto, una sola fila) */}
          <div>
            <SectionLabel>Bankroll</SectionLabel>
            <BankrollWidget />
          </div>

          {/* SECCIÓN 3 — Picks del día (grid compacto / lista horizontal) */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-4">
                <SectionLabel>Picks del día</SectionLabel>
              </div>
              <div className="flex items-center gap-3">
                <div className="bg-[#111114] border border-white/[0.08] p-0.5 rounded-lg flex items-center gap-0.5">
                  <button
                    onClick={() => handleViewChange('grid')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      viewMode === 'grid'
                        ? 'bg-white text-black'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    <LayoutGrid className="w-3.5 h-3.5" />
                    <span>Grid</span>
                  </button>
                  <button
                    onClick={() => handleViewChange('list')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      viewMode === 'list'
                        ? 'bg-white text-black'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    <List className="w-3.5 h-3.5" />
                    <span>Lista</span>
                  </button>
                </div>
                {filteredPicks.length > 6 && (
                  <Link href="/dashboard/historial" className="text-[12px] font-semibold text-zinc-400 hover:text-white flex items-center gap-1">
                    Ver todos <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            </div>
            {loading ? (
              viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-[120px] rounded-xl bg-white/[0.04] animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-[72px] rounded-xl bg-white/[0.04] animate-pulse" />
                  ))}
                </div>
              )
            ) : error ? (
              <PicksEmptyState variant="error" description={error} ctaHref="/dashboard" ctaLabel="Reintentar" />
            ) : filteredPicks.length === 0 ? (
              <PicksEmptyState variant={picks && picks.length === 0 ? 'searching' : 'no-results'} />
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredPicks.slice(0, 9).map((p) => (
                  <CompactPickCard key={p.id} pick={p} />
                ))}
              </div>
            ) : (
              <div className="flex flex-col rounded-xl overflow-hidden border border-white/[0.06]">
                {filteredPicks.slice(0, 9).map((p) => (
                  <ListPickRow key={p.id} pick={p} />
                ))}
              </div>
            )}
          </div>

          {/* SECCIÓN 4 — Mundial 2026 (strip, solo durante la ventana) */}
          {inWcWindow && <WorldCupStrip picks={wcPicks} />}
        </section>
      </div>
    </div>
  );
}

const MARKET_DISPLAY_LABEL: Record<SelectedMarket, string | null> = {
  ML: null,
  DC: '2da oport.',
  OU: 'Goles',
  BTTS: 'BTTS',
  SPREAD: 'Hándicap',
  TEAM_TOTALS: 'Goles equipo',
};

const MARKET_DISPLAY_COLOR: Record<SelectedMarket, string | null> = {
  ML: null,
  DC: 'text-purple-300 border-purple-400/30 bg-purple-400/10',
  OU: 'text-sky-300 border-sky-400/30 bg-sky-400/10',
  BTTS: 'text-pink-300 border-pink-400/30 bg-pink-400/10',
  SPREAD: 'text-orange-300 border-orange-400/30 bg-orange-400/10',
  TEAM_TOTALS: 'text-teal-300 border-teal-400/30 bg-teal-400/10',
};

function shouldLock(status: Pick['status'] | undefined, userTier: 'free' | 'pro' | 'vip'): boolean {
  if (!status) return false;
  if (userTier === 'vip') return false;
  if (userTier === 'pro') return status === 'vip';
  return status !== 'free';
}

/**
 * Generate synthetic 24h odds history for a pick.
 * Deterministic based on pick id so sparklines are stable across renders.
 * Will be replaced by real odds_history data once Mauricio's pipeline is live.
 */
function generateOddsHistory(currentOdds: number, pickId: string): number[] {
  let seed = 0;
  for (let i = 0; i < pickId.length; i++) seed += pickId.charCodeAt(i);
  const points: number[] = [];
  let val = currentOdds + (seed % 10 - 5) * 0.02;
  for (let i = 0; i < 12; i++) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    const delta = ((seed % 100) - 50) * 0.003;
    val = Math.max(1.05, val + delta);
    points.push(+val.toFixed(3));
  }
  points.push(currentOdds);
  return points;
}

function buildHighlights(picks: Pick[]) {
  if (!picks.length) return null;
  // Solo considerar picks con mercado verificado para Mayor EV / Mejor Edge,
  // si no son ruido del modelo vs cuotas sintéticas. Confianza y stake sí
  // aplican a todos porque solo dependen de nuestra probabilidad.
  const verified = picks.filter((p) => p.marketVerified);
  const topEv = verified.length
    ? [...verified].sort((a, b) => (b.evPct ?? 0) - (a.evPct ?? 0))[0]
    : undefined;
  const topConfidence = [...picks].sort((a, b) => b.confidence - a.confidence)[0];
  const topEdge = verified.length
    ? [...verified].sort((a, b) => Math.abs(b.edgePp ?? 0) - Math.abs(a.edgePp ?? 0))[0]
    : undefined;
  const topStake = verified.length
    ? [...verified].sort((a, b) => b.suggestedStake - a.suggestedStake)[0]
    : undefined;
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
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  accent?: 'neutral' | 'amber';
  count?: number;
  href?: string;
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
    <button type="button" className={className}>
      {content}
    </button>
  );
}

function PromoBanners({ userTier }: { userTier: 'free' | 'pro' | 'vip' }) {
  // Cada tier ve banners útiles para SU estado actual. Nunca le mostramos
  // pitches de upgrade a quien ya está en el plan más alto, y nunca le
  // mostramos "Activar bienvenida" a quien ya tiene cuenta activa.
  if (userTier === 'vip') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <PromoBannerCard
          label="Tu pick del día"
          title="Pick exclusivo VIP de hoy"
          caption="EV mínimo +8%, alta convicción de las 3 fuentes."
          cta="Ver pick"
          href="/dashboard/pick-del-dia"
          tone="amber"
          badge={<Crown className="w-4 h-4" />}
        />
        <PromoBannerCard
          label="Gestión"
          title="Bankroll y alertas"
          caption="Configura Kelly, límites diarios/semanales y alertas Telegram."
          cta="Configurar"
          href="/dashboard/profile"
          tone="white"
          badge={<TrendingUp className="w-4 h-4" />}
        />
      </div>
    );
  }

  if (userTier === 'pro') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <PromoBannerCard
          label="Tu pick del día"
          title="Bloqueado — exclusivo VIP"
          caption="Edge ≥ 12% con consenso de las 3 fuentes. Disponible solo para VIP."
          cta="Subir a VIP"
          href="/pricing"
          tone="amber"
          badge={<Crown className="w-4 h-4" />}
          locked
        />
        <PromoBannerCard
          label="Gestión"
          title="Bankroll y alertas"
          caption="Configura Kelly, límites diarios y alertas Telegram."
          cta="Configurar"
          href="/dashboard/profile"
          tone="white"
          badge={<TrendingUp className="w-4 h-4" />}
        />
      </div>
    );
  }

  // free
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <PromoBannerCard
        label="Cuenta gratis"
        title="2–3 picks por semana"
        caption="Acceso a picks marcados como Free. El motor analiza igual, solo limitamos volumen."
        cta="Ver planes"
        href="/pricing"
        tone="neutral"
        badge={<Sparkles className="w-4 h-4" />}
      />
      <PromoBannerCard
        label="Pick del día"
        title="Bloqueado para Free"
        caption="Un pick curado por día con edge ≥ 12%. Solo VIP."
        cta="Desbloquear"
        href="/pricing"
        tone="amber"
        badge={<Crown className="w-4 h-4" />}
        locked
      />
      <PromoBannerCard
        label="Upgrade"
        title="Potencia tu bankroll"
        caption="Pro $19/mes desbloquea picks Premium + tracking Kelly + alertas."
        cta="Ver planes"
        href="/pricing"
        tone="white"
        badge={<TrendingUp className="w-4 h-4" />}
      />
    </div>
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
        value={
          metrics?.accuracy_30d != null
            ? `${(metrics.accuracy_30d * 100).toFixed(1)}%`
            : '—'
        }
        tone={metrics?.accuracy_30d != null ? 'emerald' : 'white'}
        sub={metrics?.accuracy_30d != null ? 'L30 auditado' : 'Sin histórico aún'}
      />
      <MetricCard
        label="ROI mensual"
        value={
          metrics?.roi_monthly != null
            ? `${metrics.roi_monthly >= 0 ? '+' : ''}${(metrics.roi_monthly * 100).toFixed(1)}%`
            : '—'
        }
        tone={metrics?.roi_monthly != null ? 'emerald' : 'white'}
        sub={metrics?.roi_monthly != null ? 'vs bankroll inicial' : 'Sin histórico aún'}
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
  const router = useRouter();
  // Suscripción reactiva a Zustand: cuando el user cambia bankroll o stake_pct
  // en /onboarding o /perfil, esta tabla se re-renderiza automáticamente y
  // los valores Kelly por pick se recalculan al instante.
  const { profile, isOnboardingDone } = useUserStore();
  const bankroll = profile?.bankroll ?? 0;

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
            <th className="px-2 py-2.5 font-medium text-center hidden lg:table-cell">Odds 24h</th>
            <th className="px-3 py-2.5 font-medium text-right hidden lg:table-cell">Stake</th>
            <th className="px-5 py-2.5 font-medium text-right">Cuota</th>
          </tr>
        </thead>
        {groupedPicks.map((group) => (
          <tbody key={group.dateLabel}>
            <tr>
              <td colSpan={9} className="px-5 py-2 bg-[#16161a] border-y border-white/[0.04]">
                <div className="font-sans text-[11px] font-bold tracking-widest uppercase text-amber-500/80">
                  {group.dateLabel}
                </div>
              </td>
            </tr>
            {group.picks.map((p) => {
              const locked = shouldLock(p.status, userTier);
              const dateObj = new Date(p.kickoff);
              const timeStr = isNaN(dateObj.getTime()) ? '' : dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

              // El pick mostrado se ajusta al perfil de riesgo del usuario:
              // conservative → DC/Under más alto · balanced → 1X2 motor · aggressive → EV+/Over
              const userRiskProfile = profile?.risk_profile ?? 'balanced';
              const safePick = selectSafePick(p, userRiskProfile);
              const predLabel = safePick.label;
              const safeProbability = Math.round(safePick.probability);

              const marketLabel = MARKET_DISPLAY_LABEL[safePick.market];
              const marketColor = MARKET_DISPLAY_COLOR[safePick.market];

              // Kelly real por pick: backend devuelve suggestedStake como % del bankroll.
              // Se multiplica por el bankroll actual del usuario → cantidad en USD reactiva.
              const kellyDollars = bankroll > 0 ? (p.suggestedStake / 100) * bankroll : 0;
              let stakeDisplay = '—';
              if (!locked) {
                if (isOnboardingDone()) {
                  stakeDisplay = kellyDollars > 0
                    ? `$${kellyDollars.toFixed(2)}`
                    : `${p.suggestedStake.toFixed(1)}%`;
                } else {
                  stakeDisplay = 'Configura bankroll';
                }
              }

            return (
              <Fragment key={p.id}>
              <tr
                onClick={() => { if (!locked) router.push(`/dashboard/pick/${p.id}`) }}
                className={`border-t border-white/[0.04] transition-colors ${!locked ? 'cursor-pointer hover:bg-white/[0.02]' : ''}`}
              >
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <TierDot status={p.status} />
                    {locked ? (
                      <div>
                        <div className="font-sans font-semibold text-[13px] text-zinc-500">••• vs •••</div>
                        <div className="font-sans text-[11px] text-zinc-600 mt-0.5">{timeStr}</div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col items-center gap-1 min-w-[44px]">
                          <TeamLogo src={(p as any).homeLogo} name={p.homeTeam} size={26} />
                          <span className="font-sans text-[9.5px] text-zinc-400 text-center truncate max-w-[48px]">{p.homeTeam}</span>
                        </div>
                        <div className="flex flex-col items-center">
                          <span className="font-mono text-[10px] text-zinc-600">{timeStr}</span>
                          <span className="font-mono text-[11px] font-bold text-zinc-500">vs</span>
                        </div>
                        <div className="flex flex-col items-center gap-1 min-w-[44px]">
                          <TeamLogo src={(p as any).awayLogo} name={p.awayTeam} size={26} />
                          <span className="font-sans text-[9.5px] text-zinc-400 text-center truncate max-w-[48px]">{p.awayTeam}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 hidden md:table-cell">
                  <div className="flex items-center gap-2">
                    {p.leagueLogo && (
                      <img src={p.leagueLogo} alt={p.league} className="w-5 h-5 object-contain" />
                    )}
                    <span className="font-sans text-[12px] text-zinc-400">{p.league}</span>
                  </div>
                </td>
                <td className="px-3 py-3 text-right">
                  {locked ? (
                    <span className="font-mono text-[11px] text-zinc-600">●●●</span>
                  ) : (
                    <div className="flex flex-col items-end gap-1">
                      {marketLabel && marketColor && (
                        <span className={`inline-flex items-center h-[16px] px-1.5 rounded border font-mono font-bold text-[8px] tracking-wide ${marketColor}`}>
                          {marketLabel}
                        </span>
                      )}
                      <span className="font-sans text-[12px] text-white font-medium text-right leading-tight">{predLabel}</span>
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 text-right hidden sm:table-cell">
                  <span className="font-mono text-[12.5px] font-bold text-white">
                    {safeProbability}%
                  </span>
                </td>
                <td className="px-3 py-3 text-right hidden md:table-cell">
                  {p.marketVerified && p.edgePp != null ? (
                    <span
                      className={`font-mono text-[12.5px] font-bold ${
                        p.edgePp >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {p.edgePp >= 0 ? '+' : ''}
                      {p.edgePp.toFixed(1)}pp
                    </span>
                  ) : (
                    <span className="font-mono text-[11px] text-zinc-600" title="Sin línea de mercado verificada">
                      —
                    </span>
                  )}
                </td>
                <td className="px-3 py-3 text-right">
                  {locked ? (
                    <span className="font-mono text-[12.5px] text-zinc-600 blur-sm select-none">+99.9%</span>
                  ) : p.marketVerified && p.evPct != null ? (
                    <span className={`font-mono text-[12.5px] font-bold ${p.evPct >= 0 ? 'text-amber-300' : 'text-zinc-500'}`}>
                      {p.evPct >= 0 ? '+' : ''}
                      {p.evPct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="font-mono text-[11px] text-zinc-600" title="Sin línea de mercado verificada">
                      —
                    </span>
                  )}
                </td>
                <td className="px-2 py-3 hidden lg:table-cell">
                  <div className="flex justify-center">
                    <OddsSparkline data={generateOddsHistory(p.odds ?? 1.9, p.id)} />
                  </div>
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
                  ) : p.marketVerified && p.odds != null ? (
                    <span className="inline-flex items-center h-[30px] px-3 rounded-md bg-white/[0.06] border border-white/[0.1] font-mono font-bold text-[13px] text-white">
                      {p.odds.toFixed(2)}
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center h-[30px] px-3 rounded-md bg-white/[0.02] border border-dashed border-white/[0.08] font-mono text-[11px] text-zinc-500"
                      title="No hay cuota de mercado verificada. Pick informativo del modelo."
                    >
                      sin línea
                    </span>
                  )}
                </td>
              </tr>
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

// ───────────────────────────────────────────────────────────────────────────
// Componentes del dashboard simplificado (Phase 2)
// ───────────────────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-500 mb-2">
      {children}
    </div>
  );
}

function predictionLabel(p: Pick): string {
  if (p.prediction === 'home') return p.homeTeam;
  if (p.prediction === 'away') return p.awayTeam;
  if (p.prediction === 'draw') return 'Empate';
  return p.prediction;
}

function renderTournamentBadge(league: string, isList: boolean = false) {
  let icon = '⚽';
  let label = league;
  let pillClass = 'bg-[#111114] text-zinc-400 border-white/[0.08]';

  if (league === 'FIFA World Cup 2026') {
    icon = '🏆';
    label = 'World Cup 2026';
    pillClass = 'bg-amber-500/10 text-amber-300 border-amber-500/20';
  } else if (league === 'Premier League') {
    icon = '🏴';
    label = 'Premier League';
    pillClass = 'bg-purple-500/10 text-purple-300 border-purple-500/20';
  } else if (league === 'La Liga') {
    icon = '🇪🇸';
    label = 'La Liga';
    pillClass = 'bg-orange-500/10 text-orange-300 border-orange-500/20';
  } else if (league === 'Liga MX') {
    icon = '🇲🇽';
    label = 'Liga MX';
    pillClass = 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
  } else if (league === 'Bundesliga') {
    icon = '🇩🇪';
    label = 'Bundesliga';
    pillClass = 'bg-red-500/10 text-red-300 border-red-500/20';
  } else if (league === 'Serie A') {
    icon = '🇮🇹';
    label = 'Serie A';
    pillClass = 'bg-blue-500/10 text-blue-300 border-blue-500/20';
  } else if (league === 'Ligue 1') {
    icon = '🇫🇷';
    label = 'Ligue 1';
    pillClass = 'bg-teal-500/10 text-teal-300 border-teal-500/20';
  } else if (league === 'UEFA Champions League') {
    icon = '⭐';
    label = 'Champions';
    pillClass = 'bg-blue-950/40 text-blue-300 border-blue-800/30';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-medium leading-none ${pillClass}`}>
      <span>{icon}</span>
      <span className={isList ? 'hidden sm:inline' : ''}>{label}</span>
    </span>
  );
}

function ListPickRow({ pick }: { pick: Pick }) {
  const seguro = (pick.confidence ?? 0) >= 60 || pick.marketVerified;
  const ev = pick.evPct;
  const homeFlag = getTeamFlag(pick.homeTeam);
  const awayFlag = getTeamFlag(pick.awayTeam);

  return (
    <Link
      href={`/dashboard/pick/${pick.id}`}
      className="flex items-center justify-between gap-4 h-[72px] px-4 border-b border-white/[0.04] bg-[#111114] hover:bg-white/[0.02] transition-colors"
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex-shrink-0">
          {renderTournamentBadge(pick.league, true)}
        </div>
        <div className="font-sans font-semibold text-white text-[14px] sm:text-[15px] truncate flex items-center gap-x-1">
          <span className="inline-flex items-center gap-1">
            {homeFlag && <span className="text-[1.15em] leading-none">{homeFlag}</span>}
            <span>{pick.homeTeam}</span>
          </span>
          <span className="text-zinc-500 font-normal text-xs mx-1">vs</span>
          <span className="inline-flex items-center gap-1">
            {awayFlag && <span className="text-[1.15em] leading-none">{awayFlag}</span>}
            <span>{pick.awayTeam}</span>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0">
        <div className="hidden sm:block bg-white/[0.04] px-2.5 py-1 rounded-md border border-white/[0.06]">
          <span className="text-[11px] text-zinc-400 font-medium">{predictionLabel(pick)}</span>
        </div>

        {ev !== null && ev !== 0 && (
          <span className="text-[12px] font-mono font-bold" style={{ color: ev > 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
            {ev > 0 ? '+' : ''}{ev.toFixed(1)}% EV
          </span>
        )}

        <span
          className="text-[9px] sm:text-[10px] font-semibold rounded-full px-2 py-0.5"
          style={
            seguro
              ? { backgroundColor: 'color-mix(in srgb, var(--color-success) 15%, transparent)', color: 'var(--color-success)' }
              : { backgroundColor: 'color-mix(in srgb, var(--color-warning) 15%, transparent)', color: 'var(--color-warning)' }
          }
        >
          {seguro ? 'SEGURO' : 'RIESGO'}
        </span>

        <span className="text-zinc-500 group-hover:text-white flex items-center gap-0.5 text-[12px] font-semibold">
          <span className="hidden sm:inline">Ver</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </Link>
  );
}

function HeroBestPick({ pick, loading }: { pick: Pick | null; loading: boolean }) {
  if (loading) {
    return <div className="h-[120px] rounded-xl bg-white/[0.04] animate-pulse" />;
  }
  if (!pick) {
    return (
      <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-5 text-sm text-zinc-400">
        Sin picks para hoy · próximo análisis a las 06:00 UTC
      </div>
    );
  }
  const ev = pick.evPct;
  const homeFlag = getTeamFlag(pick.homeTeam);
  const awayFlag = getTeamFlag(pick.awayTeam);
  const isHighVariance = pick.prediction === 'away' && ev != null && ev > 50;

  return (
    <Link
      href={`/dashboard/pick/${pick.id}`}
      className="group block rounded-xl border border-white/[0.06] bg-gradient-to-br from-emerald-500/[0.06] to-transparent hover:border-white/15 p-5 transition-colors"
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">{pick.league}</span>
            {pick.marketVerified && (
              <span className="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-emerald-500/15 text-emerald-300">
                market-verified
              </span>
            )}
          </div>
          <div className="font-sans font-bold text-white text-[18px] truncate flex items-center flex-wrap gap-x-1">
            <span className="inline-flex items-center gap-1">
              {homeFlag && <span className="text-[1.15em] leading-none">{homeFlag}</span>}
              <span>{pick.homeTeam}</span>
            </span>
            <span className="text-zinc-600 font-normal text-xs mx-1">vs</span>
            <span className="inline-flex items-center gap-1">
              {awayFlag && <span className="text-[1.15em] leading-none">{awayFlag}</span>}
              <span>{pick.awayTeam}</span>
            </span>
          </div>
          <div className="text-[13px] text-zinc-400 mt-0.5">
            Recomendación: <span className="text-zinc-200 font-semibold">{predictionLabel(pick)}</span>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0 flex-wrap">
          <div className="text-right flex items-center gap-2">
            {isHighVariance && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-semibold h-[22px]">
                ⚠️ Alta varianza
              </span>
            )}
            <div>
              <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">EV</div>
              <div className="font-mono font-bold text-xl" style={{ color: 'var(--color-success)' }}>
                {ev != null ? `${ev >= 0 ? '+' : ''}${ev.toFixed(1)}%` : '—'}
              </div>
            </div>
          </div>
          <span className="text-sm font-semibold text-zinc-300 group-hover:text-white flex items-center gap-1">
            Ver análisis <ArrowRight className="w-4 h-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}

function CompactPickCard({ pick }: { pick: Pick }) {
  const seguro = (pick.confidence ?? 0) >= 60 || pick.marketVerified;
  const ev = pick.evPct;
  const homeFlag = getTeamFlag(pick.homeTeam);
  const awayFlag = getTeamFlag(pick.awayTeam);
  return (
    <Link
      href={`/dashboard/pick/${pick.id}`}
      className="block rounded-xl border border-white/[0.06] bg-[#111114] hover:border-white/15 p-4 transition-colors min-h-[120px]"
    >
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        {renderTournamentBadge(pick.league)}
        <span
          className="text-[10px] font-semibold rounded-full px-2 py-0.5"
          style={
            seguro
              ? { backgroundColor: 'color-mix(in srgb, var(--color-success) 15%, transparent)', color: 'var(--color-success)' }
              : { backgroundColor: 'color-mix(in srgb, var(--color-warning) 15%, transparent)', color: 'var(--color-warning)' }
          }
        >
          {seguro ? 'SEGURO' : 'RIESGO'}
        </span>
      </div>
      <div className="font-sans font-semibold text-white text-[15px] leading-tight mb-2 flex items-center flex-wrap gap-x-1">
        <span className="inline-flex items-center gap-1">
          {homeFlag && <span className="text-[1.15em] leading-none">{homeFlag}</span>}
          <span>{pick.homeTeam}</span>
        </span>
        <span className="text-zinc-500 font-normal text-xs mx-1">vs</span>
        <span className="inline-flex items-center gap-1">
          {awayFlag && <span className="text-[1.15em] leading-none">{awayFlag}</span>}
          <span>{pick.awayTeam}</span>
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] text-zinc-400 truncate">{predictionLabel(pick)}</span>
        {ev !== null && ev !== 0 && (
          <span className="text-[12px] font-mono font-bold flex-shrink-0" style={{ color: ev > 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
            {ev > 0 ? '+' : ''}{ev.toFixed(1)}% EV
          </span>
        )}
      </div>
    </Link>
  );
}

function WorldCupStrip({ picks }: { picks: Pick[] }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="relative inline-flex w-2 h-2">
            <span className="absolute inline-flex w-full h-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
            <span className="relative inline-flex w-2 h-2 rounded-full bg-emerald-500" />
          </span>
          <span className="text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-300">🏆 Mundial 2026 en vivo</span>
        </div>
        <Link href="/world-cup" className="text-[12px] font-semibold text-zinc-400 hover:text-white flex items-center gap-1">
          Ver todos <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
      {picks.length === 0 ? (
        <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-3 text-[13px] text-zinc-500">
          Sin próximos partidos en el pool · ver todos en /world-cup
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">
          {picks.map((p) => (
            <Link
              key={p.id}
              href={`/dashboard/pick/${p.id}`}
              className="shrink-0 rounded-lg border border-white/[0.06] bg-[#111114] hover:border-white/15 px-3 py-2 text-[12px] text-zinc-300 transition-colors"
            >
              <span className="font-semibold text-white">{p.homeTeam}</span>
              <span className="text-zinc-600"> vs </span>
              <span className="font-semibold text-white">{p.awayTeam}</span>
              <span className="text-zinc-500"> · Próximamente</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
