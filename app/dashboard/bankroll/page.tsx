'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ArrowDownCircle,
  ArrowUpCircle,
  Flame,
  RefreshCw,
  Settings,
  Snowflake,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import {
  type BankrollSummary,
  type BankrollTransaction,
  type TxType,
  depositBankroll,
  getBankrollSummary,
  getBankrollTransactions,
  setupBankroll,
  withdrawBankroll,
} from '@/lib/api/bankroll';

const SUCCESS = 'var(--color-success)';
const DANGER = 'var(--color-danger)';

const BTN_PRIMARY =
  'h-[38px] px-4 rounded-lg bg-white/10 border border-white/[0.08] text-white text-sm font-semibold hover:bg-white/15 transition-colors';
const BTN_SOFT =
  'h-9 px-3 rounded-lg bg-white/5 border border-white/[0.08] text-zinc-200 text-[13px] font-semibold hover:bg-white/10 hover:text-white transition-colors';
const INPUT_CLS =
  'w-full h-[38px] px-3 rounded-lg bg-white/[0.04] border border-white/10 text-white text-sm focus:outline-none focus:border-white/25';

function money(n: number, currency = 'USD'): string {
  try {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency, maximumFractionDigits: 2 }).format(n);
  } catch {
    return `$${n.toFixed(2)}`;
  }
}

function shortDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  } catch {
    return iso;
  }
}

const TX_BADGE: Record<TxType, { label: string; cls: string }> = {
  deposit: { label: 'Depósito', cls: 'bg-blue-500/15 text-blue-300' },
  withdrawal: { label: 'Retiro', cls: 'bg-zinc-500/15 text-zinc-300' },
  bet_placed: { label: 'Apuesta', cls: 'bg-zinc-500/15 text-zinc-300' },
  bet_won: { label: 'Ganada', cls: 'bg-emerald-500/15 text-emerald-300' },
  bet_lost: { label: 'Perdida', cls: 'bg-red-500/15 text-red-300' },
  bet_void: { label: 'Nula', cls: 'bg-amber-500/15 text-amber-300' },
  adjustment: { label: 'Ajuste', cls: 'bg-purple-500/15 text-purple-300' },
};

// ----------------------------------------------------------------------------
export default function BankrollPage() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<BankrollSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<null | 'deposit' | 'withdraw' | 'setup'>(null);

  const loadSummary = useCallback(() => {
    setLoading(true);
    setError(null);
    getBankrollSummary(token)
      .then(setSummary)
      .catch(() => setError('No se pudo cargar el bankroll. ¿Backend activo?'))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => loadSummary(), [loadSummary]);

  const configured = summary?.configured !== false && summary != null;

  if (loading && !summary) {
    return <PageShell><Skeleton /></PageShell>;
  }
  if (error) {
    return (
      <PageShell>
        <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-8 text-center">
          <p className="text-sm text-zinc-400 mb-4">{error}</p>
          <button onClick={loadSummary} className={`${BTN_PRIMARY} inline-flex items-center gap-2`}>
            <RefreshCw className="w-3.5 h-3.5" /> Reintentar
          </button>
        </div>
      </PageShell>
    );
  }
  if (!configured) {
    return (
      <PageShell>
        <SetupCard
          token={token}
          onDone={(s) => setSummary(s)}
        />
      </PageShell>
    );
  }

  const s = summary as BankrollSummary;

  return (
    <PageShell>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
        <div>
          <h1 className="font-sans text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
            <Wallet className="w-6 h-6 text-zinc-300" /> Bankroll
          </h1>
          <p className="text-sm text-zinc-400 mt-1">Crecimiento de tu capital y rendimiento de tus predicciones</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setModal('deposit')} className={`${BTN_SOFT} inline-flex items-center gap-1.5`}>
            <ArrowDownCircle className="w-4 h-4 text-emerald-400" /> Depositar
          </button>
          <button onClick={() => setModal('withdraw')} className={`${BTN_SOFT} inline-flex items-center gap-1.5`}>
            <ArrowUpCircle className="w-4 h-4 text-zinc-300" /> Retirar
          </button>
          <button onClick={() => setModal('setup')} className={`${BTN_SOFT} inline-flex items-center gap-1.5`}>
            <Settings className="w-4 h-4 text-zinc-400" /> Configurar
          </button>
        </div>
      </div>

      {/* SECTION A — summary cards */}
      <SummaryCards s={s} />

      {/* SECTION B — equity chart */}
      <EquityChart s={s} />

      {/* SECTION C — stats grid */}
      <StatsGrid s={s} />

      {/* SECTION D — transaction history */}
      <TransactionsTable token={token} reloadKey={s.current_balance} />

      {/* SECTION E — modals */}
      {modal === 'deposit' && (
        <MovementModal
          title="Depositar"
          actionLabel="Depositar"
          onClose={() => setModal(null)}
          onSubmit={(amount, note) => depositBankroll(token, { amount, note })}
          onDone={(res) => { setSummary(res); setModal(null); }}
        />
      )}
      {modal === 'withdraw' && (
        <MovementModal
          title="Retirar"
          actionLabel="Retirar"
          max={s.current_balance}
          onClose={() => setModal(null)}
          onSubmit={(amount, note) => withdrawBankroll(token, { amount, note })}
          onDone={(res) => { setSummary(res); setModal(null); }}
        />
      )}
      {modal === 'setup' && (
        <SetupModal
          token={token}
          onClose={() => setModal(null)}
          onDone={(res) => { setSummary(res); setModal(null); }}
        />
      )}
    </PageShell>
  );
}

