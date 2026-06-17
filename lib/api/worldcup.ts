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
  groups: WCGroup[];
  top_picks: WCTopPick[];
}

export function getWorldCupDashboard(): Promise<WCDashboard> {
  return apiFetch<WCDashboard>('/world-cup/dashboard');
}
