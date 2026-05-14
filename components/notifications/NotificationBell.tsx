'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Bell, TrendingUp, Target, Trophy, Activity, X } from 'lucide-react';
import type { AppNotification } from '@/types';

const STORAGE_KEY = 'edgebet_notifications';

const ICON_MAP: Record<AppNotification['type'], React.ReactNode> = {
  high_confidence_pick: <Target className="w-4 h-4 text-emerald-400" />,
  steam_move: <TrendingUp className="w-4 h-4 text-amber-400" />,
  result_settled: <Trophy className="w-4 h-4 text-indigo-400" />,
  achievement_unlocked: <Activity className="w-4 h-4 text-purple-400" />,
};

function getStoredNotifications(): AppNotification[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : getDefaultNotifications();
  } catch {
    return getDefaultNotifications();
  }
}

function getDefaultNotifications(): AppNotification[] {
  return [
    {
      id: '1',
      type: 'high_confidence_pick',
      title: 'Pick de alta confianza',
      message: 'Arsenal vs Chelsea: 78% confianza en victoria local.',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      read: false,
      actionUrl: '/dashboard',
    },
    {
      id: '2',
      type: 'steam_move',
      title: 'Steam move detectado',
      message: 'Liverpool vs Man City: cuota home bajo de 2.10 a 1.85 en 4h.',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      read: false,
    },
    {
      id: '3',
      type: 'result_settled',
      title: 'Pick resuelto',
      message: 'Barcelona vs Sevilla: Victoria local confirmada. +$12.50 PnL.',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      read: true,
    },
  ];
}

function saveNotifications(notifs: AppNotification[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifs));
  } catch {}
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setNotifications(getStoredNotifications());
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  function markAllRead() {
    const updated = notifications.map((n) => ({ ...n, read: true }));
    setNotifications(updated);
    saveNotifications(updated);
  }

  function dismiss(id: string) {
    const updated = notifications.filter((n) => n.id !== id);
    setNotifications(updated);
    saveNotifications(updated);
  }

  function formatTime(iso: string): string {
    try {
      const diff = Date.now() - new Date(iso).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 60) return `${mins}m`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h`;
      return `${Math.floor(hrs / 24)}d`;
    } catch {
      return '';
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-400 hover:text-white hover:border-white/[0.15] transition-colors"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[9px] font-mono font-bold text-white flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-11 w-[340px] bg-[#111114] border border-white/[0.08] rounded-xl overflow-hidden z-50"
          >
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
              <h3 className="font-sans font-bold text-[13px] text-white">Notificaciones</h3>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={markAllRead}
                  className="font-sans text-[11px] text-zinc-500 hover:text-white transition-colors"
                >
                  Marcar todo leido
                </button>
              )}
            </div>

            <div className="max-h-[360px] overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <Bell className="w-6 h-6 text-zinc-600 mx-auto mb-2" />
                  <p className="font-sans text-[12px] text-zinc-500">Sin notificaciones</p>
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`px-4 py-3 border-b border-white/[0.04] flex gap-3 ${
                      !n.read ? 'bg-white/[0.02]' : ''
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">{ICON_MAP[n.type]}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-sans text-[12px] font-semibold text-white truncate">
                          {n.title}
                        </p>
                        <button
                          type="button"
                          onClick={() => dismiss(n.id)}
                          className="shrink-0 text-zinc-600 hover:text-zinc-400"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      <p className="font-sans text-[11px] text-zinc-400 leading-relaxed mt-0.5">
                        {n.message}
                      </p>
                      <span className="font-mono text-[10px] text-zinc-600 mt-1 inline-block">
                        {formatTime(n.timestamp)}
                      </span>
                    </div>
                    {!n.read && (
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-2 shrink-0" />
                    )}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
