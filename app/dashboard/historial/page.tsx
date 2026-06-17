'use client';

import { useEffect, useMemo, useState } from 'react';

import { getRecentPredictions, type PredictionRow } from '@/lib/api/predictions';

const PER_PAGE = 20;

export default function HistorialPage() {
  const [rows, setRows] = useState<PredictionRow[] | null>(null);
  const [league, setLeague] = useState<string>('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    getRecentPredictions(90, 1000).then((r) => setRows(r.predictions)).catch(() => setRows([]));
  }, []);

  const leagues = useMemo(
    () => Array.from(new Set((rows ?? []).map((r) => r.league).filter(Boolean))) as string[],
    [rows],
  );
  const filtered = useMemo(
    () => (rows ?? []).filter((r) => !league || r.league === league),
    [rows, league],
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const pageRows = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  return (
    <div className="max-w-[1100px] mx-auto px-4 md:px-6 lg:px-8 py-8">
      <h1 className="font-sans text-2xl font-bold tracking-tight mb-1">Historial de picks</h1>
      <p className="text-sm text-zinc-500 mb-4">Todas las predicciones de los últimos 90 días</p>

      <div className="flex items-center gap-2 mb-3">
        <select
          value={league}
          onChange={(e) => { setLeague(e.target.value); setPage(1); }}
          className="h-9 px-3 rounded-lg bg-white/[0.04] border border-white/10 text-white text-sm"
        >
          <option value="">Todas las ligas</option>
          {leagues.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <span className="text-xs text-zinc-500">{filtered.length} predicciones</span>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-[#111114] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-zinc-500">
                <th className="px-4 py-2 font-bold">Fecha</th>
                <th className="px-4 py-2 font-bold">Partido</th>
                <th className="px-4 py-2 font-bold">Liga</th>
                <th className="px-4 py-2 font-bold">Recom.</th>
                <th className="px-4 py-2 font-bold text-right">Prob</th>
                <th className="px-4 py-2 font-bold text-right">EV</th>
              </tr>
            </thead>
            <tbody>
              {rows === null ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-500">Cargando…</td></tr>
              ) : pageRows.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-500">Sin predicciones todavía.</td></tr>
              ) : (
                pageRows.map((r, i) => (
                  <tr key={i} className="border-t border-white/[0.04]">
                    <td className="px-4 py-2.5 text-zinc-400 whitespace-nowrap">{r.match_date ?? '—'}</td>
                    <td className="px-4 py-2.5 text-zinc-200">{r.home_team} vs {r.away_team}</td>
                    <td className="px-4 py-2.5 text-zinc-400">{r.league ?? '—'}</td>
                    <td className="px-4 py-2.5 text-zinc-300">{r.recommended_bet ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-zinc-300">{r.prob != null ? `${(r.prob * 100).toFixed(0)}%` : '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: (r.ev ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                      {r.ev != null ? `${r.ev >= 0 ? '+' : ''}${(r.ev * 100).toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-white/[0.06] flex items-center justify-between text-xs">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="h-8 px-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300 disabled:opacity-40">Anterior</button>
            <span className="text-zinc-500">Página {page} de {totalPages}</span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="h-8 px-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300 disabled:opacity-40">Siguiente</button>
          </div>
        )}
      </div>
      <p className="text-[11px] text-zinc-600 mt-2">Resultado y P&L por pick se mostrarán cuando se enlacen las apuestas liquidadas a cada predicción.</p>
    </div>
  );
}
