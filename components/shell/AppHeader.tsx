'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Crown } from 'lucide-react';

import Logo from '@/components/brand/Logo';
import NotificationsPanel from '@/components/notifications/NotificationsPanel';
import { useUserStore } from '@/lib/store/userStore';
import { getProgressToNext } from '@/lib/ranking/tiers';
import RankBadge from '@/components/profile/RankBadge';

const NAV = [
  { label: 'Todos los análisis', href: '/dashboard', match: 'exact' as const },
  {
    label: 'Pick del día',
    href: '/dashboard/pick-del-dia',
    icon: <Crown className="w-3.5 h-3.5" />,
    match: 'prefix' as const,
  },
  { label: 'Promos', href: '/dashboard/promos', match: 'prefix' as const },
  { label: 'Historial', href: '/dashboard/history', match: 'prefix' as const },
];

export default function AppHeader() {
  const pathname = usePathname();
  const profile = useUserStore((s) => s.profile);
  const xp = profile?.xp ?? 0;
  const { current: rank } = getProgressToNext(xp);

  return (
    <header className="sticky top-0 z-50 bg-[#0a0a0c]/95 backdrop-blur-md border-b border-white/[0.06]">
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 lg:px-8">
        <div className="h-[64px] flex items-center justify-between gap-6">
          <Logo variant="horizontal" theme="dark" height={48} priority />

          <nav className="hidden md:flex items-center gap-1 flex-1 justify-center">
            {NAV.map((item) => {
              const active =
                item.match === 'exact' ? pathname === item.href : pathname.startsWith(item.href);
              const isCrown = item.href === '/dashboard/pick-del-dia';
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative px-5 h-[40px] flex items-center gap-1.5 font-sans text-[13px] font-semibold tracking-tight transition-colors ${
                    active
                      ? isCrown
                        ? 'text-amber-300'
                        : 'text-white'
                      : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  {item.icon}
                  {item.label}
                  {active && (
                    <span
                      className={`absolute -bottom-[1px] left-3 right-3 h-[2px] rounded-full ${
                        isCrown ? 'bg-amber-300' : 'bg-white'
                      }`}
                    />
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <Link
              href="/dashboard/promos"
              className="hidden sm:flex items-center h-[34px] px-3 rounded-md bg-white/5 border border-white/[0.08] text-zinc-200 hover:bg-white/10 hover:text-white font-sans text-[12px] font-semibold transition-colors"
            >
              Ofertas
            </Link>
            <NotificationsPanel />
            {profile && (
              <Link href="/dashboard/profile" className="ml-2 hidden sm:flex">
                <RankBadge rank={rank} size="sm" />
              </Link>
            )}
          </div>
        </div>

        <div className="md:hidden flex gap-1 pb-2 overflow-x-auto scrollbar-hide">
          {NAV.map((item) => {
            const active =
              item.match === 'exact' ? pathname === item.href : pathname.startsWith(item.href);
            const isCrown = item.href === '/dashboard/pick-del-dia';
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`shrink-0 px-3 h-[32px] flex items-center gap-1.5 font-sans text-[12px] font-semibold rounded-md transition-colors ${
                  active
                    ? isCrown
                      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
                      : 'bg-white text-[#0a0a0c] border border-white'
                    : 'bg-white/5 text-zinc-300 border border-white/[0.08]'
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
