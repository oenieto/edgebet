import type { MatchPrediction } from './types';

export const CHAMPIONS_FIXTURES: MatchPrediction[] = [
  {
    id: 'ucl-2026-04-28-rma-bay',
    competition: 'UEFA Champions League',
    competitionShort: 'Champions',
    stage: 'Semifinal · Ida',
    kickoffISO: '2026-04-28T19:00:00Z',
    homeTeam: { code: 'RMA', name: 'Real Madrid' },
    awayTeam: { code: 'BAY', name: 'Bayern München' },
    h2h: {
      matches: 12,
      homeWins: 5,
      draws: 2,
      awayWins: 5,
      avgGoals: 3.42,
      avgCorners: 11.2,
    },
    homeForm: {
      team: 'Real Madrid',
      last5: ['W', 'W', 'D', 'W', 'W'],
      goalsPerMatch: 2.6,
      cornersPerMatch: 6.8,
      cleanSheetsPct: 40,
    },
    awayForm: {
      team: 'Bayern München',
      last5: ['W', 'L', 'W', 'W', 'D'],
      goalsPerMatch: 2.2,
      cornersPerMatch: 6.4,
      cleanSheetsPct: 30,
    },
    goals: {
      line: 2.5,
      side: 'over',
      modelProb: 0.68,
      bookieOdds: 1.72,
      edgePp: 9.8,
      expectedGoals: 3.18,
    },
    corners: {
      line: 10.5,
      side: 'over',
      modelProb: 0.61,
      bookieOdds: 1.95,
      edgePp: 7.4,
      expectedCorners: 11.6,
    },
    btts: {
      prob: 0.72,
      odds: 1.55,
      edgePp: 7.5,
    },
    confidence: 74,
    reasoning: [
      'Promedio histórico H2H de 3.42 goles por partido en últimos 12 cruces.',
      'Ambos equipos llegan con +2 goles por partido en sus últimos 5.',
      'Bernabéu en partidos UCL produce 11.6 córners de media (eliminatorias 2024-26).',
    ],
  },
  {
    id: 'ucl-2026-04-29-psg-arsenal',
    competition: 'UEFA Champions League',
    competitionShort: 'Champions',
    stage: 'Semifinal · Ida',
    kickoffISO: '2026-04-29T19:00:00Z',
    homeTeam: { code: 'PSG', name: 'Paris Saint-Germain' },
    awayTeam: { code: 'ARS', name: 'Arsenal' },
    h2h: {
      matches: 6,
      homeWins: 2,
      draws: 1,
      awayWins: 3,
      avgGoals: 2.83,
      avgCorners: 10.5,
    },
    homeForm: {
      team: 'Paris Saint-Germain',
      last5: ['W', 'W', 'W', 'D', 'L'],
      goalsPerMatch: 2.4,
      cornersPerMatch: 7.0,
      cleanSheetsPct: 50,
    },
    awayForm: {
      team: 'Arsenal',
      last5: ['W', 'W', 'L', 'W', 'D'],
      goalsPerMatch: 2.0,
      cornersPerMatch: 6.6,
      cleanSheetsPct: 60,
    },
    goals: {
      line: 2.5,
      side: 'over',
      modelProb: 0.59,
      bookieOdds: 1.80,
      edgePp: 3.4,
      expectedGoals: 2.74,
    },
    corners: {
      line: 9.5,
      side: 'over',
      modelProb: 0.66,
      bookieOdds: 1.85,
      edgePp: 11.9,
      expectedCorners: 10.8,
    },
    btts: {
      prob: 0.64,
      odds: 1.72,
      edgePp: 5.8,
    },
    confidence: 71,
    reasoning: [
      'Arsenal genera 6.6 córners por partido como visitante en UCL esta temporada.',
      'PSG en Parc des Princes promedia 7.2 córners por partido en KO rounds.',
      'Defensa Arsenal mantiene 60% clean sheets — apuesta a córners > a goles.',
    ],
  },
];

export function getChampionsFixturesForDates(dates: string[]): MatchPrediction[] {
  const set = new Set(dates);
  return CHAMPIONS_FIXTURES.filter((m) => set.has(m.kickoffISO.slice(0, 10)));
}
