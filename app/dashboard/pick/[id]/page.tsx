'use client';

import React from 'react';
import useSWR from 'swr';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Clock, MapPin, Target, Flame, Trophy, Activity, Lock, BarChart3, TrendingUp } from 'lucide-react';
import { getPick, getPickStats } from '@/lib/api/picks';
import { useAuth } from '@/contexts/AuthContext';
import TeamLogo from '@/components/picks/TeamLogo';
import type { Pick, MatchStat, TeamStats } from '@/types';

function formatKickoffDate(iso: string) {
  try {
    const date = new Date(iso);
    return date.toLocaleString('es-ES', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  } catch {
    return iso;
  }
}

function formatKickoffTime(iso: string) {
  try {
    const date = new Date(iso);
    return date.toLocaleString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    }) + ' hs';
  } catch {
    return '';
  }
}

function getLiveMinute(iso: string) {
  try {
    const start = new Date(iso).getTime();
    const now = Date.now();
    const diffMins = Math.floor((now - start) / 60000);
    if (diffMins < 0) return 'Próximamente';
    if (diffMins > 115) return 'Finalizado';
    if (diffMins > 45 && diffMins <= 60) return 'Medio Tiempo';
    if (diffMins > 60) return `En vivo · Minuto ${diffMins - 15}'`;
    return `En vivo · Minuto ${diffMins}'`;
  } catch {
    return '';
  }
}

function shouldLock(status: Pick['status'] | undefined, userTier: 'free' | 'pro' | 'vip'): boolean {
  if (!status) return false;
  if (userTier === 'vip') return false;
  if (userTier === 'pro') return status === 'vip';
  return status !== 'free';
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
  '1X': 'Local o Empate',
  'X2': 'Visitante o Empate',
  '12': 'Local o Visitante',
};

