'use client';

import { useEffect, useState } from 'react';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { useAuth } from '@/contexts/AuthContext';
import { getBankrollSummary, type BankrollSummary } from '@/lib/api/bankroll';

const CARD = 'rounded-xl border border-white/[0.06] bg-[#111114] p-5';
const LABEL = 'text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-500 mb-3';

function money(n: number, c = 'USD') {
  try {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: c, maximumFractionDigits: 2 }).format(n);
  } catch {
    return `$${n.toFixed(2)}`;
  }
}

export default function EstadisticasPage() {
  const { token } = useAuth();
  const [s, setS] = useState<BankrollSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getBankrollSummary(token).then(setS).catch(() => setS(null)).finally(() => setLoaded(true));
  }, [token]);

  if (!loaded) return <div className="max-w-[1000px] mx-auto p-8"><div className="h-64 bg-white/[0.04] rounded-xl animate-pulse" /></div>;

  if (!s || s.configured === false) {
    return (
      <div className="max-w-[1000px] mx-auto px-4 md:px-6 lg:px-8 py-10">
        <h1 className="font-sans text-2xl font-bold mb-4">Estadísticas</h1>
        <div className={`${CARD} text-center text-sm text-zinc-400`}>
          Configura tu bankroll y registra apuestas para ver tus estadísticas. <a className="text-emerald-300" href="/dashboard/bankroll">Empezar →</a>
        </div>
      </div>
    );
  }

  const pie = [
    { name: 'Ganadas', value: s.won, color: '#16a34a' },
    { name: 'Perdidas', value: s.lost, color: '#dc2626' },
    { name: 'Nulas', value: s.void, color: '#ca8a04' },
  ].filter((d) => d.value > 0);

  return (
    <div className="max-w-[1000px] mx-auto px-4 md:px-6 lg:px-8 py-8 space-y-5">
      <h1 className="font-sans text-2xl font-bold tracking-tight">Estadísticas</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Resultado pie */}
        <div className={CARD}>
          <div className={LABEL}>Distribución de resultados</div>
          {pie.length === 0 ? (
            <p className="text-sm text-zinc-500 py-12 text-center">Aún no hay apuestas liquidadas.</p>
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pie} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                    {pie.map((d) => <Cell key={d.name} fill={d.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Stats grid */}
        <div className={`${CARD} space-y-2 text-sm`}>
          <div className={LABEL}>Resumen</div>
          <Row label="Total apuestas" value={`${s.total_bets}`} />
          <Row label="Ganadas / Perdidas / Nulas" value={`${s.won} / ${s.lost} / ${s.void}`} />
          <Row label="Tasa de acierto" value={`${s.win_rate.toFixed(1)}%`} />
          <Row label="Mejor racha ganadora" value={`${s.longest_win_streak} partidos`} />
          <Row label="Peor racha perdedora" value={`${s.longest_loss_streak} partidos`} />
          <Row label="Cuota promedio" value={s.avg_odds.toFixed(2)} mono />
          <Row label="Stake promedio" value={money(s.avg_stake, s.currency)} mono />
          <div className="pt-2 mt-2 border-t border-white/[0.06] flex items-center justify-between">
            <span className="text-zinc-400">P&L total</span>
            <span className="font-mono font-bold" style={{ color: s.total_pnl >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
              {s.total_pnl >= 0 ? '+' : ''}{money(s.total_pnl, s.currency)}
            </span>
          </div>
        </div>
      </div>

      <div className={CARD}>
        <div className={LABEL}>Mejores y peores</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-zinc-500 text-xs mb-1">Mejor apuesta</div>
            <div className="text-zinc-200">{s.best_bet ? `${s.best_bet.match} (+${money(s.best_bet.profit, s.currency)})` : '—'}</div>
          </div>
          <div>
            <div className="text-zinc-500 text-xs mb-1">Peor apuesta</div>
            <div className="text-zinc-200">{s.worst_bet ? `${s.worst_bet.match} (${money(s.worst_bet.profit, s.currency)})` : '—'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-zinc-400">{label}</span>
      <span className={`text-zinc-100 ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}
