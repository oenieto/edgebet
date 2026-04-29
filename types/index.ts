export type PickResult = 'home' | 'draw' | 'away';
export type PickStatus = 'free' | 'premium' | 'vip';
export type PickOutcome = 'pending' | 'win' | 'loss' | 'void';
export type UserPlan = 'free' | 'pro' | 'vip';
export type RiskProfile = 'conservative' | 'balanced' | 'aggressive';

export interface ProbabilityTriplet {
  home: number;
  draw: number;
  away: number;
}

export interface Pick {
  id: string;
  match: string;
  matchIcon?: string;
  homeTeam: string;
  awayTeam: string;
  league: string;
  leagueSlug?: string | null;
  kickoff: string;
  prediction: PickResult;
  confidence: number;
  mlProb: ProbabilityTriplet;
  polyProb?: ProbabilityTriplet | null;
  bkProb: ProbabilityTriplet;
  aiReasoning: string;
  suggestedStake: number;
  status: PickStatus;
  outcome?: PickOutcome;
  odds?: number | null;
  edgePp?: number | null;
  evPct?: number | null;
}

export interface LeagueInfo {
  slug: string;
  name: string;
  code: string;
}

export interface Metrics {
  accuracy_30d: number;
  roi_monthly: number;
  verified_picks: number;
  active_divergences: number;
}

export interface League {
  code: string;
  name: string;
  country: string;
  flag: string;
  picksThisWeek: number;
  accuracyPct: number;
}

export interface BankrollSnapshot {
  date: string;
  amount: number;
  pnl: number;
  picksCount: number;
}
