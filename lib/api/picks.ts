import type { LeagueInfo, Metrics, Pick } from '@/types';
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

export function getPick(id: string): Promise<Pick> {
  return apiFetch<Pick>(`/picks/${id}`);
}

export function getPickStats(id: string): Promise<import('@/types').PickStatsResponse> {
  return apiFetch<import('@/types').PickStatsResponse>(`/picks/${id}/stats`);
}

