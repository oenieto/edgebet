'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Crown, LogOut, Mail, Pencil, Settings, Shield, User } from 'lucide-react';

import Avatar from '@/components/profile/Avatar';
import AvatarPicker from '@/components/profile/AvatarPicker';
import RankBadge from '@/components/profile/RankBadge';
import RankCard from '@/components/profile/RankCard';
import RewardsList from '@/components/profile/RewardsList';
import { useAuth } from '@/contexts/AuthContext';
import { getProgressToNext } from '@/lib/ranking/tiers';
import { useProfileVisuals } from '@/lib/ranking/store';
import { useUserStore } from '@/lib/store/userStore';

type Section = 'overview' | 'rank' | 'rewards' | 'avatar' | 'settings';

const TABS: { id: Section; label: string }[] = [
  { id: 'overview', label: 'Resumen' },
  { id: 'rank', label: 'Rango' },
  { id: 'rewards', label: 'Recompensas' },
  { id: 'avatar', label: 'Avatar' },
  { id: 'settings', label: 'Configuración' },
];

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const visuals = useProfileVisuals();
  const [tab, setTab] = useState<Section>('overview');

  useEffect(() => {
    const t = searchParams.get('tab') as Section | null;
    if (t && TABS.some((x) => x.id === t)) setTab(t);
  }, [searchParams]);

  if (!user) return null;

  const initials = user.name
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('');

  const { profile } = useUserStore();
  const xp = profile?.xp ?? visuals.xp;
  const { current: rank } = getProgressToNext(xp);

  const tierClass =
    user.tier === 'vip'
      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
      : user.tier === 'pro'
        ? 'bg-white/10 text-white border border-white/[0.08]'
        : 'bg-white/5 text-zinc-400 border border-white/[0.06]';

  const onLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 lg:px-8 py-10">
      <header className="flex items-center gap-5 mb-8">
        <Avatar
          presetId={visuals.avatarPresetId}
          customDataUrl={visuals.avatarCustomData}
          initials={initials}
          size={88}
          ringColor={rank.color}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h1 className="font-sans font-extrabold text-[24px] md:text-[28px] text-white tracking-tight truncate">
              {user.name}
            </h1>
            <RankBadge rank={rank} size="sm" />
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-sans text-[13px] text-zinc-400">{user.email}</span>
            <span className={`font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full ${tierClass}`}>
              Plan {user.tier}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setTab('avatar')}
          className="hidden md:inline-flex items-center gap-2 h-[36px] px-4 rounded-full bg-white/5 border border-white/[0.08] text-zinc-300 font-sans text-[12px] font-semibold hover:bg-white/10 hover:text-white transition-colors"
        >
          <Pencil className="w-3.5 h-3.5" />
          Editar
        </button>
      </header>

      <nav className="flex gap-1 overflow-x-auto scrollbar-hide -mx-1 px-1 mb-6 border-b border-white/[0.06]">
        {TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`relative px-4 h-[40px] flex items-center font-sans text-[13px] font-semibold tracking-tight whitespace-nowrap transition-colors ${
                active ? 'text-white' : 'text-zinc-400 hover:text-white'
              }`}
            >
              {t.label}
              {active && (
                <span className="absolute -bottom-[1px] left-3 right-3 h-[2px] rounded-full bg-white" />
              )}
            </button>
          );
        })}
      </nav>

      {tab === 'overview' && <OverviewSection user={user} xp={xp} />}
      {tab === 'rank' && <RankCard xp={xp} />}
      {tab === 'rewards' && <RewardsList currentRankId={rank.id} />}
      {tab === 'avatar' && (
        <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6 md:p-8">
          <h2 className="font-sans font-bold text-[16px] text-white mb-1">Tu avatar</h2>
          <p className="font-sans text-[12px] text-zinc-400 mb-6">
            Subí tu foto o elegí uno de la galería. Inspirado en el estilo OneFootball.
          </p>
          <AvatarPicker
            presetId={visuals.avatarPresetId}
            customDataUrl={visuals.avatarCustomData}
            initials={initials}
            ringColor={rank.color}
            onSelectPreset={visuals.selectPreset}
            onUploadCustom={visuals.setCustomAvatar}
            onClear={visuals.clearAvatar}
          />
        </div>
      )}
      {tab === 'settings' && <SettingsSection user={user} onLogout={onLogout} />}
    </div>
  );
}

