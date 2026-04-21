'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Crown,
  Flame,
  Lock,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { getExclusivePick } from '@/lib/api/picks';
import type { Pick } from '@/types';

export default function PickDelDiaPage() {
  const { user } = useAuth();
  const userTier = (user?.tier ?? 'free') as 'free' | 'pro' | 'vip';
  const locked = userTier !== 'vip';

  const [pick, setPick] = useState<Pick | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getExclusivePick()
      .then((p) => {
        if (!cancelled) {
          setPick(p);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        console.error(err);
        setError('No se pudo cargar el pick exclusivo.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-8">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl bg-[#111114] border border-white/[0.06] p-6 md:p-8 mb-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(251,191,36,0.12),transparent_55%)] pointer-events-none" />
        <div className="relative z-10 flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-300 to-amber-500 flex items-center justify-center shadow-[0_0_30px_rgba(251,191,36,0.35)] shrink-0">
            <Crown className="w-7 h-7 text-[#0a0a0c]" strokeWidth={2.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] font-bold text-amber-300">
                Exclusivo VIP · Pick del día
              </span>
              <span className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                EV ≥ 12%
              </span>
            </div>
            <h1 className="font-sans font-extrabold text-[26px] md:text-[32px] text-white tracking-tight leading-tight mb-2">
              Un solo pick. El de mayor ventaja matemática del día.
            </h1>
            <p className="font-sans text-[14px] text-zinc-400 max-w-2xl leading-relaxed">
              Curado desde las cinco grandes ligas europeas. Cruzamos nuestro modelo ELO + forma
              reciente contra las líneas de Bet365 y Pinnacle, y publicamos solo el outlier más claro.
            </p>
          </div>
        </div>

        {/* Stats pill row */}
        <div className="relative z-10 mt-6 grid grid-cols-2 md:grid-cols-4 gap-2">
          <StatPill label="Hit rate 90d" value="68%" tone="emerald" />
          <StatPill label="ROI promedio" value="+31.4%" tone="emerald" />
          <StatPill label="EV mínimo" value="≥12%" tone="amber" />
          <StatPill label="Frecuencia" value="1 / día" tone="white" />
        </div>
      </div>

      {/* Pick principal */}
      {loading && <SkeletonPick />}

      {error && !loading && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-sans font-bold text-[13px] text-red-200">No se pudo cargar</p>
            <p className="font-sans text-[12px] text-red-300/80 font-mono">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && pick && (
        <PickShowcase pick={pick} locked={locked} userTier={userTier} />
      )}

      {/* Why VIP (always visible) */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
        <BenefitCard
          icon={<Flame className="w-4 h-4" />}
          title="Edge máximo garantizado"
          body="Publicamos solo si EV ≥ 12%. Si no hay outlier en el día, no hay pick — no rellenamos."
        />
        <BenefitCard
          icon={<Zap className="w-4 h-4" />}
          title="Alerta inmediata"
          body="Telegram privado + email cuando detectamos la divergencia. Antes que movamos el mercado."
        />
        <BenefitCard
          icon={<CheckCircle2 className="w-4 h-4" />}
          title="Auditoría total"
          body="Histórico público mes a mes. PnL real con stakes sugeridos por Kelly fraccional."
        />
      </div>

      {/* CTA final si no es VIP */}
      {locked && (
        <div className="mt-6 rounded-2xl bg-gradient-to-r from-amber-300 to-amber-500 text-[#0a0a0c] p-6 md:p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="font-sans font-extrabold text-[20px] mb-1 tracking-tight">
              Desbloquea el Pick del día con VIP
            </div>
            <p className="font-sans text-[13px] opacity-80 max-w-xl">
              €79/mes. Acceso al pick exclusivo + todos los picks VIP (edge ≥ 8%) + análisis con IA
              + alertas Telegram. Cancela cuando quieras.
            </p>
          </div>
          <Link
            href="/pricing"
            className="shrink-0 inline-flex items-center gap-2 h-[48px] px-6 rounded-full bg-[#0a0a0c] text-amber-300 font-sans font-bold text-[14px] hover:bg-black transition-colors"
          >
            Ver planes
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
}

// ========== sub-components ==========

function PickShowcase({
  pick,
  locked,
  userTier,
}: {
  pick: Pick;
  locked: boolean;
  userTier: 'free' | 'pro' | 'vip';
}) {
  const predLabel =
    pick.prediction === 'home'
      ? `${pick.homeTeam} gana`
      : pick.prediction === 'away'
        ? `${pick.awayTeam} gana`
        : 'Empate';

  return (
    <div className="relative bg-[#111114] border border-white/[0.06] rounded-2xl overflow-hidden">
      {/* Match header */}
      <div className="px-6 py-5 border-b border-white/[0.06] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Target className="w-4 h-4 text-amber-300" />
          <div>
            <div className="font-sans text-[12px] text-zinc-500">
              {pick.league} · {formatKickoff(pick.kickoff)}
            </div>
            <div className="font-sans font-bold text-[20px] text-white tracking-tight">
              {locked ? '••• vs •••' : `${pick.homeTeam} vs ${pick.awayTeam}`}
            </div>
          </div>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/20">
          Pick del día · VIP
        </span>
      </div>

      {/* Main content */}
      {locked ? (
        <LockedBody userTier={userTier} pick={pick} />
      ) : (
        <UnlockedBody pick={pick} predLabel={predLabel} />
      )}
    </div>
  );
}

function UnlockedBody({ pick, predLabel }: { pick: Pick; predLabel: string }) {
  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-[1.3fr_1fr] gap-6">
      {/* Left: prediction + reasoning */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="font-sans text-[11px] uppercase tracking-widest font-bold text-zinc-400">
            Predicción del modelo
          </span>
          <span className="font-mono text-[13px] font-bold text-white">
            {pick.confidence}% confianza
          </span>
        </div>
        <div className="bg-[#16161a] border border-white/[0.06] rounded-xl p-4 mb-4">
          <div className="font-sans font-extrabold text-[26px] text-white tracking-tight leading-tight">
            {predLabel}
          </div>
          <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-white rounded-full"
              style={{ width: `${pick.confidence}%` }}
            />
          </div>
        </div>

        <div className="border-l-2 border-amber-300 pl-4">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span className="font-sans text-[11px] uppercase tracking-widest font-bold text-amber-300">
              Razonamiento IA
            </span>
          </div>
          <p className="font-sans text-[13.5px] text-zinc-200 leading-relaxed">
            {pick.aiReasoning}
          </p>
        </div>
      </div>

      {/* Right: numbers */}
      <div className="flex flex-col gap-3">
        <StatRow
          label="EV detectado"
          value={`+${pick.evPct?.toFixed(1) ?? '—'}%`}
          tone="emerald"
          big
        />
        <StatRow
          label="Edge vs Bet365"
          value={`${(pick.edgePp ?? 0) >= 0 ? '+' : ''}${pick.edgePp?.toFixed(1) ?? '—'} pp`}
          tone="emerald"
        />
        <StatRow
          label="Cuota recomendada"
          value={pick.odds?.toFixed(2) ?? '—'}
          tone="white"
        />
        <StatRow
          label="Stake sugerido (Kelly)"
          value={`${pick.suggestedStake.toFixed(1)}%`}
          tone="white"
        />
        <div className="mt-1 pt-3 border-t border-white/[0.06]">
          <div className="font-sans text-[10px] uppercase tracking-widest font-bold text-zinc-500 mb-2">
            Probabilidades cruzadas
          </div>
          <div className="grid grid-cols-3 gap-2">
            <ProbPill label="ML" value={mainProb(pick, pick.mlProb)} />
            <ProbPill label="Bet365" value={mainProb(pick, pick.bkProb)} />
            {pick.polyProb ? (
              <ProbPill label="Poly" value={mainProb(pick, pick.polyProb)} />
            ) : (
              <div className="rounded-md bg-white/[0.03] border border-white/[0.06] px-2 py-1.5 text-center opacity-40">
                <div className="font-mono text-[9px] text-zinc-500">POLY</div>
                <div className="font-mono text-[12px] text-zinc-600">—</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function LockedBody({ userTier, pick }: { userTier: 'free' | 'pro' | 'vip'; pick: Pick }) {
  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-[1.3fr_1fr] gap-6">
      <div className="relative">
        <div className="bg-[#16161a] border border-white/[0.06] rounded-xl p-4 mb-4 blur-sm select-none pointer-events-none">
          <div className="font-sans font-extrabold text-[26px] text-white tracking-tight leading-tight">
            ••••••• gana
          </div>
          <div className="h-1 w-full bg-black/40 rounded-full overflow-hidden mt-3">
            <div className="h-full bg-white w-3/4" />
          </div>
        </div>
        <div className="border-l-2 border-amber-300 pl-4 blur-sm select-none pointer-events-none">
          <div className="font-sans text-[11px] uppercase tracking-widest font-bold text-amber-300 mb-1">
            Razonamiento IA
          </div>
          <p className="font-sans text-[13.5px] text-zinc-200 leading-relaxed">
            {'• '.repeat(40)}
          </p>
        </div>

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
          <div className="w-14 h-14 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center mb-3">
            <Lock className="w-6 h-6 text-amber-300" />
          </div>
          <div className="font-sans font-bold text-[16px] text-white mb-1">
            Contenido exclusivo VIP
          </div>
          <p className="font-sans text-[12.5px] text-zinc-300 max-w-xs mb-4">
            {userTier === 'pro'
              ? 'El Pick del día es una pieza extra del plan VIP (€79/mes). Upgrade desde tu cuenta actual.'
              : 'Activa VIP para ver la predicción completa, el razonamiento IA y los números.'}
          </p>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-1.5 h-[38px] px-5 rounded-full bg-amber-300 text-[#0a0a0c] font-sans font-bold text-[13px] hover:bg-amber-200 transition-colors"
          >
            <Crown className="w-4 h-4" />
            Desbloquear · €79/mes
          </Link>
        </div>
      </div>

      {/* Right: sidebar muestra solo EV para crear intriga */}
      <div className="flex flex-col gap-3">
        <StatRow
          label="EV detectado"
          value={`+${pick.evPct?.toFixed(1) ?? '—'}%`}
          tone="emerald"
          big
        />
        <div className="bg-[#16161a] border border-white/[0.06] rounded-lg p-3 text-center">
          <div className="font-sans text-[11px] text-zinc-400 mb-2">
            Solo desvelamos el EV como teaser.
          </div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Edge · Cuota · Stake · IA bloqueados
          </div>
        </div>
        <Link
          href="/pricing"
          className="mt-auto inline-flex items-center justify-center gap-1.5 h-[42px] rounded-lg bg-amber-300 text-[#0a0a0c] font-sans font-bold text-[13px] hover:bg-amber-200 transition-colors"
        >
          Ver planes VIP
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'emerald' | 'amber' | 'white';
}) {
  const toneClass =
    tone === 'amber'
      ? 'text-amber-300'
      : tone === 'emerald'
        ? 'text-emerald-400'
        : 'text-white';
  return (
    <div className="bg-[#0a0a0c] border border-white/[0.06] rounded-lg px-3 py-2">
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-0.5">
        {label}
      </div>
      <div className={`font-mono font-bold text-[15px] ${toneClass}`}>{value}</div>
    </div>
  );
}

function StatRow({
  label,
  value,
  tone,
  big = false,
}: {
  label: string;
  value: string;
  tone: 'emerald' | 'amber' | 'white';
  big?: boolean;
}) {
  const colorMap = {
    emerald: 'text-emerald-400',
    amber: 'text-amber-300',
    white: 'text-white',
  } as const;
  return (
    <div className="bg-[#16161a] border border-white/[0.06] rounded-lg px-4 py-3 flex items-center justify-between">
      <span className="font-sans text-[12px] text-zinc-400">{label}</span>
      <span className={`font-mono font-bold ${big ? 'text-[22px]' : 'text-[14px]'} ${colorMap[tone]}`}>
        {value}
      </span>
    </div>
  );
}

function ProbPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-[#16161a] border border-white/[0.06] px-2 py-1.5 text-center">
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="font-mono text-[12px] font-bold text-white">{Math.round(value * 100)}%</div>
    </div>
  );
}

function BenefitCard({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-4">
      <div className="w-8 h-8 rounded-lg bg-white/5 text-zinc-200 flex items-center justify-center mb-3">
        {icon}
      </div>
      <div className="font-sans font-bold text-[13.5px] text-white mb-1">{title}</div>
      <p className="font-sans text-[12px] text-zinc-400 leading-snug">{body}</p>
    </div>
  );
}

function SkeletonPick() {
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6 animate-pulse">
      <div className="h-5 w-1/3 bg-white/5 rounded mb-3" />
      <div className="h-8 w-2/3 bg-white/5 rounded mb-6" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-20 bg-white/5 rounded-xl" />
        <div className="h-20 bg-white/5 rounded-xl" />
      </div>
    </div>
  );
}

function mainProb(pick: Pick, triplet: Pick['mlProb']): number {
  if (pick.prediction === 'home') return triplet.home;
  if (pick.prediction === 'draw') return triplet.draw;
  return triplet.away;
}

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
