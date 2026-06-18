import type { Pick } from '@/types';
import { apiFetch } from './client';

export type Signal = 'green' | 'yellow' | 'red';

export interface WCTeamRow {
  team: string;
  flag: string;
  confederation: string;
  wc_result: 'W' | 'D' | 'L' | null;
  wc_score: string | null;
  prob_win: number;
  prob_draw: number;
  prob_loss: number;
  gf_per_game: number | null;
  gc_per_game: number | null;
  over25_tendency: 'over' | 'under' | 'even' | null;
  btts_pct: number | null;
  corners_for: number | null;
  corners_against: number | null;
  corners_line: string | null;
  cards_avg: number | null;
  cards_line: string | null;
  possession_avg: number | null;
  shots_on_target: number | null;
  form_last5: Array<'W' | 'D' | 'L'> | null;
  hot_stat: string | null;
  overall_signal: Signal;
  data_source?: 'poisson_historical' | 'elo_estimate';
  estimated?: boolean;
}

export interface WCGroup {
  group: string;
  teams: WCTeamRow[];
}

export interface WCTopPick {
  rank: number;
  team: string;
  flag: string;
  label: string;
  hot_stat: string;
  signal: Signal;
}

export interface WCDashboard {
  generated_at: string;
  model_label: string;
  groups: WCGroup[];
  top_picks: WCTopPick[];
}

export interface WCFixture {
  id: number;
  external_id: string;
  home_team: string;
  home_flag: string;
  away_team: string;
  away_flag: string;
  match_date: string;
  status: string;
  tournament_phase: string;
  match_group: string;
  round_number: number | null;
  home_goals: number | null;
  away_goals: number | null;
  predicted_home_goals: number;
  predicted_away_goals: number;
  predicted_most_likely_score: string;
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  best_odds_home: number | null;
  best_odds_draw: number | null;
  best_odds_away: number | null;
  home_form: Array<'W' | 'D' | 'L'>;
  away_form: Array<'W' | 'D' | 'L'>;
}

export interface WCFixturesResponse {
  fixtures: WCFixture[];
  total: number;
}

export interface WCPrediction extends Pick {
  home_form: Array<'W' | 'D' | 'L'>;
  away_form: Array<'W' | 'D' | 'L'>;
  h2h: any[];
}

export interface WCStandingRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  flag: string;
}

export interface WCStandingsResponse {
  groups: Record<string, WCStandingRow[]>;
  last_updated: string;
}

export function getWorldCupDashboard(): Promise<WCDashboard> {
  return apiFetch<WCDashboard>('/world-cup/dashboard');
}

export function getWCFixtures(params?: { group?: string; status?: string; date?: string }): Promise<WCFixturesResponse> {
  const query = new URLSearchParams();
  if (params?.group) query.append('group', params.group);
  if (params?.status) query.append('status', params.status);
  if (params?.date) query.append('date', params.date);
  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<WCFixturesResponse>(`/world-cup/fixtures${qs}`);
}

export function getWCPredictions(): Promise<WCPrediction[]> {
  return apiFetch<WCPrediction[]>('/world-cup/predictions');
}

export function getWCStandings(): Promise<WCStandingsResponse> {
  return apiFetch<WCStandingsResponse>('/world-cup/standings');
}

export function getWCGroupStandings(groupLetter: string): Promise<WCStandingRow[]> {
  return apiFetch<WCStandingRow[]>(`/world-cup/standings/${groupLetter}`);
}

export function getWCLive(): Promise<{ fixtures: Array<{ id: number; external_id: string; home_team: string; away_team: string }> }> {
  return apiFetch<{ fixtures: Array<{ id: number; external_id: string; home_team: string; away_team: string }> }>('/world-cup/live');
}

export function getWCTeamStats(teamName: string): Promise<any> {
  return apiFetch<any>(`/world-cup/team-stats/${encodeURIComponent(teamName)}`);
}

export function getWCH2h(home: string, away: string): Promise<any> {
  return apiFetch<any>(`/world-cup/h2h?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
}

