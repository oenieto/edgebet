import pandas as pd
import numpy as np


class FeatureEngineer:
    """Rolling averages, odds features, xG proxy, fatigue, H2H."""

    def __init__(self, window: int = 5):
        self.window = window

    def compute_team_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values("Date").copy()
        renamed_cols = [
            "Date", "Team", "GF", "GA",
            "Shots", "ShotsAgainst", "SoT", "SoTAgainst",
            "Corners", "CornersAgainst", "Fouls", "FoulsAgainst",
        ]
        home_records = df[["Date", "HomeTeam", "FTHG", "FTAG", "HS", "AS", "HST", "AST", "HC", "AC", "HF", "AF"]].copy()
        home_records.columns = renamed_cols

        away_records = df[["Date", "AwayTeam", "FTAG", "FTHG", "AS", "HS", "AST", "HST", "AC", "HC", "AF", "HF"]].copy()
        away_records.columns = renamed_cols

        home_records["IsHome"] = 1
        away_records["IsHome"] = 0

        all_records = pd.concat([home_records, away_records]).sort_values("Date")
        stats_cols = ["GF","GA","Shots","ShotsAgainst","SoT","SoTAgainst","Corners","CornersAgainst","Fouls","FoulsAgainst"]

        rolling_stats = {}
        for team in all_records["Team"].unique():
            team_data = all_records[all_records["Team"] == team].copy()
            for col in stats_cols:
                team_data[f"avg_{col}"] = (
                    team_data[col].shift(1)
                    .rolling(window=self.window, min_periods=3).mean()
                )
            team_data["Points"] = team_data.apply(
                lambda r: 3 if r["GF"] > r["GA"] else (1 if r["GF"] == r["GA"] else 0), axis=1
            )
            team_data["Form"] = team_data["Points"].shift(1).rolling(window=self.window, min_periods=3).mean()
            rolling_stats[team] = team_data

        return pd.concat(rolling_stats.values())

    def build_match_features(self, df: pd.DataFrame) -> pd.DataFrame:
        team_stats = self.compute_team_stats(df)
        stat_features = [c for c in team_stats.columns if c.startswith("avg_")]
        stat_features.append("Form")
        features_list = []

        for idx, match in df.iterrows():
            home, away, date = match["HomeTeam"], match["AwayTeam"], match["Date"]
            home_stats = team_stats[(team_stats["Team"]==home)&(team_stats["Date"]==date)&(team_stats["IsHome"]==1)]
            away_stats = team_stats[(team_stats["Team"]==away)&(team_stats["Date"]==date)&(team_stats["IsHome"]==0)]
            if home_stats.empty or away_stats.empty:
                continue
            row = {"match_idx": idx}
            for feat in stat_features:
                h_val = home_stats[feat].values[0]
                a_val = away_stats[feat].values[0]
                row[f"home_{feat}"] = h_val
                row[f"away_{feat}"] = a_val
                row[f"diff_{feat}"] = h_val - a_val
            features_list.append(row)

        features_df = pd.DataFrame(features_list).set_index("match_idx")
        return df.join(features_df, how="inner").dropna(subset=list(features_df.columns))

    @staticmethod
    def add_odds_features(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if all(col in df.columns for col in ["B365H","B365D","B365A"]):
            df["odds_prob_H"] = 1 / df["B365H"]
            df["odds_prob_D"] = 1 / df["B365D"]
            df["odds_prob_A"] = 1 / df["B365A"]
            total = df["odds_prob_H"] + df["odds_prob_D"] + df["odds_prob_A"]
            df["norm_prob_H"] = df["odds_prob_H"] / total
            df["norm_prob_D"] = df["odds_prob_D"] / total
            df["norm_prob_A"] = df["odds_prob_A"] / total
            df["odds_spread"] = df["norm_prob_H"] - df["norm_prob_A"]
        return df

    @staticmethod
    def compute_xg_proxy(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        SOT_CONVERSION, SHOT_CONVERSION = 0.30, 0.03
        if "HST" in df.columns and "HS" in df.columns:
            df["home_xG_proxy"] = df["HST"]*SOT_CONVERSION + (df["HS"]-df["HST"]).clip(lower=0)*SHOT_CONVERSION
            df["away_xG_proxy"] = df["AST"]*SOT_CONVERSION + (df["AS"]-df["AST"]).clip(lower=0)*SHOT_CONVERSION
            df["home_xG_overperf"] = df["FTHG"] - df["home_xG_proxy"]
            df["away_xG_overperf"] = df["FTAG"] - df["away_xG_proxy"]
        return df

    @staticmethod
    def compute_fatigue_features(df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values("Date").copy()
        rest_days_home, rest_days_away = [], []
        last_match: dict[str, pd.Timestamp] = {}

        for _, row in df.iterrows():
            home, away, date = row["HomeTeam"], row["AwayTeam"], row["Date"]
            rest_days_home.append(min((date - last_match[home]).days, 30) if home in last_match else 14)
            rest_days_away.append(min((date - last_match[away]).days, 30) if away in last_match else 14)
            last_match[home] = date
            last_match[away] = date

        df["home_rest_days"] = rest_days_home
        df["away_rest_days"] = rest_days_away
        df["rest_advantage"] = df["home_rest_days"] - df["away_rest_days"]
        df["home_fatigued"] = (df["home_rest_days"] <= 3).astype(int)
        df["away_fatigued"] = (df["away_rest_days"] <= 3).astype(int)
        df["is_midweek"] = df["Date"].dt.dayofweek.isin([1, 2]).astype(int)
        return df

    @staticmethod
    def compute_h2h_features(df: pd.DataFrame, n_last: int = 5) -> pd.DataFrame:
        df = df.sort_values("Date").copy()
        h2h_features = []

        for idx, row in df.iterrows():
            home, away, date = row["HomeTeam"], row["AwayTeam"], row["Date"]
            prev = df[
                (df["Date"] < date) &
                (((df["HomeTeam"]==home)&(df["AwayTeam"]==away)) |
                 ((df["HomeTeam"]==away)&(df["AwayTeam"]==home)))
            ].tail(n_last)

            if len(prev) < 2:
                h2h_features.append({"h2h_home_wins": np.nan, "h2h_draws": np.nan, "h2h_total_goals_avg": np.nan})
                continue

            home_wins, draws, total_goals = 0, 0, 0
            for _, p in prev.iterrows():
                if p["HomeTeam"] == home:
                    if p["FTR"] == "H": home_wins += 1
                    elif p["FTR"] == "D": draws += 1
                else:
                    if p["FTR"] == "A": home_wins += 1
                    elif p["FTR"] == "D": draws += 1
                total_goals += p["FTHG"] + p["FTAG"]

            n = len(prev)
            h2h_features.append({
                "h2h_home_wins": home_wins / n,
                "h2h_draws": draws / n,
                "h2h_total_goals_avg": total_goals / n,
            })

        return pd.concat([df, pd.DataFrame(h2h_features, index=df.index)], axis=1)