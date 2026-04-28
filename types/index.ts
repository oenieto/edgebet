export type PickResult = 'home' | 'draw' | 'away' | 'over_1_5' | 'under_1_5' | 'over_2_5' | 'under_2_5' | 'over_3_5' | 'under_3_5' | '1X' | 'X2' | '12';
export type PickMarket = 'ML' | 'OU' | 'DC';
export type PickStatus = 'free' | 'premium' | 'vip';
export type PickOutcome = 'pending' | 'win' | 'loss' | 'void';
export type UserPlan = 'free' | 'pro' | 'vip';
export type RiskProfile = 'conservative' | 'balanced' | 'aggressive';

export type ProbMap = Record<string, number>;

export interface Pick {
  id: string;
  match: string;
  homeTeam: string;
  awayTeam: string;
  homeLogo?: string | null;
  awayLogo?: string | null;
  league: string;
  leagueSlug?: string | null;
  market?: PickMarket;
  kickoff: string;
  prediction: PickResult;
  confidence: number;
  mlProb: ProbMap;
  polyProb?: ProbMap | null;
  bkProb: ProbMap;
  blendedProb?: ProbMap;
  aiReasoning: string;
  suggestedStake: number;
  status: PickStatus;
  outcome?: PickOutcome;
  odds?: number | null;
  edgePp?: number | null;
  evPct?: number | null;
  sourcesAgree?: boolean;
  modelSource?: string;
  bookmakerSource?: string;
  marketVerified?: boolean;
  polyMeta?: Record<string, any>;
  allOutcomes?: Array<{ name: string; probability: number }>;
  combos?: {
    safe: string;
    medium: string;
    risky: string;
  };
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

export interface MatchStat {
  date: string;
  home: string;
  away: string;
  homeLogo?: string | null;
  awayLogo?: string | null;
  score: string;
  result?: 'W' | 'D' | 'L' | null;
}

export interface TeamAggregates {
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
}

export interface TeamStats {
  team: string;
  logo?: string | null;
  form?: string;
  elo?: number;
  last_5: MatchStat[];
  aggregates?: TeamAggregates;
}

export interface PickStatsResponse {
  h2h: MatchStat[];
  home_stats: TeamStats;
  away_stats: TeamStats;
}

