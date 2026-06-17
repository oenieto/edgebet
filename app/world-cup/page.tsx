'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, Trophy, Zap } from 'lucide-react';

import {
  getWorldCupDashboard,
  type Signal,
  type WCDashboard,
  type WCTeamRow,
  type WCTopPick,
} from '@/lib/api/worldcup';

// Colores de señal desde variables CSS (valores dinámicos → inline style permitido).
const SIGNAL_VAR: Record<Signal, string> = {
  green: 'var(--color-success)',
  yellow: 'var(--color-warning)',
  red: 'var(--color-danger)',
};

const GROUP_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'];

function tint(varName: string, pct: number): string {
  return `color-mix(in srgb, ${varName} ${pct}%, transparent)`;
}

const Dash = () => <span className="text-zinc-600">—</span>;

// ----------------------------------------------------------------------------
// Átomos
// ----------------------------------------------------------------------------

function Pill({ signal, children }: { signal: Signal; children: React.ReactNode }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium text-white inline-flex items-center"
      style={{ backgroundColor: SIGNAL_VAR[signal] }}
    >
      {children}
    </span>
  );
}

function FormSquare({ r }: { r: 'W' | 'D' | 'L' }) {
  const sig: Signal = r === 'W' ? 'green' : r === 'D' ? 'yellow' : 'red';
  return (
    <span
      className="w-5 h-5 rounded-sm text-white text-[10px] font-bold inline-flex items-center justify-center"
      style={{ backgroundColor: SIGNAL_VAR[sig] }}
    >
      {r}
    </span>
  );
}

function num(n: number | null, digits = 1): string {
  return n == null ? '' : n.toFixed(digits);
}

// ----------------------------------------------------------------------------
// Celdas de la tabla
// ----------------------------------------------------------------------------

function TeamCell({ t }: { t: WCTeamRow }) {
  return (
    <div className="flex items-center gap-2 min-w-[150px]">
      <span className="text-lg leading-none">{t.flag}</span>
      <span className="font-medium text-zinc-100 truncate">{t.team}</span>
      {t.estimated && (
        <span title="Dato estimado por modelo ELO" className="text-zinc-500 shrink-0">
          <Zap className="w-3 h-3" />
        </span>
      )}
    </div>
  );
}

function GoalsCell({ t }: { t: WCTeamRow }) {
  if (t.gf_per_game == null && t.gc_per_game == null) return <Dash />;
  const gfColor = t.gf_per_game != null && t.gf_per_game >= 1.5 ? SIGNAL_VAR.green : undefined;
  const gcColor = t.gc_per_game != null && t.gc_per_game >= 1.3 ? SIGNAL_VAR.red : undefined;
  return (
    <span className="font-mono">
      <span style={{ color: gfColor }}>{t.gf_per_game != null ? num(t.gf_per_game) : '—'}</span>
      <span className="text-zinc-600"> / </span>
      <span style={{ color: gcColor }}>{t.gc_per_game != null ? num(t.gc_per_game) : '—'}</span>
    </span>
  );
}

function OuCell({ t }: { t: WCTeamRow }) {
  if (!t.over25_tendency) return <Dash />;
  if (t.over25_tendency === 'even') return <span className="text-zinc-400 text-xs">Par</span>;
  const isOver = t.over25_tendency === 'over';
  return <Pill signal={isOver ? 'green' : 'yellow'}>{isOver ? 'Over' : 'Under'}</Pill>;
}

function BttsCell({ t }: { t: WCTeamRow }) {
  if (t.btts_pct == null) return <Dash />;
  const sig: Signal = t.btts_pct > 50 ? 'green' : t.btts_pct >= 35 ? 'yellow' : 'red';
  return (
    <span className="font-mono" style={{ color: SIGNAL_VAR[sig] }}>
      {t.btts_pct}%
    </span>
  );
}

function CornersCell({ t }: { t: WCTeamRow }) {
  if (t.corners_for == null && t.corners_against == null) return <Dash />;
  return (
    <div className="leading-tight">
      <span className="font-mono">
        {num(t.corners_for)}F / {num(t.corners_against)}C
      </span>
      {t.corners_line && (
        <div className="text-[10px] text-zinc-500 mt-0.5">{t.corners_line}</div>
      )}
    </div>
  );
}

function CardsCell({ t }: { t: WCTeamRow }) {
  if (t.cards_avg == null) return <Dash />;
  return (
    <div className="leading-tight">
      <span className="font-mono">{num(t.cards_avg)}</span>
      {t.cards_line && <div className="text-[10px] text-zinc-500 mt-0.5">{t.cards_line}</div>}
    </div>
  );
}

