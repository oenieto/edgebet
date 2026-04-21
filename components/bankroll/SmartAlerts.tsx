'use client';

import { useState, useEffect } from 'react';
import { useUserStore } from '@/lib/store/userStore';
import { AlertCircle, X, PauseCircle } from 'lucide-react';

export default function SmartAlerts() {
  const { profile, alerts, weeklyUsedPct, isOverWeeklyLimit } = useUserStore();
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
  
  if (!profile) return null;

  const activeBanners = [];

  // Check Weekly Limit
  const weeklyAlert = alerts.find(a => a.alert_type === 'weekly_limit');
  const threshold = weeklyAlert?.threshold_pct || 80;
  const usedPct = weeklyUsedPct();

  if (weeklyAlert?.enabled !== false && usedPct >= threshold && !dismissed['weekly']) {
    activeBanners.push({
      id: 'weekly',
      type: 'warning',
      icon: <AlertCircle className="w-5 h-5" />,
      message: isOverWeeklyLimit() 
        ? `Has superado tu límite semanal de $${profile.weekly_limit.toLocaleString()}.`
        : `Llevas el ${usedPct.toFixed(0)}% apostado esta semana. Te acercas a tu límite.`,
      color: isOverWeeklyLimit() ? 'bg-red-500/10 border-red-500/20 text-red-200' : 'bg-amber-500/10 border-amber-500/20 text-amber-200',
      iconColor: isOverWeeklyLimit() ? 'text-red-400' : 'text-amber-400',
    });
  }

  // Check Pause Mode
  const pauseAlert = alerts.find(a => a.alert_type === 'pause_mode');
  if (pauseAlert?.enabled && !dismissed['pause']) {
    activeBanners.push({
      id: 'pause',
      type: 'info',
      icon: <PauseCircle className="w-5 h-5" />,
      message: `Modo pausa activo. Los picks están bloqueados temporalmente por tu seguridad.`,
      color: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-200',
      iconColor: 'text-indigo-400',
      action: <button className="ml-4 text-xs font-bold underline">Desactivar</button>
    });
  }

  // Priorities: Pause > Limit
  const visible = activeBanners.slice(0, 2);

  if (visible.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mb-6">
      {visible.map((banner) => (
        <div 
          key={banner.id} 
          className={`flex items-center justify-between p-4 rounded-xl border ${banner.color} animate-in fade-in slide-in-from-top-2`}
        >
          <div className="flex items-center gap-3">
            <div className={`${banner.iconColor}`}>{banner.icon}</div>
            <div className="text-sm font-medium">
              {banner.message}
              {banner.action}
            </div>
          </div>
          <button 
            onClick={() => setDismissed(p => ({ ...p, [banner.id]: true }))}
            className="p-1 rounded-md hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4 opacity-70" />
          </button>
        </div>
      ))}
    </div>
  );
}