// ----------------------------------------------------------------------------
function PageShell({ children }: { children: React.ReactNode }) {
  return <div className="max-w-[1200px] mx-auto px-4 md:px-6 lg:px-8 py-6">{children}</div>;
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-10 w-1/3 bg-white/[0.04] rounded-lg" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 bg-white/[0.04] rounded-xl" />)}
      </div>
      <div className="h-72 bg-white/[0.04] rounded-xl" />
    </div>
  );
}

// SECTION A
function SummaryCards({ s }: { s: BankrollSummary }) {
  const up = s.current_balance >= s.initial_capital;
  const roiUp = s.roi >= 0;
  const streak = s.current_streak;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <Card title="Balance Actual">
        <div className="text-2xl font-mono font-bold" style={{ color: up ? SUCCESS : DANGER }}>
          {money(s.current_balance, s.currency)}
        </div>
        <div className="text-xs text-zinc-500 mt-1">Inicial: {money(s.initial_capital, s.currency)}</div>
      </Card>
      <Card title="ROI Total">
        <div className="text-2xl font-mono font-bold flex items-center gap-1" style={{ color: roiUp ? SUCCESS : DANGER }}>
          {roiUp ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {roiUp ? '+' : ''}{s.roi.toFixed(2)}%
        </div>
        <div className="text-xs text-zinc-500 mt-1">P&L {money(s.total_pnl, s.currency)}</div>
      </Card>
      <Card title="Tasa de Acierto">
        <div className="text-2xl font-mono font-bold text-zinc-100">{s.win_rate.toFixed(1)}%</div>
        <div className="text-xs text-zinc-500 mt-1">({s.won} G / {s.lost} P)</div>
      </Card>
      <Card title="Racha Actual">
        <div className="text-2xl font-mono font-bold flex items-center gap-1.5 text-zinc-100">
          {streak >= 3 && <Flame className="w-5 h-5 text-orange-400" />}
          {streak <= -3 && <Snowflake className="w-5 h-5 text-blue-300" />}
          {streak > 0 ? `${streak}G` : streak < 0 ? `${-streak}P` : '—'}
        </div>
        <div className="text-xs text-zinc-500 mt-1">Mejor: {s.longest_win_streak}G · Peor: {s.longest_loss_streak}P</div>
      </Card>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-4">
      <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-bold mb-2">{title}</div>
      {children}
    </div>
  );
}

