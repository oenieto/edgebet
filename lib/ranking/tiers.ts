export type RankId = 'aprendiz' | 'estratega' | 'cazador' | 'maestro' | 'leyenda' | 'elite_mx';

export interface Rank {
  id: RankId;
  name: string;
  level: number;
  minXp: number;
  color: string;
  glow: string;
  tagline: string;
}

export const RANKS: Rank[] = [
  {
    id: 'aprendiz',
    name: 'Aprendiz',
    level: 1,
    minXp: 0,
    color: '#94a3b8',
    glow: 'from-slate-400/30 to-slate-500/0',
    tagline: 'Estás aprendiendo a leer el edge.',
  },
  {
    id: 'estratega',
    name: 'Estratega',
    level: 2,
    minXp: 250,
    color: '#34d399',
    glow: 'from-emerald-400/30 to-emerald-500/0',
    tagline: 'Reconoces patrones, gestionas bankroll.',
  },
  {
    id: 'cazador',
    name: 'Cazador de valor',
    level: 3,
    minXp: 750,
    color: '#60a5fa',
    glow: 'from-sky-400/30 to-sky-500/0',
    tagline: 'Detectas EV antes que el mercado.',
  },
  {
    id: 'maestro',
    name: 'Maestro',
    level: 4,
    minXp: 2000,
    color: '#a78bfa',
    glow: 'from-violet-400/35 to-violet-500/0',
    tagline: 'Disciplina + edge sostenidos en el largo plazo.',
  },
  {
    id: 'leyenda',
    name: 'Leyenda',
    level: 5,
    minXp: 5000,
    color: '#fbbf24',
    glow: 'from-amber-300/40 to-amber-500/0',
    tagline: 'Top 1%. ROI documentado, decisiones de élite.',
  },
  {
    id: 'elite_mx',
    name: 'Élite MX',
    level: 6,
    minXp: 12000,
    color: '#f43f5e',
    glow: 'from-rose-400/45 to-rose-600/0',
    tagline: 'Acceso a eventos exclusivos en México.',
  },
];

export function getRankByXp(xp: number): Rank {
  let current = RANKS[0];
  for (const r of RANKS) {
    if (xp >= r.minXp) current = r;
    else break;
  }
  return current;
}

export function getNextRank(current: Rank): Rank | null {
  const idx = RANKS.findIndex((r) => r.id === current.id);
  return idx >= 0 && idx < RANKS.length - 1 ? RANKS[idx + 1] : null;
}

export function getProgressToNext(xp: number): {
  current: Rank;
  next: Rank | null;
  pct: number;
  xpInLevel: number;
  xpNeeded: number;
} {
  const current = getRankByXp(xp);
  const next = getNextRank(current);
  if (!next) {
    return { current, next: null, pct: 100, xpInLevel: xp - current.minXp, xpNeeded: 0 };
  }
  const xpInLevel = xp - current.minXp;
  const xpNeeded = next.minXp - current.minXp;
  return {
    current,
    next,
    pct: Math.min(100, Math.round((xpInLevel / xpNeeded) * 100)),
    xpInLevel,
    xpNeeded,
  };
}
