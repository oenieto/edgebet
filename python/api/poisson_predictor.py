"""
Edgebet — predictor basado en Poisson (Goles Esperados xG).

Deriva probabilidades 1X2 coherentemente a partir de las intensidades
de goles esperados (lambdas) estimadas a partir de la forma ofensiva/defensiva.
"""
from __future__ import annotations

import math

from api.poisson_markets import _expected_goals, _score_matrix, _outcome_probs

def predict_poisson_probs(home_form: dict, away_form: dict) -> dict:
    """
    Genera probabilidades H/D/A basadas puramente en el modelo de Poisson.
    Útil como metodología alternativa o cuando no se dispone del ensemble entrenado.
    """
    try:
        lam_home, lam_away = _expected_goals(home_form, away_form)
        matrix = _score_matrix(lam_home, lam_away)
        probs = _outcome_probs(matrix)
        return {
            "home": probs["home"],
            "draw": probs["draw"],
            "away": probs["away"]
        }
    except Exception as exc:
        print(f"[poisson_predictor] Falló la predicción Poisson: {exc}")
        # Fallback básico uniforme
        return {"home": 0.37, "draw": 0.26, "away": 0.37}


# ============================================================================
# PoissonPredictor — selecciones nacionales con datos históricos reales
# ============================================================================
def _time_decay_weight(year: int) -> float:
    """Pesos por antigüedad: 2024+ → 1.0, 2022–23 → 0.7, 2020–21 → 0.4, <2020 → 0.2."""
    if year >= 2024:
        return 1.0
    if year >= 2022:
        return 0.7
    if year >= 2020:
        return 0.4
    return 0.2


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _dc_tau(i: int, j: int, lh: float, la: float, rho: float) -> float:
    """Corrección Dixon-Coles para marcadores bajos (0-0, 1-0, 0-1, 1-1)."""
    if i == 0 and j == 0:
        return 1.0 - lh * la * rho
    if i == 0 and j == 1:
        return 1.0 + lh * rho
    if i == 1 and j == 0:
        return 1.0 + la * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


class PoissonPredictor:
    """Predictor Poisson con fuerzas de ataque/defensa por selección estimadas
    desde histórico real, con decaimiento temporal y corrección Dixon-Coles.

    Si una selección no tiene datos suficientes, `predict()` devuelve
    data_source='elo_estimate' y deja que el llamador caiga a ELO.
    """

    MIN_MATCHES = 3        # mínimo de partidos (ponderados por conteo) para confiar
    MAX_GOALS = 8
    RHO = -0.1             # parámetro Dixon-Coles

    def __init__(self) -> None:
        self.national_attack: dict[str, float] = {}
        self.national_defense: dict[str, float] = {}
        self.league_avg: float = 1.35
        self.home_factor: float = 1.10
        self._counts: dict[str, int] = {}
        self.fitted: bool = False

    def fit_national_teams(self, history_df) -> "PoissonPredictor":
        """Estima ataque/defensa por selección desde el DataFrame de histórico.

        `history_df` con columnas date, home_team, away_team, home_goals,
        away_goals, competition, stage. Vacío → no se ajusta (fitted=False).
        """
        self.national_attack.clear()
        self.national_defense.clear()
        self._counts.clear()
        self.fitted = False

        if history_df is None or len(history_df) == 0:
            return self

        # Acumuladores ponderados por equipo.
        gf: dict[str, float] = {}   # goles a favor ponderados
        ga: dict[str, float] = {}   # goles en contra ponderados
        wsum: dict[str, float] = {} # suma de pesos (≈ nº de partidos ponderado)
        tot_home_goals = tot_away_goals = tot_w = 0.0

        for _, row in history_df.iterrows():
            try:
                hg = float(row["home_goals"])
                ag = float(row["away_goals"])
            except (TypeError, ValueError, KeyError):
                continue
            home, away = row["home_team"], row["away_team"]
            year = _row_year(row.get("date"))
            w = _time_decay_weight(year)

            gf[home] = gf.get(home, 0.0) + w * hg
            ga[home] = ga.get(home, 0.0) + w * ag
            gf[away] = gf.get(away, 0.0) + w * ag
            ga[away] = ga.get(away, 0.0) + w * hg
            wsum[home] = wsum.get(home, 0.0) + w
            wsum[away] = wsum.get(away, 0.0) + w
            self._counts[home] = self._counts.get(home, 0) + 1
            self._counts[away] = self._counts.get(away, 0) + 1

            tot_home_goals += w * hg
            tot_away_goals += w * ag
            tot_w += w

        if tot_w <= 0:
            return self

        avg_home = tot_home_goals / tot_w
        avg_away = tot_away_goals / tot_w
        self.league_avg = max((avg_home + avg_away) / 2.0, 0.2)
        self.home_factor = max(avg_home / max(avg_away, 0.2), 1.0)

        for team, w in wsum.items():
            if w <= 0:
                continue
            team_gf = gf[team] / w  # goles a favor por partido
            team_ga = ga[team] / w  # goles en contra por partido
            self.national_attack[team] = max(team_gf / self.league_avg, 0.05)
            self.national_defense[team] = max(team_ga / self.league_avg, 0.05)

        self.fitted = bool(self.national_attack)
        return self

    def _has_data(self, team: str) -> bool:
        return team in self.national_attack and self._counts.get(team, 0) >= self.MIN_MATCHES

    def has_team_data(self, team: str) -> bool:
        """True si la selección tiene suficientes partidos reales para Poisson."""
        return self._has_data(team)

    def predict(self, home_team: str, away_team: str) -> dict:
        """Probabilidades 1X2 + data_source. Usa Poisson histórico solo si ambas
        selecciones tienen datos suficientes; si no, marca elo_estimate."""
        if not (self._has_data(home_team) and self._has_data(away_team)):
            return {"home": None, "draw": None, "away": None, "data_source": "elo_estimate"}

        lam_home = self.league_avg * self.national_attack[home_team] * self.national_defense[away_team] * self.home_factor
        lam_away = self.league_avg * self.national_attack[away_team] * self.national_defense[home_team]
        lam_home = min(max(lam_home, 0.05), 6.0)
        lam_away = min(max(lam_away, 0.05), 6.0)

        ph = pd = pa = 0.0
        total = 0.0
        for i in range(self.MAX_GOALS + 1):
            for j in range(self.MAX_GOALS + 1):
                p = _dc_tau(i, j, lam_home, lam_away, self.RHO) * _poisson_pmf(i, lam_home) * _poisson_pmf(j, lam_away)
                p = max(p, 0.0)
                total += p
                if i > j:
                    ph += p
                elif i == j:
                    pd += p
                else:
                    pa += p
        if total <= 0:
            return {"home": None, "draw": None, "away": None, "data_source": "elo_estimate"}
        return {
            "home": ph / total,
            "draw": pd / total,
            "away": pa / total,
            "data_source": "poisson_historical",
        }


def _row_year(date_val) -> int:
    """Extrae el año de un valor de fecha (str YYYY-... o datetime/Timestamp)."""
    if date_val is None:
        return 0
    if hasattr(date_val, "year"):
        return int(date_val.year)
    try:
        return int(str(date_val)[:4])
    except (ValueError, TypeError):
        return 0


# Singleton perezoso usado por el router del Mundial.
_PREDICTOR: PoissonPredictor | None = None


def get_national_predictor() -> PoissonPredictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = PoissonPredictor()
    return _PREDICTOR