function PossessionCell({ t }: { t: WCTeamRow }) {
  if (t.possession_avg == null) return <Dash />;
  const sig: Signal = t.possession_avg > 55 ? 'green' : t.possession_avg >= 45 ? 'yellow' : 'red';
  return (
    <span className="font-mono" style={{ color: SIGNAL_VAR[sig] }}>
      {t.possession_avg}%
    </span>
  );
}

function FormCell({ t }: { t: WCTeamRow }) {
  if (!t.form_last5 || t.form_last5.length === 0) return <Dash />;
  return (
    <div className="flex gap-0.5">
      {t.form_last5.map((r, i) => (
        <FormSquare key={i} r={r} />
      ))}
    </div>
  );
}

// ----------------------------------------------------------------------------
// Tabla de grupo
// ----------------------------------------------------------------------------

const COLS = ['Equipo', 'V/E/D %', 'GF/GC p/p', 'O/U 2.5', 'BTTS %', 'Corners', 'Tarjetas', 'Posesión', 'Forma', '🔥 Dato'];

function GroupTable({ teams }: { teams: WCTeamRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-[#111114]">
      <table className="w-full text-xs sm:text-sm border-collapse">
        <thead>
          <tr className="border-b border-white/[0.06] text-left">
            {COLS.map((c) => (
              <th
                key={c}
                className="px-3 py-2.5 font-sans text-[10px] uppercase tracking-wider text-zinc-500 font-bold whitespace-nowrap"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map((t) => (
            <tr
              key={t.team}
              className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02]"
              style={{ borderLeft: `3px solid ${SIGNAL_VAR[t.overall_signal]}` }}
            >
              <td className="px-3 py-2.5">
                <TeamCell t={t} />
              </td>
              <td className="px-3 py-2.5">
                <div className="flex gap-1">
                  <Pill signal="green">{t.prob_win}</Pill>
                  <Pill signal="yellow">{t.prob_draw}</Pill>
                  <Pill signal="red">{t.prob_loss}</Pill>
                </div>
              </td>
              <td className="px-3 py-2.5"><GoalsCell t={t} /></td>
              <td className="px-3 py-2.5"><OuCell t={t} /></td>
              <td className="px-3 py-2.5"><BttsCell t={t} /></td>
              <td className="px-3 py-2.5"><CornersCell t={t} /></td>
              <td className="px-3 py-2.5"><CardsCell t={t} /></td>
              <td className="px-3 py-2.5"><PossessionCell t={t} /></td>
              <td className="px-3 py-2.5"><FormCell t={t} /></td>
              <td className="px-3 py-2.5 max-w-[220px]">
                {t.hot_stat ? (
                  <span className="italic text-zinc-400 text-[11px] line-clamp-2 block">
                    {t.hot_stat}
                  </span>
                ) : (
                  <Dash />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Top Picks
// ----------------------------------------------------------------------------

function TopPickCard({ p }: { p: WCTopPick }) {
  return (
    <div
      className="border border-white/[0.06] rounded-xl p-4 bg-[#111114]"
      style={{ borderLeft: `3px solid ${SIGNAL_VAR[p.signal]}` }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="font-mono text-[11px] font-bold rounded-md px-1.5 py-0.5 text-zinc-100"
          style={{ backgroundColor: tint('var(--color-success)', 12) }}
        >
          #{p.rank}
        </span>
        <span className="text-xl leading-none">{p.flag}</span>
        <span className="font-bold text-zinc-100 truncate">{p.team}</span>
      </div>
      <span
        className="inline-block text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 mb-2 text-zinc-200"
        style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}
      >
        {p.label}
      </span>
      <p className="text-xs leading-snug" style={{ color: SIGNAL_VAR.green }}>
        {p.hot_stat}
      </p>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Skeleton + error
// ----------------------------------------------------------------------------

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-10 bg-white/[0.04] rounded-lg w-2/3" />
      <div className="h-16 bg-white/[0.04] rounded-lg" />
      <div className="flex gap-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-8 w-20 bg-white/[0.04] rounded-md" />
        ))}
      </div>
      <div className="h-64 bg-white/[0.04] rounded-xl" />
    </div>
  );
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-ES', {
      dateStyle: 'long',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

// ----------------------------------------------------------------------------
// Página
// ----------------------------------------------------------------------------

export default function WorldCupPage() {
  const [data, setData] = useState<WCDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeGroup, setActiveGroup] = useState('A');

  const load = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getWorldCupDashboard()
      .then((res) => {
        if (cancelled) return;
        setData(res);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        console.error('World Cup dashboard fetch failed', err);
        setError(
          'No se pudo cargar el dashboard del Mundial. Verifica que el backend FastAPI esté activo.',
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => load(), [load]);

  const activeTeams = useMemo(
    () => data?.groups.find((g) => g.group === activeGroup)?.teams ?? [],
    [data, activeGroup],
  );

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-zinc-100">
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-6 space-y-5">
        {/* 1. Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 mb-2 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Volver al dashboard
            </Link>
            <h1 className="font-sans text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
              <Trophy className="w-6 h-6" style={{ color: SIGNAL_VAR.green }} />
              Mundial 2026 — Análisis por Grupo
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              Estadísticas, forma reciente y picks sugeridos · Solo para entretenimiento
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-2 h-[38px] px-4 rounded-md bg-white/5 border border-white/[0.08] text-zinc-200 hover:bg-white/10 hover:text-white text-sm font-semibold transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>

        {/* 2. Color legend */}
        <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-3">
          <div className="flex flex-wrap items-center gap-2">
            <LegendPill signal="green" label="Verde = Favorable / Victoria esperada" />
            <LegendPill signal="yellow" label="Amarillo = Neutro / Empate probable" />
            <LegendPill signal="red" label="Rojo = En contra / Derrota estimada" />
          </div>
          <p className="text-[11px] text-zinc-500 mt-2">
            Los colores reflejan la señal combinada de forma, goles y probabilidad estimada
          </p>
        </div>

        {/* 3. Disclaimer */}
        <div
          className="rounded-xl p-3 text-[13px] leading-snug"
          style={{
            backgroundColor: tint('var(--color-warning)', 12),
            border: `1px solid ${tint('var(--color-warning)', 35)}`,
            color: 'var(--color-warning)',
          }}
        >
          ⚠ Las probabilidades son estimaciones propias basadas en forma reciente y modelo Poisson
          — NO son datos oficiales ni cuotas de apuestas. Esto es solo para entretenimiento.
        </div>

        {loading && !data ? (
          <Skeleton />
        ) : error ? (
          <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-8 text-center">
            <p className="text-sm text-zinc-400 mb-4">{error}</p>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 h-[38px] px-4 rounded-md bg-white/10 border border-white/[0.08] text-white text-sm font-semibold hover:bg-white/15 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Reintentar
            </button>
          </div>
        ) : data ? (
          <>
            {/* 4. Group tabs */}
            <div className="flex gap-1.5 overflow-x-auto scrollbar-hide pb-1">
              {GROUP_LETTERS.map((letter) => {
                const active = letter === activeGroup;
                return (
                  <button
                    key={letter}
                    type="button"
                    onClick={() => setActiveGroup(letter)}
                    className={`shrink-0 px-4 h-[34px] rounded-md text-sm font-semibold transition-colors border ${
                      active
                        ? 'bg-white text-[#0a0a0c] border-white'
                        : 'bg-white/5 text-zinc-300 border-white/[0.08] hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    Grupo {letter}
                  </button>
                );
              })}
            </div>

            {/* 5. Group stats table */}
            <GroupTable teams={activeTeams} />

            {/* 6. Top Picks */}
            <section className="pt-2">
              <h2 className="font-sans text-lg font-bold tracking-tight mb-3">
                🏆 Top Picks — Equipos en Mejor Forma
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {data.top_picks.map((p) => (
                  <TopPickCard key={p.rank} p={p} />
                ))}
              </div>
            </section>

            {/* 7. Footer */}
            <footer className="pt-4 mt-4 border-t border-white/[0.06] text-[11px] text-zinc-500 space-y-1">
              <p>Fuentes: world_cup.py fixtures · Modelo Poisson interno · The Odds API</p>
              <p>Actualizado: {fmtDate(data.generated_at)}</p>
              <p className="text-zinc-600">
                ⚠ Este informe es exclusivamente para entretenimiento. No constituye asesoramiento
                de apuestas.
              </p>
            </footer>
          </>
        ) : null}
      </div>
    </div>
  );
}

function LegendPill({ signal, label }: { signal: Signal; label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
      style={{
        backgroundColor: tint(SIGNAL_VAR[signal], 12),
        color: SIGNAL_VAR[signal],
        border: `1px solid ${tint(SIGNAL_VAR[signal], 35)}`,
      }}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: SIGNAL_VAR[signal] }} />
      {label}
    </span>
  );
}
