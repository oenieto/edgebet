'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Crown, LogOut, TrendingUp, Trophy, ArrowLeft, Menu, X } from 'lucide-react';
import { useState } from 'react';
import useSWR from 'swr';

import { useAuth } from '@/contexts/AuthContext';
import NotificationBell from '@/components/notifications/NotificationBell';
import { apiFetch } from '@/lib/api/client';

const NAV = [
  { label: 'Todos los análisis', href: '/dashboard', match: 'exact' as const },
  {
    label: 'Bankroll',
    href: '/dashboard/bankroll',
    icon: <TrendingUp className="w-3.5 h-3.5" />,
    match: 'prefix' as const,
  },
  {
    label: 'Pick del día',
    href: '/dashboard/pick-del-dia',
    icon: <Crown className="w-3.5 h-3.5" />,
    match: 'prefix' as const,
  },
  { label: 'Promos', href: '/dashboard/promos', match: 'prefix' as const },
  { label: 'Parlays', href: '/dashboard/parlays', match: 'prefix' as const },
  { label: 'Historial', href: '/dashboard/history', match: 'prefix' as const },
  {
    label: 'Mundial 2026',
    href: '/world-cup',
    icon: <Trophy className="w-3.5 h-3.5" />,
    match: 'prefix' as const,
    live: true,
  },
];

function LiveDot() {
  return (
    <span className="relative inline-flex w-2 h-2 ml-0.5">
      <span className="absolute inline-flex w-full h-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
      <span className="relative inline-flex w-2 h-2 rounded-full bg-emerald-500" />
    </span>
  );
}

function WCHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const { data: liveData } = useSWR('/world-cup/live', () => 
    apiFetch<{ fixtures: any[] }>('/world-cup/live').catch(() => ({ fixtures: [] })),
    { refreshInterval: 15000 }
  );

  const isLive = liveData?.fixtures && liveData.fixtures.length > 0;

  const wcNav = [
    { label: 'Grupos', href: '/world-cup', match: 'exact' },
    { label: 'Partidos', href: '/world-cup/matches', match: 'prefix' },
    { label: 'Predicciones', href: '/world-cup/predictions', match: 'prefix' },
    { label: 'Tabla', href: '/world-cup/standings', match: 'prefix' },
  ];

  return (
    <header 
      className="sticky top-0 z-50 bg-[#1A1A2E] border-b border-[#C8A951]/25 wc-theme"
      style={{
        backgroundImage: 'repeating-linear-gradient(45deg, rgba(200, 169, 81, 0.03), rgba(200, 169, 81, 0.03) 12px, transparent 12px, transparent 24px)',
        height: '72px'
      }}
    >
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 lg:px-8 h-full flex items-center justify-between gap-6">
        {/* Left: FIFA Logo Treatment */}
        <div className="flex items-center gap-4 h-full">
          <Link href="/world-cup" className="flex items-center gap-3 group">
            <Trophy className="w-7 h-7 text-[#C8A951] shrink-0 animate-pulse" />
            <div className="flex flex-col">
              <span className="text-[10px] tracking-[0.2em] text-[#C8A951] font-bold uppercase leading-none mb-1">
                FIFA WORLD CUP
              </span>
              <span className="text-2xl font-black text-white leading-none">
                2026
              </span>
            </div>
          </Link>
          
          {/* Vertical gold divider */}
          <div className="hidden md:block w-px h-8 bg-[#C8A951]/30 ml-2" />
          
          {/* Center Navigation (Desktop) */}
          <nav className="hidden md:flex items-center gap-1 h-full ml-4">
            {wcNav.map((item) => {
              const active = item.match === 'exact' 
                ? pathname === item.href 
                : pathname.startsWith(item.href) && (item.href !== '/world-cup' || pathname === '/world-cup');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative px-4 h-[72px] flex items-center font-sans text-[13px] font-bold tracking-tight transition-colors ${
                    active ? 'text-[#C8A951]' : 'text-white/70 hover:text-white'
                  }`}
                >
                  {item.label}
                  {active && (
                    <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#C8A951]" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: Live Indicator + Back to Dashboard */}
        <div className="flex items-center gap-4">
          {/* Live indicator */}
          {isLive && (
            <div className="flex items-center gap-1.5 bg-[#E63946]/10 border border-[#E63946]/30 px-3 py-1 rounded-full text-[#E63946] text-xs font-bold shrink-0">
              <span className="relative inline-flex w-2 h-2">
                <span className="absolute inline-flex w-full h-full rounded-full bg-[#E63946] opacity-75 animate-ping" />
                <span className="relative inline-flex w-2 h-2 rounded-full bg-[#E63946]" />
              </span>
              <span>EN VIVO</span>
            </div>
          )}

          {/* Return link */}
          <Link
            href="/dashboard"
            className="hidden sm:flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
          </Link>

          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 text-white/70 hover:text-white rounded-md bg-white/5 border border-white/10"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {menuOpen && (
        <div className="md:hidden fixed inset-0 top-[72px] z-40 bg-[#1A1A2E] flex flex-col p-6 border-t border-[#C8A951]/20">
          <nav className="flex flex-col gap-4">
            {wcNav.map((item) => {
              const active = item.match === 'exact' 
                ? pathname === item.href 
                : pathname.startsWith(item.href) && (item.href !== '/world-cup' || pathname === '/world-cup');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className={`text-lg font-bold py-2 border-b border-white/5 transition-colors ${
                    active ? 'text-[#C8A951]' : 'text-white/70'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
            
            <Link
              href="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-white/50 hover:text-white py-4 mt-4 text-sm"
            >
              <ArrowLeft className="w-4 h-4" /> Volver al Dashboard Principal
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

export default function AppHeader() {
  const pathname = usePathname();

  if (pathname.startsWith('/world-cup')) {
    return <WCHeader />;
  }

  return (
    <header className="sticky top-0 z-50 bg-[#0a0a0c]/95 backdrop-blur-md border-b border-white/[0.06]">
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 lg:px-8">
        <div className="h-[64px] flex items-center justify-between gap-6">
          <Link href="/dashboard" className="flex items-center gap-2.5 shrink-0 group">
            <Image
              src="/inverso.png"
              alt="Edgebet"
              width={160}
              height={40}
              priority
              className="h-[36px] w-auto object-cover"
              style={{ clipPath: 'inset(0px 0px 10px 0px)' }}
            />
          </Link>

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
                  {(item as { live?: boolean }).live && <LiveDot />}
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
            <div className="hidden sm:block">
              <NotificationBell />
            </div>

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
                {(item as { live?: boolean }).live && <LiveDot />}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
