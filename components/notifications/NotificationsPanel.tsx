'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Award, Bell, CheckCircle2, Gift, Sparkles } from 'lucide-react';

interface Notification {
  id: string;
  kind: 'rank' | 'reward' | 'pick' | 'system';
  title: string;
  body: string;
  time: string;
  href?: string;
  unread?: boolean;
}

const SAMPLE: Notification[] = [
  {
    id: 'n1',
    kind: 'rank',
    title: 'Subiste a Estratega',
    body: 'Desbloqueaste 1 pick Premium gratis al mes.',
    time: 'hace 2h',
    href: '/dashboard/profile',
    unread: true,
  },
  {
    id: 'n2',
    kind: 'reward',
    title: 'Pick gratis disponible',
    body: 'Aplicalo a cualquier match con edge ≥ 5%.',
    time: 'hace 5h',
    href: '/dashboard',
    unread: true,
  },
  {
    id: 'n3',
    kind: 'pick',
    title: 'Pick del día publicado',
    body: 'Real Madrid vs. Barça · EV +12.4%',
    time: 'ayer',
    href: '/dashboard/pick-del-dia',
  },
  {
    id: 'n4',
    kind: 'system',
    title: 'Nuevo sistema de rangos',
    body: 'Ahora podés ver tu progreso y recompensas en tu perfil.',
    time: 'ayer',
    href: '/dashboard/profile',
  },
];

const ICON: Record<Notification['kind'], JSX.Element> = {
  rank: <Award className="w-4 h-4 text-emerald-400" />,
  reward: <Gift className="w-4 h-4 text-amber-300" />,
  pick: <Sparkles className="w-4 h-4 text-sky-400" />,
  system: <CheckCircle2 className="w-4 h-4 text-zinc-400" />,
};

export default function NotificationsPanel() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>(SAMPLE);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    window.addEventListener('keydown', onEsc);
    return () => {
      window.removeEventListener('mousedown', onClick);
      window.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const unreadCount = items.filter((n) => n.unread).length;

  const markAllRead = () => setItems((prev) => prev.map((n) => ({ ...n, unread: false })));
  const markRead = (id: string) =>
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, unread: false } : n)));

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative w-[34px] h-[34px] rounded-md bg-white/5 border border-white/[0.08] flex items-center justify-center text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
        aria-label="Notificaciones"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[16px] h-[16px] px-1 rounded-full bg-emerald-400 text-[10px] font-mono font-bold text-[#0a0a0c] flex items-center justify-center"
            aria-label={`${unreadCount} no leídas`}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-[42px] w-[340px] max-w-[calc(100vw-2rem)] rounded-xl bg-[#111114] border border-white/[0.08] shadow-2xl shadow-black/40 overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
            <span className="font-sans font-bold text-[13px] text-white">Notificaciones</span>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={markAllRead}
                className="font-sans text-[11px] text-zinc-400 hover:text-white"
              >
                Marcar todas
              </button>
            )}
          </div>
          <ul className="max-h-[420px] overflow-y-auto">
            {items.length === 0 && (
              <li className="px-4 py-8 text-center font-sans text-[12px] text-zinc-500">
                Sin notificaciones.
              </li>
            )}
            {items.map((n) => {
              const inner = (
                <div
                  className={`px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors flex gap-3 ${
                    n.unread ? 'bg-white/[0.02]' : ''
                  }`}
                >
                  <div className="w-7 h-7 rounded-md bg-white/5 flex items-center justify-center shrink-0">
                    {ICON[n.kind]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-sans font-semibold text-[13px] text-white truncate">
                        {n.title}
                      </span>
                      {n.unread && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />}
                    </div>
                    <p className="font-sans text-[12px] text-zinc-400 mt-0.5">{n.body}</p>
                    <span className="font-mono text-[10px] text-zinc-600 mt-1 inline-block">
                      {n.time}
                    </span>
                  </div>
                </div>
              );
              return (
                <li key={n.id}>
                  {n.href ? (
                    <Link href={n.href} onClick={() => { markRead(n.id); setOpen(false); }}>
                      {inner}
                    </Link>
                  ) : (
                    <button type="button" onClick={() => markRead(n.id)} className="w-full text-left">
                      {inner}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          <div className="px-4 py-3 border-t border-white/[0.06]">
            <Link
              href="/dashboard/profile"
              onClick={() => setOpen(false)}
              className="font-sans text-[12px] font-semibold text-zinc-300 hover:text-white"
            >
              Ver historial completo →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
