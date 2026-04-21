'use client';

import Link from 'next/link';
import { CheckCircle2, Crown, Mail, Shield, User } from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';

export default function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;

  const tierClass =
    user.tier === 'vip'
      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
      : user.tier === 'pro'
        ? 'bg-white/10 text-white border border-white/[0.08]'
        : 'bg-white/5 text-zinc-400 border border-white/[0.06]';

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="font-sans font-extrabold text-[28px] text-white tracking-tight">
          Tu perfil
        </h1>
        <p className="font-sans text-[14px] text-zinc-400 mt-1">
          Datos de cuenta, plan y preferencias.
        </p>
      </div>

      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6 md:p-8 flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-white text-[#0a0a0c] flex items-center justify-center font-mono text-[22px] font-bold">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="font-sans font-bold text-[18px] text-white">{user.name}</div>
            <div className="font-sans text-[13px] text-zinc-400">{user.email}</div>
          </div>
          <span
            className={`ml-auto font-mono text-[10px] uppercase tracking-widest px-2.5 py-1 rounded-full ${tierClass}`}
          >
            {user.tier}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <InfoRow icon={<User className="w-4 h-4" />} label="Nombre" value={user.name} />
          <InfoRow icon={<Mail className="w-4 h-4" />} label="Email" value={user.email} />
          <InfoRow
            icon={<Shield className="w-4 h-4" />}
            label="Tier actual"
            value={user.tier.toUpperCase()}
          />
          <InfoRow
            icon={<CheckCircle2 className="w-4 h-4" />}
            label="Miembro desde"
            value={user.created_at.slice(0, 10)}
          />
        </div>
      </div>

      {user.tier !== 'vip' && (
        <div className="mt-5 bg-gradient-to-r from-amber-300 to-amber-500 text-[#0a0a0c] rounded-2xl p-6 md:p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Crown className="w-5 h-5" />
              <span className="font-sans font-extrabold text-[17px]">
                Desbloquea el Pick del día
              </span>
            </div>
            <p className="font-sans text-[13px] opacity-80">
              Upgrade a VIP para acceso al pick exclusivo + todos los picks con edge ≥ 8%.
            </p>
          </div>
          <Link
            href="/pricing"
            className="px-5 h-[44px] flex items-center bg-[#0a0a0c] text-amber-300 rounded-full font-sans font-bold text-[14px] hover:bg-black transition-colors"
          >
            Ver planes
          </Link>
        </div>
      )}
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-[#16161a] border border-white/[0.06] rounded-xl p-4">
      <div className="flex items-center gap-2 text-zinc-500 text-[10px] font-medium uppercase tracking-widest mb-1">
        {icon}
        {label}
      </div>
      <div className="font-sans font-semibold text-[14px] text-white">{value}</div>
    </div>
  );
}