function OverviewSection({
  user,
  xp,
}: {
  user: { name: string; email: string; tier: string; created_at: string };
  xp: number;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">
      <div className="flex flex-col gap-5">
        <RankCard xp={xp} />

        <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-sans font-bold text-[16px] text-white">Datos de cuenta</h2>
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              Editables
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <InfoRow icon={<User className="w-4 h-4" />} label="Nombre" value={user.name} />
            <InfoRow icon={<Mail className="w-4 h-4" />} label="Email" value={user.email} />
            <InfoRow
              icon={<Shield className="w-4 h-4" />}
              label="Plan"
              value={user.tier.toUpperCase()}
            />
            <InfoRow
              icon={<Settings className="w-4 h-4" />}
              label="Miembro desde"
              value={user.created_at.slice(0, 10)}
            />
          </div>
        </div>
      </div>

      <aside className="flex flex-col gap-5">
        {user.tier !== 'vip' && (
          <div className="bg-gradient-to-br from-amber-300 to-amber-500 text-[#0a0a0c] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-1">
              <Crown className="w-4 h-4" />
              <span className="font-sans font-extrabold text-[14px]">Upgrade a VIP</span>
            </div>
            <p className="font-sans text-[12px] opacity-80 mb-3">
              Análisis Claude, alertas Telegram y picks con edge ≥ 8%.
            </p>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center w-full h-[40px] rounded-full bg-[#0a0a0c] text-amber-300 font-sans font-bold text-[13px] hover:bg-black transition-colors"
            >
              Ver planes
            </Link>
          </div>
        )}

        <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-5">
          <h3 className="font-sans font-bold text-[13px] text-white mb-3">Atajos</h3>
          <div className="flex flex-col gap-1.5">
            <Link
              href="/dashboard/promos"
              className="font-sans text-[12px] text-zinc-300 hover:text-white"
            >
              Ofertas y promos →
            </Link>
            <Link
              href="/dashboard/history"
              className="font-sans text-[12px] text-zinc-300 hover:text-white"
            >
              Historial completo →
            </Link>
            <Link
              href="/dashboard/pick-del-dia"
              className="font-sans text-[12px] text-zinc-300 hover:text-white"
            >
              Pick del día →
            </Link>
          </div>
        </div>
      </aside>
    </div>
  );
}

function SettingsSection({
  user,
  onLogout,
}: {
  user: { name: string; email: string };
  onLogout: () => void;
}) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const onSave = () => {
    setSavedAt(Date.now());
    setTimeout(() => setSavedAt(null), 3000);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6">
        <h2 className="font-sans font-bold text-[16px] text-white mb-1">Datos personales</h2>
        <p className="font-sans text-[12px] text-zinc-400 mb-5">
          Cambiá tu nombre o email. El email se usa para alertas y recibos.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Nombre">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full h-[44px] px-3 rounded-lg bg-[#16161a] border border-white/[0.08] text-white font-sans text-[14px] focus:outline-none focus:border-white/20"
            />
          </Field>
          <Field label="Email">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-[44px] px-3 rounded-lg bg-[#16161a] border border-white/[0.08] text-white font-sans text-[14px] focus:outline-none focus:border-white/20"
            />
          </Field>
        </div>
        <div className="mt-5 flex items-center gap-3">
          <button
            type="button"
            onClick={onSave}
            className="h-[40px] px-5 rounded-full bg-white text-[#0a0a0c] font-sans font-bold text-[13px] hover:bg-zinc-200 transition-colors"
          >
            Guardar cambios
          </button>
          {savedAt && (
            <span className="font-sans text-[12px] text-emerald-400">Guardado ✓</span>
          )}
        </div>
      </div>

      <div className="bg-[#111114] border border-white/[0.06] rounded-2xl p-6">
        <h2 className="font-sans font-bold text-[16px] text-white mb-1">Seguridad</h2>
        <p className="font-sans text-[12px] text-zinc-400 mb-5">
          Cerrá sesión en este dispositivo o cambiá tu password.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled
            className="h-[40px] px-5 rounded-full bg-white/5 border border-white/[0.08] text-zinc-500 font-sans font-semibold text-[13px] cursor-not-allowed"
            title="Próximamente"
          >
            Cambiar password
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex items-center gap-2 h-[40px] px-5 rounded-full bg-red-500/10 border border-red-500/30 text-red-300 font-sans font-semibold text-[13px] hover:bg-red-500/20 hover:text-red-200 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold">
        {label}
      </span>
      {children}
    </label>
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
      <div className="font-sans font-semibold text-[14px] text-white truncate">{value}</div>
    </div>
  );
}
