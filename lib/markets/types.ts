export type MarketKind = 'goals' | 'corners' | 'btts';

export interface H2HSnapshot {
  matches: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  avgGoals: number;
  avgCorners: number;
}

export interface FormSnapshot {
  team: string;
  last5: ('W' | 'D' | 'L')[];
  goalsPerMatch: number;
  cornersPerMatch: number;
  cleanSheetsPct: number;
}

export interface GoalsPrediction {
  line: number;
  side: 'over' | 'under';
  modelProb: number;
  bookieOdds: number;
  edgePp: number;
  expectedGoals: number;
}

export interface CornersPrediction {
  line: number;
  side: 'over' | 'under';
  modelProb: number;
  bookieOdds: number;
  edgePp: number;
  expectedCorners: number;
}

export interface MatchPrediction {
  id: string;
  competition: string;
  competitionShort: string;
  stage: string;
  kickoffISO: string;
  homeTeam: { code: string; name: string };
  awayTeam: { code: string; name: string };
  h2h: H2HSnapshot;
  homeForm: FormSnapshot;
  awayForm: FormSnapshot;
  goals: GoalsPrediction;
  corners: CornersPrediction;
  btts: { prob: number; odds: number; edgePp: number };
  confidence: number;
  reasoning: string[];
}