export default function PickDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const userTier = (user?.tier ?? 'free') as 'free' | 'pro' | 'vip';

  const { data: pick, error, isLoading } = useSWR(id ? `pick-${id}` : null, () => getPick(id as string));
  const { data: stats } = useSWR(id ? `pick-stats-${id}` : null, () => getPickStats(id as string));

  if (isLoading) {
    return (
      <div className="max-w-[1000px] mx-auto px-4 py-10 flex justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
          <p className="text-zinc-500 font-sans text-sm">Cargando detalles...</p>
        </div>
      </div>
    );
  }

  if (error || !pick) {
    return (
      <div className="max-w-[1000px] mx-auto px-4 py-10">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-zinc-400 hover:text-white mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Volver
        </button>
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-xl font-sans text-center">
          No se encontró el pick o hubo un error al cargar.
        </div>
      </div>
    );
  }

  const isLocked = shouldLock(pick.status, userTier);
  const liveStatus = getLiveMinute(pick.kickoff);
  const isLive = liveStatus.includes('En vivo');

  return (
    <div className="max-w-[1000px] mx-auto px-4 py-8">
      <button onClick={() => router.back()} className="flex items-center gap-2 text-zinc-400 hover:text-white mb-6 font-sans text-sm transition-colors w-fit">
        <ArrowLeft className="w-4 h-4" />
        Volver al Dashboard
      </button>

      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl overflow-hidden mb-6 relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 via-amber-300 to-amber-500" />
        <div className="p-6 md:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-8 border-b border-white/[0.06] pb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
                <Trophy className="w-5 h-5 text-zinc-300" />
              </div>
              <div>
                <h1 className="font-sans font-bold text-[18px] text-white tracking-tight">{pick.league}</h1>
                <p className="font-sans text-[13px] text-zinc-500 capitalize">{formatKickoffDate(pick.kickoff)}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-[#16161a] border border-white/[0.04] rounded-lg px-4 py-2">
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 font-sans text-[11px] text-zinc-500 uppercase tracking-widest font-semibold mb-1">
                  <MapPin className="w-3.5 h-3.5" /> Estadio
                </div>
                <span className="font-sans text-[14px] text-white">Estadio Local</span>
              </div>
              <div className="w-px h-8 bg-white/[0.06]" />
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 font-sans text-[11px] text-zinc-500 uppercase tracking-widest font-semibold mb-1">
                  <Clock className="w-3.5 h-3.5" /> Hora
                </div>
                <span className="font-sans text-[14px] text-white">{formatKickoffTime(pick.kickoff)}</span>
              </div>
              <div className="w-px h-8 bg-white/[0.06]" />
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 font-sans text-[11px] text-zinc-500 uppercase tracking-widest font-semibold mb-1">
                  <Activity className="w-3.5 h-3.5" /> Estado
                </div>
                <span className={`font-sans text-[14px] font-semibold ${isLive ? 'text-red-400' : 'text-zinc-300'}`}>
                  {isLive && <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block mr-2 animate-pulse" />}
                  {liveStatus}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 md:gap-12 mb-10">
            <div className="flex flex-col items-center gap-3 flex-1 min-w-0">
              <TeamLogo src={pick.homeLogo} name={pick.homeTeam} size={88} />
              <h2 className="font-sans font-extrabold text-[20px] md:text-[28px] text-white tracking-tight text-center truncate max-w-full" title={pick.homeTeam}>
                {pick.homeTeam}
              </h2>
              <span className="font-mono text-[11px] uppercase tracking-widest text-zinc-500">Local</span>
            </div>

            <div className="flex flex-col items-center justify-center shrink-0">
              <div className="w-12 h-12 md:w-14 md:h-14 rounded-full bg-[#16161a] border border-white/[0.08] flex items-center justify-center font-mono font-bold text-[16px] md:text-[18px] text-zinc-400">
                VS
              </div>
            </div>

            <div className="flex flex-col items-center gap-3 flex-1 min-w-0">
              <TeamLogo src={pick.awayLogo} name={pick.awayTeam} size={88} />
              <h2 className="font-sans font-extrabold text-[20px] md:text-[28px] text-white tracking-tight text-center truncate max-w-full" title={pick.awayTeam}>
                {pick.awayTeam}
              </h2>
              <span className="font-mono text-[11px] uppercase tracking-widest text-zinc-500">Visitante</span>
            </div>
          </div>

          {isLocked ? (
            <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/20 rounded-2xl p-8 text-center backdrop-blur-sm">
              <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="w-8 h-8 text-amber-400" />
              </div>
              <h3 className="font-sans font-bold text-[20px] text-white mb-2">Pick Premium Lock</h3>
              <p className="font-sans text-[14px] text-zinc-400 max-w-md mx-auto mb-6">
                Este análisis detallado es exclusivo para usuarios con plan Pro o VIP. Actualiza tu plan para acceder a la predicción y el modelo.
              </p>
              <button onClick={() => router.push('/pricing')} className="h-[44px] px-8 rounded-full bg-amber-400 text-[#0a0a0c] font-sans font-bold text-[14px] hover:bg-amber-300 transition-colors">
                Ver planes de Upgrade
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Target className="w-5 h-5 text-amber-400" />
                  <h3 className="font-sans font-bold text-[16px] text-white">Recomendación del Modelo</h3>
                </div>
                <div className="flex items-end justify-between mb-4">
                  <div className="font-sans text-[18px] font-semibold text-white">
                    {predictionLabel[pick.prediction] ?? pick.prediction}
                  </div>
                  <div className="font-mono text-[24px] font-bold text-emerald-400">
                    {pick.confidence}% <span className="text-[12px] text-zinc-500">prob</span>
                  </div>
                </div>
                <div className="font-sans text-[14px] text-zinc-400 leading-relaxed bg-[#111114] p-4 rounded-xl border border-white/[0.04]">
                  {pick.aiReasoning}
                </div>
              </div>

              <div className="flex flex-col gap-6">
                <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
                   <div className="flex items-center gap-2 mb-4">
                    <Flame className="w-5 h-5 text-amber-400" />
                    <h3 className="font-sans font-bold text-[16px] text-white">Probabilidades (Layer Blend)</h3>
                  </div>
                  <div className="space-y-4">
                    {pick.blendedProb && Object.entries(pick.blendedProb).map(([outcome, prob]) => {
                       const label = predictionLabel[outcome] ?? outcome;
                       const pct = (prob * 100).toFixed(1);
                       const isSelected = outcome === pick.prediction;
                       return (
                         <div key={outcome} className="relative">
                            <div className="flex justify-between font-sans text-[13px] mb-1.5">
                              <span className={isSelected ? 'text-white font-bold' : 'text-zinc-400'}>{label}</span>
                              <span className="font-mono text-zinc-300">{pct}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-[#111114] rounded-full overflow-hidden">
                              <div className={`h-full rounded-full transition-all ${isSelected ? 'bg-amber-400' : 'bg-zinc-600'}`} style={{ width: `${pct}%` }} />
                            </div>
                         </div>
                       )
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#16161a] border border-white/[0.04] rounded-xl p-5">
                    <div className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 mb-1 font-semibold">Stake Sugerido</div>
                    <div className="font-mono text-[24px] font-bold text-white mb-1">{pick.suggestedStake.toFixed(1)}%</div>
                    <div className="font-sans text-[11px] text-zinc-500">de tu bankroll</div>
                  </div>
                  <div className="bg-[#16161a] border border-white/[0.04] rounded-xl p-5">
                    <div className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 mb-1 font-semibold">Cuota Ref.</div>
                    <div className="font-mono text-[24px] font-bold text-white mb-1">@{pick.odds?.toFixed(2) ?? '—'}</div>
                    <div className="font-sans text-[11px] text-emerald-400 flex items-center gap-1">
                      {pick.evPct && pick.evPct > 0 ? `+${pick.evPct.toFixed(1)}% EV` : ''}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {stats && (
            <div className="mt-8 space-y-6">
              <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-amber-400" />
                  <h3 className="font-sans font-bold text-[16px] text-white">
                    Últimos {stats.h2h.length || 5} Enfrentamientos (H2H)
                  </h3>
                </div>
                {stats.h2h.length === 0 ? (
                   <p className="font-sans text-[13px] text-zinc-500 text-center py-4">
                     No se registraron enfrentamientos directos recientes entre estos equipos.
                   </p>
                ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                    {stats.h2h.map((m, i) => (
                      <H2HCard key={i} match={m} />
                    ))}
                  </div>
                )}
                {stats.h2h.length > 0 && <H2HSummary h2h={stats.h2h} home={pick.homeTeam} away={pick.awayTeam} />}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <TeamMomentumCard team={stats.home_stats} />
                <TeamMomentumCard team={stats.away_stats} />
              </div>

              {stats.home_stats.last_5.length > 0 && stats.away_stats.last_5.length > 0 && (
                <SmartInsights
                  home={stats.home_stats}
                  away={stats.away_stats}
                  h2h={stats.h2h}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── H2H card estilo OneFootball ────────────────────────────────────────────
function H2HCard({ match }: { match: MatchStat }) {
  const [hScore, aScore] = match.score.split('-').map((s) => parseInt(s, 10));
  const isDraw = !isNaN(hScore) && hScore === aScore;
  const homeWon = !isDraw && hScore > aScore;
  const awayWon = !isDraw && aScore > hScore;

  const badgeClass = isDraw
    ? 'bg-zinc-600 text-white'
    : homeWon
      ? 'bg-emerald-500 text-white'
      : 'bg-red-500 text-white';
  const badgeLabel = isDraw ? 'EMPATE' : homeWon ? 'VICTORIA' : 'DERROTA';

  return (
    <div className="bg-[#111114] border border-white/[0.04] rounded-xl overflow-hidden">
      {/* Badge top */}
      <div className={`text-center py-1 text-[9px] font-mono font-bold tracking-widest ${badgeClass}`}>
        {badgeLabel}
      </div>
      <div className="p-3 flex flex-col items-center gap-2">
        {/* Score */}
        <div className="font-mono font-bold text-[22px] text-white tracking-tight">
          {match.score}
        </div>
        {/* Teams with logos */}
        <div className="flex items-center justify-between w-full gap-1">
          <div className="flex flex-col items-center gap-1 flex-1 min-w-0">
            <TeamLogo src={match.homeLogo} name={match.home} size={26} />
            <span className="font-sans text-[9.5px] text-zinc-400 truncate text-center w-full">{match.home}</span>
          </div>
          <span className="text-zinc-600 text-[10px] shrink-0">vs</span>
          <div className="flex flex-col items-center gap-1 flex-1 min-w-0">
            <TeamLogo src={match.awayLogo} name={match.away} size={26} />
            <span className="font-sans text-[9.5px] text-zinc-400 truncate text-center w-full">{match.away}</span>
          </div>
        </div>
        {/* Date */}
        <span className="font-sans text-[9px] text-zinc-600 pt-1 border-t border-white/[0.04] w-full text-center">
          {match.date}
        </span>
      </div>
    </div>
  );
}

// ─── Resumen estadístico H2H (W/D/L para el local) ─────────────────────────────
function H2HSummary({ h2h, home, away }: { h2h: MatchStat[]; home: string; away: string }) {
  let homeWins = 0, awayWins = 0, draws = 0;
  let homeGoals = 0, awayGoals = 0;
  for (const m of h2h) {
    const [h, a] = m.score.split('-').map((s) => parseInt(s, 10));
    if (isNaN(h) || isNaN(a)) continue;
    const homeIsLocal = m.home === home;
    const localGoals = homeIsLocal ? h : a;
    const visitorGoals = homeIsLocal ? a : h;
    homeGoals += localGoals;
    awayGoals += visitorGoals;
    if (h === a) draws++;
    else if ((h > a && homeIsLocal) || (a > h && !homeIsLocal)) homeWins++;
    else awayWins++;
  }
  const total = h2h.length;
  return (
    <div className="mt-4 pt-4 border-t border-white/[0.04]">
      <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-widest text-zinc-500 mb-2">
        <span>Balance histórico</span>
        <span>
          GF {homeGoals} · GC {awayGoals}
        </span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden bg-zinc-800">
        <div className="bg-emerald-500" style={{ width: `${(homeWins / total) * 100}%` }} title={`${home} ${homeWins}`} />
        <div className="bg-zinc-500" style={{ width: `${(draws / total) * 100}%` }} title={`Empates ${draws}`} />
        <div className="bg-red-500" style={{ width: `${(awayWins / total) * 100}%` }} title={`${away} ${awayWins}`} />
      </div>
      <div className="flex items-center justify-between text-[11px] font-sans text-zinc-400 mt-2">
        <span><span className="text-emerald-400 font-bold">{homeWins}</span> {home}</span>
        <span><span className="text-zinc-300 font-bold">{draws}</span> empates</span>
        <span><span className="text-red-400 font-bold">{awayWins}</span> {away}</span>
      </div>
    </div>
  );
}

// ─── Momentum card por equipo (forma + agregados + últimos partidos) ──────────
function TeamMomentumCard({ team }: { team: TeamStats }) {
  return (
    <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <TeamLogo src={team.logo} name={team.team} size={40} />
          <div className="min-w-0">
            <h3 className="font-sans font-bold text-[15px] text-white truncate">{team.team}</h3>
            <p className="font-sans text-[11px] text-zinc-500">
              {team.aggregates
                ? `${team.aggregates.wins}V ${team.aggregates.draws}E ${team.aggregates.losses}D`
                : `ELO ${team.elo ?? '—'}`}
            </p>
          </div>
        </div>
        {team.form && <FormPills form={team.form} />}
      </div>

      <p className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold mb-3">
        Últimos partidos
      </p>

      {team.last_5.length === 0 ? (
        <p className="font-sans text-[13px] text-zinc-500 text-center py-4">No hay datos.</p>
      ) : (
        <div className="grid grid-cols-1 gap-2">
          {team.last_5.map((m, i) => (
            <MomentumRow key={i} match={m} targetTeam={team.team} />
          ))}
        </div>
      )}
    </div>
  );
}

function FormPills({ form }: { form: string }) {
  const colors: Record<string, string> = {
    W: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    D: 'bg-zinc-500/20 text-zinc-300 border-zinc-500/30',
    L: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  return (
    <div className="flex items-center gap-1 shrink-0">
      {form.split('').map((r, i) => (
        <span
          key={i}
          className={`w-5 h-5 flex items-center justify-center rounded border font-mono font-bold text-[10px] ${colors[r] ?? 'bg-zinc-700 text-zinc-500 border-zinc-600'}`}
        >
          {r}
        </span>
      ))}
    </div>
  );
}

function MomentumRow({ match, targetTeam }: { match: MatchStat; targetTeam: string }) {
  const [hScore, aScore] = match.score.split('-').map((s) => parseInt(s, 10));
  const result = match.result ?? 'D';
  const isHome = match.home === targetTeam;

  // OneFootball style badge
  const badgeMap = {
    W: { label: 'VICTORIA', cls: 'bg-emerald-500 text-white' },
    L: { label: 'DERROTA',  cls: 'bg-red-500 text-white' },
    D: { label: 'EMPATE',   cls: 'bg-zinc-600 text-white' },
  };
  const badge = badgeMap[result as keyof typeof badgeMap] ?? badgeMap.D;

  return (
    <div className="bg-[#111114] border border-white/[0.04] rounded-xl overflow-hidden">
      {/* Result banner */}
      <div className={`text-center py-0.5 text-[9px] font-mono font-bold tracking-widest ${badge.cls}`}>
        {badge.label}
      </div>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <div className="flex-1 min-w-0">
          {/* Home row */}
          <div className="flex items-center justify-between text-[12px] mb-1">
            <div className="flex items-center gap-2 min-w-0">
              <TeamLogo src={match.homeLogo} name={match.home} size={18} />
              <span className={`truncate ${isHome ? 'font-bold text-white' : 'text-zinc-400'}`}>
                {match.home}
              </span>
            </div>
            <span className="font-mono font-bold text-zinc-300 ml-2 shrink-0">{isNaN(hScore) ? '—' : hScore}</span>
          </div>
          {/* Away row */}
          <div className="flex items-center justify-between text-[12px]">
            <div className="flex items-center gap-2 min-w-0">
              <TeamLogo src={match.awayLogo} name={match.away} size={18} />
              <span className={`truncate ${!isHome ? 'font-bold text-white' : 'text-zinc-400'}`}>
                {match.away}
              </span>
            </div>
            <span className="font-mono font-bold text-zinc-300 ml-2 shrink-0">{isNaN(aScore) ? '—' : aScore}</span>
          </div>
        </div>
      </div>
      <div className="text-center pb-1.5">
        <span className="font-sans text-[9px] text-zinc-600">{match.date}</span>
      </div>
    </div>
  );
}

// ─── Recomendaciones inteligentes basadas en estadísticas reales ──────────────
function SmartInsights({ home, away, h2h }: { home: TeamStats; away: TeamStats; h2h: MatchStat[] }) {
  const insights: { icon: React.ReactNode; tone: 'emerald' | 'amber' | 'red' | 'neutral'; title: string; body: string }[] = [];

  if (home.aggregates && away.aggregates) {
    const homeGfAvg = home.aggregates.goals_for / Math.max(home.last_5.length, 1);
    const homeGaAvg = home.aggregates.goals_against / Math.max(home.last_5.length, 1);
    const awayGfAvg = away.aggregates.goals_for / Math.max(away.last_5.length, 1);
    const awayGaAvg = away.aggregates.goals_against / Math.max(away.last_5.length, 1);
    const expGoals = (homeGfAvg + awayGaAvg + awayGfAvg + homeGaAvg) / 2;

    if (expGoals >= 2.8) {
      insights.push({
        icon: <Flame className="w-4 h-4" />,
        tone: 'amber',
        title: 'Partido con fuegos artificiales',
        body: `Promedio combinado de ${expGoals.toFixed(1)} goles esperados. Over 2.5 con valor estadístico.`,
      });
    } else if (expGoals <= 1.9) {
      insights.push({
        icon: <Activity className="w-4 h-4" />,
        tone: 'neutral',
        title: 'Defensas firmes en ambos lados',
        body: `Solo ${expGoals.toFixed(1)} goles esperados. Under 2.5 ofrece margen de seguridad.`,
      });
    }

    const homeWinPct = (home.aggregates.wins / Math.max(home.last_5.length, 1)) * 100;
    const awayWinPct = (away.aggregates.wins / Math.max(away.last_5.length, 1)) * 100;
    if (homeWinPct >= 80) {
      insights.push({
        icon: <TrendingUp className="w-4 h-4" />,
        tone: 'emerald',
        title: `${home.team} en racha`,
        body: `${home.aggregates.wins} victorias en sus últimos ${home.last_5.length} partidos. Forma sólida.`,
      });
    }
    if (awayWinPct >= 80) {
      insights.push({
        icon: <TrendingUp className="w-4 h-4" />,
        tone: 'emerald',
        title: `${away.team} en racha`,
        body: `${away.aggregates.wins} victorias en sus últimos ${away.last_5.length} partidos. Llega encendido.`,
      });
    }

    if (home.aggregates.losses >= 3) {
      insights.push({
        icon: <Activity className="w-4 h-4" />,
        tone: 'red',
        title: `${home.team} en crisis`,
        body: `${home.aggregates.losses} derrotas recientes. Cuidado con apostar a su favor sin contexto adicional.`,
      });
    }
  }

  if (home.elo && away.elo) {
    const eloGap = home.elo - away.elo;
    if (Math.abs(eloGap) >= 120) {
      const fav = eloGap > 0 ? home.team : away.team;
      insights.push({
        icon: <BarChart3 className="w-4 h-4" />,
        tone: 'amber',
        title: `Brecha ELO clara a favor de ${fav}`,
        body: `Diferencial de ${Math.abs(eloGap).toFixed(0)} puntos ELO. Favorito sólido por nivel histórico.`,
      });
    }
  }

  if (h2h.length >= 3) {
    let homeWins = 0, awayWins = 0, draws = 0;
    for (const m of h2h) {
      const [h, a] = m.score.split('-').map((s) => parseInt(s, 10));
      if (isNaN(h) || isNaN(a)) continue;
      const homeIsLocal = m.home === home.team;
      if (h === a) draws++;
      else if ((h > a && homeIsLocal) || (a > h && !homeIsLocal)) homeWins++;
      else awayWins++;
    }
    if (homeWins >= 3) {
      insights.push({
        icon: <Trophy className="w-4 h-4" />,
        tone: 'emerald',
        title: `Bestia negra: ${home.team} domina el H2H`,
        body: `${homeWins} victorias en los últimos ${h2h.length} cruces directos.`,
      });
    } else if (awayWins >= 3) {
      insights.push({
        icon: <Trophy className="w-4 h-4" />,
        tone: 'emerald',
        title: `Bestia negra: ${away.team} domina el H2H`,
        body: `${awayWins} victorias en los últimos ${h2h.length} cruces directos.`,
      });
    } else if (draws >= 3) {
      insights.push({
        icon: <Activity className="w-4 h-4" />,
        tone: 'neutral',
        title: 'Cruce históricamente parejo',
        body: `${draws} empates en ${h2h.length} cruces. Doble oportunidad gana valor aquí.`,
      });
    }
  }

  if (insights.length === 0) {
    return null;
  }

  const toneClasses: Record<typeof insights[number]['tone'], string> = {
    emerald: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300',
    amber: 'bg-amber-500/10 border-amber-500/20 text-amber-300',
    red: 'bg-red-500/10 border-red-500/20 text-red-300',
    neutral: 'bg-white/[0.04] border-white/[0.08] text-zinc-300',
  };

  return (
    <div className="bg-[#16161a] border border-white/[0.04] rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-amber-400" />
        <h3 className="font-sans font-bold text-[16px] text-white">Lecturas inteligentes</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {insights.map((ins, i) => (
          <div key={i} className={`rounded-xl border p-4 ${toneClasses[ins.tone]}`}>
            <div className="flex items-center gap-2 mb-1.5">
              {ins.icon}
              <span className="font-sans font-bold text-[13px]">{ins.title}</span>
            </div>
            <p className="font-sans text-[12.5px] leading-snug opacity-90">{ins.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
