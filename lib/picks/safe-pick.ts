import type { MarketOutcome, Pick, RiskProfile } from '@/types';

export type SelectedMarket = 'ML' | 'OU' | 'DC' | 'BTTS' | 'SPREAD' | 'TEAM_TOTALS';

export interface SelectedPick {
  market: SelectedMarket;
  outcome: string;
  label: string;
  probability: number; // 0-100
  rationale: 'highest_safety' | 'value_play' | 'engine_pick';
}

function mlLabel(pick: Pick): string {
  if (pick.prediction === 'home') return `${pick.homeTeam} gana`;
  if (pick.prediction === 'away') return `${pick.awayTeam} gana`;
  if (pick.prediction === 'draw') return 'Empate';
  return pick.prediction;
}

function mlOption(pick: Pick): SelectedPick {
  const label = mlLabel(pick);
  return {
    market: 'ML',
    outcome: pick.prediction,
    label,
    probability: pick.confidence,
    rationale: 'engine_pick',
  };
}

function bestUnderOu(pick: Pick): MarketOutcome | undefined {
  return (pick.markets?.ou_outcomes ?? [])
    .filter((o) => o.outcome.startsWith('under_'))
    .sort((a, b) => b.our_prob_pct - a.our_prob_pct)[0];
}

function bestOverOu(pick: Pick, minProb = 50): MarketOutcome | undefined {
  return (pick.markets?.ou_outcomes ?? [])
    .filter((o) => o.outcome.startsWith('over_') && o.our_prob_pct >= minProb)
    .sort((a, b) => b.our_prob_pct - a.our_prob_pct)[0];
}

function bestDc(pick: Pick): MarketOutcome | undefined {
  return (pick.markets?.dc_outcomes ?? [])
    .sort((a, b) => b.our_prob_pct - a.our_prob_pct)[0];
}

/**
 * Selecciona el pick "seguro" según el perfil de riesgo del usuario.
 *
 *   conservative → mayor probabilidad entre DC + Under_X.5 (y ML si >=70%)
 *   balanced     → el pick principal del motor (1X2)
 *   aggressive   → ML con EV positivo si hay; si no, mejor Over de goles
 */
export function selectSafePick(pick: Pick, profile: RiskProfile = 'balanced'): SelectedPick {
  const ml = mlOption(pick);

  if (profile === 'conservative') {
    const candidates: SelectedPick[] = [];
    if (ml.probability >= 70) candidates.push(ml);
    const dc = bestDc(pick);
    if (dc) {
      candidates.push({
        market: 'DC',
        outcome: dc.outcome,
        label: dc.label,
        probability: dc.our_prob_pct,
        rationale: 'highest_safety',
      });
    }
    const under = bestUnderOu(pick);
    if (under) {
      candidates.push({
        market: 'OU',
        outcome: under.outcome,
        label: under.label,
        probability: under.our_prob_pct,
        rationale: 'highest_safety',
      });
    }
    if (candidates.length > 0) {
      return candidates.sort((a, b) => b.probability - a.probability)[0];
    }
    return ml;
  }

  if (profile === 'aggressive') {
    if ((pick.evPct ?? 0) > 0) {
      return { ...ml, rationale: 'value_play' };
    }
    const over = bestOverOu(pick, 50);
    if (over) {
      return {
        market: 'OU',
        outcome: over.outcome,
        label: over.label,
        probability: over.our_prob_pct,
        rationale: 'value_play',
      };
    }
    return { ...ml, rationale: 'value_play' };
  }

  return ml;
}

/**
 * Devuelve los 3 mejores picks por mercado (ML, DC, OU) para el card multi-market.
 * Útil para la vista expandida estilo betmines.
 */
export interface MarketBest {
  market: SelectedMarket;
  outcome: string;
  label: string;
  probability: number; // 0-100
}

export function topPickPerMarket(pick: Pick): MarketBest[] {
  const result: MarketBest[] = [];

  const ml = mlOption(pick);
  result.push({
    market: 'ML',
    outcome: ml.outcome,
    label: ml.label,
    probability: ml.probability,
  });

  const dc = bestDc(pick);
  if (dc) {
    result.push({
      market: 'DC',
      outcome: dc.outcome,
      label: dc.label,
      probability: dc.our_prob_pct,
    });
  }

  const ou = (pick.markets?.ou_outcomes ?? []).sort(
    (a, b) => b.our_prob_pct - a.our_prob_pct,
  )[0];
  if (ou) {
    result.push({
      market: 'OU',
      outcome: ou.outcome,
      label: ou.label,
      probability: ou.our_prob_pct,
    });
  }

  // BTTS — mejor de yes/no
  const btts = (pick.markets?.btts_outcomes ?? []).sort(
    (a, b) => b.our_prob_pct - a.our_prob_pct,
  )[0];
  if (btts) {
    result.push({
      market: 'BTTS',
      outcome: btts.outcome,
      label: btts.label,
      probability: btts.our_prob_pct,
    });
  }

  // Spread — mejor handicap por probabilidad
  const spread = (pick.markets?.spread_outcomes ?? []).sort(
    (a, b) => b.our_prob_pct - a.our_prob_pct,
  )[0];
  if (spread) {
    result.push({
      market: 'SPREAD',
      outcome: spread.outcome,
      label: spread.label,
      probability: spread.our_prob_pct,
    });
  }

  // Team totals — mejor (típicamente over del favorito)
  const teamTotal = (pick.markets?.team_totals_outcomes ?? []).sort(
    (a, b) => b.our_prob_pct - a.our_prob_pct,
  )[0];
  if (teamTotal) {
    result.push({
      market: 'TEAM_TOTALS',
      outcome: teamTotal.outcome,
      label: teamTotal.label,
      probability: teamTotal.our_prob_pct,
    });
  }

  return result;
}

export function riskTone(probabilityPct: number): 'safe' | 'medium' | 'risky' {
  if (probabilityPct >= 70) return 'safe';
  if (probabilityPct >= 55) return 'medium';
  return 'risky';
}
