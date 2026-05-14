import type {
  Parlay,
  ParlayLeg,
  ParlayRiskBand,
  ParlayRiskProfile,
  Pick,
} from '@/types';

export const RISK_BANDS: Record<ParlayRiskProfile, ParlayRiskBand> = {
  seguro: { min: 1.1, max: 1.3 },
  moderado: { min: 1.3, max: 1.6 },
  arriesgado: { min: 1.6, max: 2.0 },
  muy_arriesgado: { min: 2.0, max: Infinity },
};

export const RISK_LABELS: Record<ParlayRiskProfile, string> = {
  seguro: 'Seguro',
  moderado: 'Moderado',
  arriesgado: 'Arriesgado',
  muy_arriesgado: 'Muy arriesgado',
};

export const RISK_DESCRIPTIONS: Record<ParlayRiskProfile, string> = {
  seguro: 'Favoritos de alta confianza, baja varianza',
  moderado: 'Mezcla de favoritos y picks con valor',
  arriesgado: 'Inclinación a underdogs, divergencias',
  muy_arriesgado: 'Combos de upside máximo',
};

const TOLERANCE = 0.05;
const MIN_LEGS = 2;
const MAX_LEGS = 8;

function pickToLeg(pick: Pick): ParlayLeg {
  return {
    pickId: pick.id,
    match: pick.match,
    homeTeam: pick.homeTeam,
    awayTeam: pick.awayTeam,
    prediction: pick.prediction,
    odds: pick.odds ?? 0,
    confidence: pick.confidence,
    market: pick.market ?? 'ML',
  };
}

function inBand(odds: number, band: ParlayRiskBand): boolean {
  return odds >= band.min && odds < (band.max === Infinity ? Number.POSITIVE_INFINITY : band.max);
}

function productOdds(legs: ParlayLeg[]): number {
  return legs.reduce((acc, l) => acc * l.odds, 1);
}

function productConfidence(legs: ParlayLeg[]): number {
  if (legs.length === 0) return 0;
  const p = legs.reduce((acc, l) => acc * (l.confidence / 100), 1);
  return p * 100;
}

function buildRationale(legs: ParlayLeg[], profile: ParlayRiskProfile, gapPct: number): string {
  if (legs.length === 0) {
    return 'No hay picks disponibles dentro del rango de riesgo seleccionado.';
  }
  const profileLabel = RISK_LABELS[profile].toLowerCase();
  const avgConf = legs.reduce((a, l) => a + l.confidence, 0) / legs.length;
  const matches = legs.map((l) => `${l.homeTeam} vs ${l.awayTeam}`).join(', ');
  const gapNote =
    Math.abs(gapPct) <= TOLERANCE
      ? `Las cuotas combinadas quedan dentro del ±${(TOLERANCE * 100).toFixed(0)}% del objetivo.`
      : gapPct > 0
        ? `Las cuotas combinadas superan el objetivo en ${(gapPct * 100).toFixed(1)}% porque el siguiente leg disponible cruzaba el target.`
        : `No fue posible alcanzar el objetivo dentro del rango ${profileLabel}: faltan picks con momio suficiente en esta banda.`;
  return `Parlay de perfil ${profileLabel} con ${legs.length} legs (${matches}). Confianza promedio por leg: ${avgConf.toFixed(0)}%. ${gapNote}`;
}

/**
 * Selecciona legs del rango de riesgo dado hasta acercarse a `targetOdds`.
 * No combina dos legs del mismo partido. Greedy ordenado por confianza desc.
 */
export function buildParlay(
  picks: Pick[],
  riskProfile: ParlayRiskProfile,
  targetOdds: number,
): Parlay {
  const band = RISK_BANDS[riskProfile];

  const candidates = picks
    .filter((p) => typeof p.odds === 'number' && inBand(p.odds as number, band))
    .sort((a, b) => b.confidence - a.confidence);

  const legs: ParlayLeg[] = [];
  const usedMatches = new Set<string>();

  for (const pick of candidates) {
    if (legs.length >= MAX_LEGS) break;
    if (usedMatches.has(pick.match)) continue;

    const candidateLeg = pickToLeg(pick);
    const oddsWithCandidate = productOdds([...legs, candidateLeg]);

    // Si el siguiente leg ya supera el target en más de la tolerancia y ya tenemos
    // el mínimo de legs, paramos y nos quedamos con lo que hay.
    if (legs.length >= MIN_LEGS && oddsWithCandidate > targetOdds * (1 + TOLERANCE)) {
      break;
    }

    legs.push(candidateLeg);
    usedMatches.add(pick.match);

    const currentOdds = productOdds(legs);
    if (legs.length >= MIN_LEGS && Math.abs(currentOdds - targetOdds) / targetOdds <= TOLERANCE) {
      break;
    }
  }

  const combinedOdds = productOdds(legs);
  const combinedConfidence = productConfidence(legs);
  const gapPct = targetOdds > 0 ? (combinedOdds - targetOdds) / targetOdds : 0;
  const withinTolerance = legs.length >= MIN_LEGS && Math.abs(gapPct) <= TOLERANCE;

  return {
    legs,
    combinedOdds: legs.length > 0 ? combinedOdds : 0,
    combinedConfidence,
    targetOdds,
    riskProfile,
    gapPct,
    withinTolerance,
    rationale: buildRationale(legs, riskProfile, gapPct),
  };
}