// SECTION B
function EquityChart({ s }: { s: BankrollSummary }) {
  const [days, setDays] = useState<30 | 60 | 90>(90);
  const data = useMemo(() => (s.equity_log ?? []).slice(-days), [s.equity_log, days]);
  const up = s.current_balance >= s.initial_capital;
  const lineColor = up ? '#16a34a' : '#dc2626';

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-sans text-sm font-semibold text-zinc-200">Crecimiento del capital</h2>
        <div className="flex gap-1">
          {([30, 60, 90] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2.5 h-7 rounded-md text-xs font-semibold transition-colors ${
                days === d ? 'bg-white text-[#0a0a0c]' : 'bg-white/5 text-zinc-400 hover:bg-white/10'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>
      {data.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-sm text-zinc-500">
          Aún no hay historial de equity. Deposita o liquida apuestas para verlo crecer.
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fill: '#71717a', fontSize: 11 }} stroke="rgba(255,255,255,0.1)" />
              <YAxis tick={{ fill: '#71717a', fontSize: 11 }} stroke="rgba(255,255,255,0.1)" width={48}
                tickFormatter={(v) => `${Math.round(Number(v))}`} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                labelFormatter={(l) => shortDate(String(l))}
                formatter={(value) => {
                  const v = Number(value);
                  const pnl = v - s.initial_capital;
                  return [`${money(v, s.currency)} (${pnl >= 0 ? '+' : ''}${money(pnl, s.currency)})`, 'Balance'];
                }}
              />
              <ReferenceLine y={s.initial_capital} stroke="#71717a" strokeDasharray="4 4"
                label={{ value: 'Capital inicial', fill: '#71717a', fontSize: 10, position: 'insideTopRight' }} />
              <Line type="monotone" dataKey="balance" stroke={lineColor} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// SECTION C
function StatsGrid({ s }: { s: BankrollSummary }) {
  const pnlUp = s.total_pnl >= 0;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
      <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-4 space-y-2 text-sm">
        <Row label="Total apuestas" value={`${s.total_bets}`} />
        <Row label="Ganadas / Perdidas / Nulas" value={`${s.won} / ${s.lost} / ${s.void}`} />
        <Row label="Mejor racha ganadora" value={`${s.longest_win_streak} partidos`} />
        <Row label="Peor racha perdedora" value={`${s.longest_loss_streak} partidos`} />
        <Row label="Cuota promedio" value={s.avg_odds.toFixed(2)} mono />
        <Row label="Stake promedio" value={money(s.avg_stake, s.currency)} mono />
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-4 space-y-2 text-sm">
        <Row label="Mejor apuesta" value={s.best_bet ? `${s.best_bet.match} (+${money(s.best_bet.profit, s.currency)})` : '—'} />
        <Row label="Peor apuesta" value={s.worst_bet ? `${s.worst_bet.match} (${money(s.worst_bet.profit, s.currency)})` : '—'} />
        <div className="pt-2 mt-2 border-t border-white/[0.06] flex items-center justify-between">
          <span className="text-zinc-400">P&L total</span>
          <span className="font-mono font-bold" style={{ color: pnlUp ? SUCCESS : DANGER }}>
            {pnlUp ? '+' : ''}{money(s.total_pnl, s.currency)}
          </span>
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

// SECTION D
function TransactionsTable({ token, reloadKey }: { token: string | null; reloadKey: number }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ total: number; transactions: BankrollTransaction[] }>({ total: 0, transactions: [] });
  const [loading, setLoading] = useState(true);
  const limit = 20;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getBankrollTransactions(token, page, limit)
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => { if (!cancelled) setData({ total: 0, transactions: [] }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, page, reloadKey]);

  const totalPages = Math.max(1, Math.ceil(data.total / limit));

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111114] overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <h2 className="font-sans text-sm font-semibold text-zinc-200">Historial de movimientos</h2>
        <span className="text-xs text-zinc-500">{data.total} en total</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs sm:text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-zinc-500">
              <th className="px-4 py-2 font-bold">Fecha</th>
              <th className="px-4 py-2 font-bold">Tipo</th>
              <th className="px-4 py-2 font-bold">Partido / Nota</th>
              <th className="px-4 py-2 font-bold text-right">Monto</th>
              <th className="px-4 py-2 font-bold text-right">Balance</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-zinc-500">Cargando…</td></tr>
            ) : data.transactions.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-zinc-500">Sin movimientos todavía.</td></tr>
            ) : (
              data.transactions.map((t) => {
                const badge = TX_BADGE[t.type] ?? { label: t.type, cls: 'bg-zinc-500/15 text-zinc-300' };
                const credit = t.amount >= 0;
                return (
                  <tr key={t.id} className="border-t border-white/[0.04]">
                    <td className="px-4 py-2.5 text-zinc-400 whitespace-nowrap">{shortDate(t.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${badge.cls}`}>{badge.label}</span>
                    </td>
                    <td className="px-4 py-2.5 text-zinc-300 max-w-[260px] truncate">{t.note ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: credit ? SUCCESS : DANGER }}>
                      {credit ? '+' : '−'}{money(Math.abs(t.amount)).replace('-', '')}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-zinc-300">{money(t.balance_after)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-white/[0.06] flex items-center justify-between text-xs">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
            className={`${BTN_SOFT} disabled:opacity-40`}>Anterior</button>
          <span className="text-zinc-500">Página {page} de {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}
            className={`${BTN_SOFT} disabled:opacity-40`}>Siguiente</button>
        </div>
      )}
    </div>
  );
}

// SECTION E — modals
function MovementModal({
  title, actionLabel, max, onClose, onSubmit, onDone,
}: {
  title: string; actionLabel: string; max?: number;
  onClose: () => void;
  onSubmit: (amount: number, note?: string) => Promise<BankrollSummary>;
  onDone: (res: BankrollSummary) => void;
}) {
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = () => {
    const n = parseFloat(amount);
    if (!Number.isFinite(n) || n <= 0) { setErr('Monto inválido.'); return; }
    if (max != null && n > max) { setErr('Monto mayor al balance.'); return; }
    setBusy(true); setErr(null);
    onSubmit(n, note || undefined)
      .then(onDone)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : 'Error'))
      .finally(() => setBusy(false));
  };

  return (
    <ModalShell title={title} onClose={onClose}>
      <label className="block text-xs text-zinc-400 mb-1">Monto</label>
      <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} autoFocus
        className={INPUT_CLS} placeholder="0.00" />
      <label className="block text-xs text-zinc-400 mb-1 mt-3">Nota (opcional)</label>
      <input value={note} onChange={(e) => setNote(e.target.value)} className={INPUT_CLS} placeholder="Ej. Recarga abril" />
      {err && <p className="text-xs text-red-400 mt-2">{err}</p>}
      <div className="flex gap-2 mt-4">
        <button onClick={submit} disabled={busy} className={`${BTN_PRIMARY} flex-1 disabled:opacity-50`}>{actionLabel}</button>
        <button onClick={onClose} className={BTN_SOFT}>Cancelar</button>
      </div>
    </ModalShell>
  );
}

function SetupModal({ token, onClose, onDone }: { token: string | null; onClose: () => void; onDone: (res: BankrollSummary) => void }) {
  return (
    <ModalShell title="Configurar bankroll" onClose={onClose}>
      <SetupForm token={token} onDone={onDone} />
    </ModalShell>
  );
}

function SetupCard({ token, onDone }: { token: string | null; onDone: (res: BankrollSummary) => void }) {
  return (
    <div className="max-w-md mx-auto rounded-xl border border-white/[0.06] bg-[#111114] p-6 mt-10 text-center">
      <Wallet className="w-8 h-8 mx-auto text-zinc-400 mb-3" />
      <h2 className="font-sans text-lg font-bold mb-1">Configura tu bankroll</h2>
      <p className="text-sm text-zinc-400 mb-5">
        Establece tu capital inicial para rastrear el crecimiento real de tus predicciones con Kelly fraccional
      </p>
      <SetupForm token={token} onDone={onDone} />
    </div>
  );
}

function SetupForm({ token, onDone }: { token: string | null; onDone: (res: BankrollSummary) => void }) {
  const [capital, setCapital] = useState('1000');
  const [currency, setCurrency] = useState('USD');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = () => {
    const n = parseFloat(capital);
    if (!Number.isFinite(n) || n < 10) { setErr('El capital inicial mínimo es 10.'); return; }
    setBusy(true); setErr(null);
    setupBankroll(token, { initial_capital: n, currency })
      .then(onDone)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : 'Error'))
      .finally(() => setBusy(false));
  };

  return (
    <div className="text-left">
      <label className="block text-xs text-zinc-400 mb-1">Capital inicial</label>
      <input type="number" min={10} value={capital} onChange={(e) => setCapital(e.target.value)} className={INPUT_CLS} />
      <label className="block text-xs text-zinc-400 mb-1 mt-3">Moneda</label>
      <select value={currency} onChange={(e) => setCurrency(e.target.value)} className={INPUT_CLS}>
        <option value="USD">USD</option>
        <option value="MXN">MXN</option>
        <option value="EUR">EUR</option>
      </select>
      {err && <p className="text-xs text-red-400 mt-2">{err}</p>}
      <button onClick={submit} disabled={busy} className={`${BTN_PRIMARY} w-full mt-4 disabled:opacity-50`}>Comenzar a rastrear</button>
      <p className="text-[11px] text-zinc-500 text-center mt-2">Puedes modificarlo después en cualquier momento</p>
    </div>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div className="w-full max-w-sm rounded-xl border border-white/[0.08] bg-[#111114] p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-sans text-base font-bold mb-4">{title}</h3>
        {children}
      </div>
    </div>
  );
}
