'use client';

import { Calendar, CornerUpRight, Goal, Sparkles, Target, TrendingUp } from 'lucide-react';
import type { MatchPrediction } from '@/lib/markets/types';

interface Props {
  match: MatchPrediction;
}

const FORM_COLOR: Record<'W' | 'D' | 'L', string> = {
  W: 'bg-emerald-500/20 text-emerald-300',
  D: 'bg-zinc-500/20 text-zinc-300',
  L: 'bg-red-500/20 text-red-300',
};

export default function MatchMarketCard({ match }: Props) {
  const dt = new Date(match.kickoffISO);
  const dayLabel = dt.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric', month: 'short' });
  const timeLabel = dt.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

  return (
    <article className="bg-[#111114] border border-white/[0.06] rounded-2xl overflow-hidden">
      <header className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[16px] leading-none">🇪🇺</span>
          <div className="min-w-0">
            <div className="font-sans font-bold text-[13px] text-white truncate">
              {match.competition}
            </div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              {match.stage}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-400 shrink-0">
          <Calendar className="w-3.5 h-3.5" />
          {dayLabel} · {timeLabel}
        </div>
      </header>

      <div className="px-5 py-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <TeamColumn team={match.homeTeam} form={match.homeForm.last5} align="right" />
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-widest">vs</span>
          <span
            className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded"
            style={{
              background: 'rgba(251,191,36,0.12)',
              color: '#fcd34d',
            }}
          >
            {match.confidence}% conf
          </span>
        </div>
        <TeamColumn team={match.awayTeam} form={match.awayForm.last5} align="left" />
      </div>

      <div className="px-5 pb-4 grid grid-cols-3 gap-2 text-center">
        <H2HStat label="H2H" value={`${match.h2h.matches}`} sub="cruces" />
        <H2HStat label="Goles avg" value={match.h2h.avgGoals.toFixed(2)} sub="por match" />
        <H2HStat label="Córners avg" value={match.h2h.avgCorners.toFixed(1)} sub="por match" />
      </div>

      <div className="px-5 pb-5 grid grid-cols-1 md:grid-cols-3 gap-2.5">
        <MarketTile
          icon={<Goal className="w-3.5 h-3.5" />}
          title={`${match.goals.side === 'over' ? 'Over' : 'Under'} ${match.goals.line} goles`}
          modelProbPct={match.goals.modelProb * 100}
          odds={match.goals.bookieOdds}
          edgePp={match.goals.edgePp}
          aux={`xG ${match.goals.expectedGoals.toFixed(2)}`}
        />
        <MarketTile
          icon={<CornerUpRight className="w-3.5 h-3.5" />}
          title={`${match.corners.side === 'over' ? 'Over' : 'Under'} ${match.corners.line} córners`}
          modelProbPct={match.corners.modelProb * 100}
          odds={match.corners.bookieOdds}
          edgePp={match.corners.edgePp}
          aux={`E[c] ${match.corners.expectedCorners.toFixed(1)}`}
        />
        <MarketTile
          icon={<Target className="w-3.5 h-3.5" />}
          title="Ambos anotan"
          modelProbPct={match.btts.prob * 100}
          odds={match.btts.odds}
          edgePp={match.btts.edgePp}
          aux="BTTS yes"
        />
      </div>

      <div className="px-5 py-4 border-t border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400 font-semibold">
            Razonamiento
          </span>
        </div>
        <ul className="flex flex-col gap-1.5">
          {match.reasoning.map((r, i) => (
            <li key={i} className="font-sans text-[12px] text-zinc-300 leading-snug">
              <span className="font-mono text-zinc-600 mr-1.5">{(i + 1).toString().padStart(2, '0')}</span>
              {r}
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

function TeamColumn({
  team,
  form,
  align,
}: {
  team: { code: string; name: string };
  form: ('W' | 'D' | 'L')[];
  align: 'left' | 'right';
}) {
  return (
    <div className={`flex flex-col gap-2 ${align === 'right' ? 'items-end text-right' : 'items-start text-left'}`}>
      <div className="flex items-center gap-2">
        <div
          className={`w-10 h-10 rounded-full bg-white/[0.06] flex items-center justify-center font-mono text-[12px] font-bold text-white order-${align === 'right' ? 'last' : 'first'}`}
        >
          {team.code}
        </div>
        <div className="flex flex-col min-w-0">
          <span className="font-sans font-bold text-[14px] text-white truncate">{team.name}</span>
          <span className="font-mono text-[10px] text-zinc-500">{team.code}</span>
        </div>
      </div>
      <div className={`flex gap-1 ${align === 'right' ? 'flex-row-reverse' : ''}`}>
        {form.map((f, i) => (
          <span
            key={i}
            className={`w-5 h-5 rounded font-mono text-[10px] font-bold flex items-center justify-center ${FORM_COLOR[f]}`}
          >
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}

function H2HStat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg py-2.5">
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
      <div className="font-mono font-bold text-[16px] text-white">{value}</div>
      <div className="font-sans text-[10px] text-zinc-500 mt-0.5">{sub}</div>
    </div>
  );
}

function MarketTile({
  icon,
  title,
  modelProbPct,
  odds,
  edgePp,
  aux,
}: {
  icon: React.ReactNode;
  title: string;
  modelProbPct: number;
  odds: number;
  edgePp: number;
  aux: string;
}) {
  const positive = edgePp >= 0;
  const edgeClass = edgePp >= 8 ? 'text-amber-300' : positive ? 'text-emerald-400' : 'text-red-400';
  return (
    <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3.5">
      <div className="flex items-center justify-between mb-2">
        <span className="flex items-center gap-1.5 font-sans font-semibold text-[12px] text-white">
          <span className="text-zinc-400">{icon}</span>
          {title}
        </span>
        <span className={`flex items-center gap-0.5 font-mono text-[11px] font-bold ${edgeClass}`}>
          <TrendingUp className="w-3 h-3" />
          {edgePp >= 0 ? '+' : ''}
          {edgePp.toFixed(1)}pp
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Mini label="Modelo" value={`${modelProbPct.toFixed(0)}%`} />
        <Mini label="Cuota" value={odds.toFixed(2)} />
        <Mini label="Aux" value={aux} />
      </div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="font-mono font-bold text-[13px] text-white truncate">{value}</div>
    </div>
  );
}
