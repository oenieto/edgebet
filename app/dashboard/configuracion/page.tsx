'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/contexts/AuthContext';
import { getBankrollSummary, setupBankroll, type BankrollSummary } from '@/lib/api/bankroll';

const TOGGLES = [
  { key: 'notif_new_pick', label: 'Nuevo pick disponible' },
  { key: 'notif_settled', label: 'Pick liquidado' },
  { key: 'notif_weekly', label: 'Resumen semanal' },
] as const;

const INPUT = 'w-full h-[38px] px-3 rounded-lg bg-white/[0.04] border border-white/10 text-white text-sm focus:outline-none focus:border-white/25';
const CARD = 'rounded-xl border border-white/[0.06] bg-[#111114] p-5';
const LABEL = 'text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-500 mb-3';

export default function ConfiguracionPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<BankrollSummary | null>(null);
  const [toggles, setToggles] = useState<Record<string, boolean>>({});
  const [resetOpen, setResetOpen] = useState(false);

  useEffect(() => {
    getBankrollSummary(token).then(setSummary).catch(() => setSummary(null));
    const stored: Record<string, boolean> = {};
    for (const t of TOGGLES) stored[t.key] = localStorage.getItem(t.key) === 'true';
    setToggles(stored);
  }, [token]);

  const flip = (key: string) => {
    setToggles((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem(key, String(next[key]));
      return next;
    });
  };

  const doReset = async () => {
    if (!summary) return;
    await setupBankroll(token, { initial_capital: summary.initial_capital || 1000, currency: summary.currency || 'USD' });
    setResetOpen(false);
    router.push('/dashboard/bankroll');
  };

  const configured = summary?.configured !== false && summary != null;

  return (
    <div className="max-w-[760px] mx-auto px-4 md:px-6 lg:px-8 py-8 space-y-5">
      <h1 className="font-sans text-2xl font-bold tracking-tight">Configuración</h1>

      {/* Cuenta */}
      <div className={CARD}>
        <div className={LABEL}>Cuenta</div>
        <label className="block text-xs text-zinc-400 mb-1">Nombre</label>
        <input className={INPUT} defaultValue={user?.name ?? ''} />
        <label className="block text-xs text-zinc-400 mb-1 mt-3">Email</label>
        <input className={`${INPUT} opacity-60`} value={user?.email ?? ''} readOnly />
        <p className="text-[11px] text-zinc-600 mt-2">El email no se puede modificar.</p>
      </div>

      {/* Bankroll */}
      <div className={CARD}>
        <div className={LABEL}>Bankroll</div>
        {configured ? (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="text-sm text-zinc-300">
              Capital: <span className="font-mono font-semibold text-white">{summary?.current_balance?.toFixed(2)} {summary?.currency}</span>
            </div>
            <button onClick={() => setResetOpen(true)} className="h-9 px-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-[13px] font-semibold hover:bg-red-500/20">
              Reiniciar bankroll
            </button>
          </div>
        ) : (
          <a href="/dashboard/bankroll" className="text-sm text-emerald-300">Configura tu bankroll →</a>
        )}
      </div>

      {/* Notificaciones */}
      <div className={CARD}>
        <div className={LABEL}>Notificaciones</div>
        <div className="space-y-2">
          {TOGGLES.map((t) => (
            <button key={t.key} onClick={() => flip(t.key)} className="w-full flex items-center justify-between py-1.5">
              <span className="text-sm text-zinc-300">{t.label}</span>
              <span className={`w-10 h-6 rounded-full transition-colors relative ${toggles[t.key] ? 'bg-emerald-500' : 'bg-white/10'}`}>
                <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${toggles[t.key] ? 'left-[18px]' : 'left-0.5'}`} />
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Plan */}
      <div className={CARD}>
        <div className={LABEL}>Plan</div>
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm uppercase tracking-widest text-amber-300">Plan {user?.tier ?? 'free'}</span>
          <span className="text-[12px] text-zinc-500">Mejorar plan — próximamente</span>
        </div>
      </div>

      {resetOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60" onClick={() => setResetOpen(false)}>
          <div className="w-full max-w-sm rounded-xl border border-white/[0.08] bg-[#111114] p-5" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-bold mb-2">¿Seguro?</h3>
            <p className="text-sm text-zinc-400 mb-4">Esto borrará tu historial de movimientos y reiniciará el balance.</p>
            <div className="flex gap-2">
              <button onClick={doReset} className="flex-1 h-9 rounded-lg bg-red-500/15 border border-red-500/25 text-red-300 text-sm font-semibold">Reiniciar</button>
              <button onClick={() => setResetOpen(false)} className="h-9 px-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300 text-sm">Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
