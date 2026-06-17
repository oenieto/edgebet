import pandas as pd
import numpy as np


class FootballELO:
    """
    ELO ratings for football teams.
    FIFA formula: R_new = R_old + K * M * (S - E)
    """

    def __init__(self, k: int = 32, home_advantage: int = 65):
        self.k = k
        self.home_advantage = home_advantage
        self.ratings: dict[str, float] = {}

    def get_rating(self, team: str) -> float:
        return self.ratings.setdefault(team, 1500.0)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def margin_multiplier(self, goal_diff: int) -> float:
        return np.log(abs(goal_diff) + 1) * (2.2 / 2.2)

    def update(self, home: str, away: str,
               home_goals: int, away_goals: int) -> tuple[float, float]:
        r_home = self.get_rating(home) + self.home_advantage
        r_away = self.get_rating(away)
        e_home = self.expected_score(r_home, r_away)
        e_away = 1.0 - e_home

        if home_goals > away_goals:
            s_home, s_away = 1.0, 0.0
        elif home_goals < away_goals:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        m = self.margin_multiplier(home_goals - away_goals)
        self.ratings[home] += self.k * m * (s_home - e_home)
        self.ratings[away] += self.k * m * (s_away - e_away)
        return self.ratings[home], self.ratings[away]

    def compute_elo_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Iterate matches chronologically, save pre-match ELO,
        then update. Prevents data leakage.
        """
        df = df.sort_values("Date").copy()
        elo_features = []

        for _, row in df.iterrows():
            home = row["HomeTeam"]
            away = row["AwayTeam"]
            r_home = self.get_rating(home)
            r_away = self.get_rating(away)
            e_home = self.expected_score(r_home + self.home_advantage, r_away)

            elo_features.append({
                "elo_home": r_home,
                "elo_away": r_away,
                "elo_diff": r_home - r_away,
                "elo_expected_home": e_home,
                "elo_expected_away": 1 - e_home,
            })

            if pd.notna(row.get("FTHG")) and pd.notna(row.get("FTAG")):
                self.update(home, away, int(row["FTHG"]), int(row["FTAG"]))

        return pd.concat(
            [df.reset_index(drop=True), pd.DataFrame(elo_features)],
            axis=1,
        )

    def top_teams(self, n: int = 10) -> list[tuple[str, float]]:
        return sorted(self.ratings.items(), key=lambda x: -x[1])[:n]


# ============================================================================
# ELO de selecciones nacionales desde histórico real
# ============================================================================
_KNOCKOUT_MARKERS = (
    "FINAL", "SEMI", "QUARTER", "ROUND_OF", "ROUND OF", "KNOCKOUT",
    "PLAY", "LAST_16", "16",
)


def _is_knockout(stage: str | None, competition: str | None) -> bool:
    s = f"{stage or ''} {competition or ''}".upper()
    return any(m in s for m in _KNOCKOUT_MARKERS)


def load_national_team_history() -> "pd.DataFrame":
    """Lee national_teams_history.csv como DataFrame ordenado por fecha.

    DataFrame vacío (con columnas) si no hay histórico — el llamador cae a ELO base.
    """
    cols = ["date", "home_team", "away_team", "home_goals", "away_goals", "competition", "stage"]
    try:
        # Import diferido: data/ depende de la ruta de ejecución de la app.
        from data.national_team_loader import read_history
        rows = read_history()
    except Exception as exc:  # pragma: no cover - defensivo
        print(f"[elo] no pude cargar histórico de selecciones: {exc}")
        rows = []

    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team"]).sort_values("date").reset_index(drop=True)
    return df


def compute_national_elo_from_history(df: "pd.DataFrame") -> dict[str, float]:
    """Actualiza los ELO base de selecciones (world_cup.py) cronológicamente.

    k=40 en fase de grupos, k=50 en eliminatorias. Si `df` está vacío devuelve
    los ELO base sin cambios (fallback honesto).
    """
    # Import diferido para evitar acoplar features→api en tiempo de import.
    try:
        from api.world_cup import WORLD_CUP_TEAM_ELOS
        ratings: dict[str, float] = dict(WORLD_CUP_TEAM_ELOS)
    except Exception:
        ratings = {}

    if df is None or len(df) == 0:
        return ratings

    home_adv = 65.0
    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        try:
            hg = int(row["home_goals"])
            ag = int(row["away_goals"])
        except (TypeError, ValueError):
            continue

        r_home = ratings.setdefault(home, 1500.0)
        r_away = ratings.setdefault(away, 1500.0)
        e_home = 1.0 / (1.0 + 10 ** ((r_away - (r_home + home_adv)) / 400.0))
        e_away = 1.0 - e_home

        if hg > ag:
            s_home, s_away = 1.0, 0.0
        elif hg < ag:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        k = 50.0 if _is_knockout(row.get("stage"), row.get("competition")) else 40.0
        margin = np.log(abs(hg - ag) + 1.0)
        ratings[home] = r_home + k * margin * (s_home - e_home)
        ratings[away] = r_away + k * margin * (s_away - e_away)

    return ratings