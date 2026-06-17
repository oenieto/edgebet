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
  leagueLogo?: string | null;
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
  markets?: MarketsData | null;
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
  logo?: string;
}

export interface Metrics {
  accuracy_30d: number | null;
  roi_monthly: number | null;
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

// Performance dashboard types
export interface AccuracyPoint {
  date: string;
  accuracy: number;
  picks_resolved: number;
}

export interface RoiPoint {
  date: string;
  daily_roi: number;
  cumulative_roi: number;
}

export interface LeaguePerformance {
  slug: string;
  name: string;
  accuracy: number;
  picks_resolved: number;
  roi: number;
}

export interface PerformanceSummary {
  avg_accuracy: number;
  total_roi: number;
  total_picks: number;
  best_day: string;
  worst_day: string;
}

export interface PerformanceData {
  period_days: number;
  accuracy_series: AccuracyPoint[];
  roi_series: RoiPoint[];
  league_breakdown: LeaguePerformance[];
  summary: PerformanceSummary;
}

// Parlay types — AI-generated only (Pro/VIP). User does not build legs manually.
export type ParlayRiskProfile = 'seguro' | 'moderado' | 'arriesgado' | 'muy_arriesgado';

export interface ParlayRiskBand {
  min: number;
  max: number; // Infinity for the top tier
}

export interface ParlayLeg {
  pickId: string;
  match: string;
  homeTeam: string;
  awayTeam: string;
  prediction: string;
  odds: number;
  confidence: number;
  market: string;
}

export interface Parlay {
  legs: ParlayLeg[];
  combinedOdds: number;
  combinedConfidence: number; // product of leg confidences (0-100)
  targetOdds: number;
  riskProfile: ParlayRiskProfile;
  gapPct: number; // (combinedOdds - targetOdds) / targetOdds, signed
  withinTolerance: boolean; // |gapPct| <= 0.05
  rationale: string;
}

// Notification types
export interface AppNotification {
  id: string;
  type: 'high_confidence_pick' | 'steam_move' | 'result_settled' | 'achievement_unlocked';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
}

// Player prop types
export interface PlayerPropLine {
  player_name: string;
  team: string;
  prop_type: 'shots' | 'sot' | 'cards' | 'passes' | 'goals';
  line: number;
  over_prob: number;
  under_prob: number;
  odds_over?: number;
  odds_under?: number;
}

// Market outcome types (from Poisson + Odds API)
export type MarketKey = 'OU' | 'DC' | 'BTTS' | 'TEAM_TOTALS' | 'SPREAD' | 'ML';

export interface MarketOutcome {
  market: MarketKey;
  outcome: string;
  label: string;
  our_prob_pct: number;
  market_prob_pct?: number | null;
  odds?: number | null;
  edge_pp?: number | null;
  ev_pct?: number | null;
}

export interface MarketsData {
  lambda_home: number;
  lambda_away: number;
  expected_total_goals: number;
  ou_outcomes: MarketOutcome[];
  dc_outcomes: MarketOutcome[];
  btts_outcomes?: MarketOutcome[];
  team_totals_outcomes?: MarketOutcome[];
  spread_outcomes?: MarketOutcome[];
}

