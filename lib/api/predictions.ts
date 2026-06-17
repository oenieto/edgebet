import { apiFetch } from './client';

export interface PredictionRow {
  match_date: string | null;
  league: string | null;
  home_team: string | null;
  away_team: string | null;
  recommended_bet: string | null;
  prob: number | null;
  ev: number | null;
  kelly_stake: number | null;
  method: string | null;
  generated_at: string | null;
}

export interface PredictionsResponse {
  predictions: PredictionRow[];
  count: number;
}

export function getRecentPredictions(days = 30, limit = 300): Promise<PredictionsResponse> {
  return apiFetch<PredictionsResponse>(`/predictions/recent?days=${days}&limit=${limit}`);
}
