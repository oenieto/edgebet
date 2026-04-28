'use client';

import Link from 'next/link';
import { ArrowLeft, ArrowUpRight, Calendar, Settings, ShieldAlert, Wallet } from 'lucide-react';

import BankrollTracker from '@/components/bankroll/BankrollTracker';
import SmartAlerts from '@/components/bankroll/SmartAlerts';
import { useUserStore } from '@/lib/store/userStore';

export default function BankPage() {
  const { profile, bankroll, weeklyUsed } = useUserStore();

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 lg:px-8 py-10">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 font-sans text-[12px] text-zinc-500 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Volver al dashboard
      </Link>

      <header className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Wallet className="w-5 h-5 text-emerald-400" />
          <h1 className="font-sans font-extrabold text-[28px] text-white tracking-tight">
            Gestión de bank
          </h1>
        </div>
        <p className="font-sans text-[14px] text-zinc-400">
          Seguí tu bankroll, configurá límites de riesgo y revisá tu PnL.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-5">
        <div className="flex flex-col gap-5">
          <BankrollTracker />
          <SmartAlerts />

          <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-zinc-400" />
                <h2 className="font-sans font-bold text-[15px] text-white">Resumen del mes</h2>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
                Vista previa
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Stat
                label="Bankroll actual"
                value={bankroll ? `$${bankroll.current_amount.toLocaleString()}` : '—'}
              />
              <Stat
                label="Inicial"
                value={bankroll ? `$${bankroll.initial_amount.toLocaleString()}` : '—'}
              />
              <Stat
                label="PnL %"
                value={
                  bankroll
                    ? `${bankroll.pnl_pct > 0 ? '+' : ''}${bankroll.pnl_pct.toFixed(1)}%`
                    : '—'
                }
                tone={bankroll ? (bankroll.pnl_pct >= 0 ? 'pos' : 'neg') : undefined}
              />
              <Stat
                label="Riesgo semanal"
                value={
                  profile
                    ? `$${weeklyUsed.toLocaleString()} / $${profile.weekly_limit.toLocaleString()}`
                    : '—'
                }
              />
            </div>
          </div>
        </div>

        <aside className="flex flex-col gap-5">
          <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5">
            <h3 className="font-sans font-bold text-[14px] text-white mb-3">Acciones rápidas</h3>
            <ul className="flex flex-col gap-2">
              <ActionItem
                href="/dashboard/profile?tab=settings"
                icon={<Settings className="w-3.5 h-3.5" />}
                label="Ajustar perfil de riesgo"
                desc="Conservador / Balanceado / Agresivo."
              />
              <ActionItem
                href="/dashboard/promos"
                icon={<ArrowUpRight className="w-3.5 h-3.5" />}
                label="Promos activas"
                desc="Revisá ofertas vigentes para sumar bankroll."
              />
            </ul>
          </div>

          <div className="bg-amber-500/[0.08] border border-amber-500/20 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <ShieldAlert className="w-4 h-4 text-amber-300" />
              <span className="font-sans font-bold text-[13px] text-amber-200">Recordatorio</span>
            </div>
            <p className="font-sans text-[12px] text-amber-100/80 leading-relaxed">
              Apostá solo lo que te puedas permitir perder. Edgebet es una herramienta de análisis,
              no garantiza resultados.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'pos' | 'neg';
}) {
  const valueClass =
    tone === 'pos' ? 'text-emerald-400' : tone === 'neg' ? 'text-red-400' : 'text-white';
  return (
    <div className="bg-[#16161a] border border-white/[0.06] rounded-xl p-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 mb-1">
        {label}
      </div>
      <div className={`font-mono font-bold text-[18px] ${valueClass}`}>{value}</div>
    </div>
  );
}

function ActionItem({
  href,
  icon,
  label,
  desc,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  desc: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="block rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-zinc-300">{icon}</span>
          <span className="font-sans font-semibold text-[13px] text-white">{label}</span>
        </div>
        <p className="font-sans text-[12px] text-zinc-400">{desc}</p>
      </Link>
    </li>
  );
}
