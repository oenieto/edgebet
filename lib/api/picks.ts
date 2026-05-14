import type { LeagueInfo, Metrics, PerformanceData, Pick, PickStatsResponse } from '@/types';
import { apiFetch } from './client';

export function getPicksToday(leagueSlug?: string): Promise<Pick[]> {
  const qs = leagueSlug ? `?league=${encodeURIComponent(leagueSlug)}` : '';
  return apiFetch<Pick[]>(`/picks/today${qs}`);
}

export function getMetrics(): Promise<Metrics> {
  return apiFetch<Metrics>('/metrics');
}

export function getLeagues(): Promise<LeagueInfo[]> {
  return apiFetch<LeagueInfo[]>('/leagues');
}

export function getExclusivePick(): Promise<Pick> {
  return apiFetch<Pick>('/picks/exclusive');
}

/**
 * Detalle de un pick por id. El backend no expone /picks/{id} todavía
 * (la lista entera vive en /picks/today con TTL 5 min) — filtramos en
 * cliente. Cuando haya endpoint dedicado, cambiar por apiFetch directo.
 */
export async function getPick(id: string): Promise<Pick | null> {
  const all = await getPicksToday();
  return all.find((p) => p.id === id) ?? null;
}

/**
 * Stats H2H + últimos 5 partidos de cada equipo. Backend expone
 * /picks/{id}/stats que computa esto desde el histórico ya cacheado.
 */
export function getPickStats(id: string): Promise<PickStatsResponse> {
  return apiFetch<PickStatsResponse>(`/picks/${encodeURIComponent(id)}/stats`);
}

export function getPerformance(days: number = 30): Promise<PerformanceData> {
  return apiFetch<PerformanceData>(`/metrics/performance?days=${days}`);
}
