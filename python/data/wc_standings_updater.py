"""
Edgebet — FIFA World Cup 2026 group standings updater.

Aggregates finished matches, updates points/standings, updates ELO, and serves standing tables.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from api.db import connect
from api.world_cup import list_groups
from data.team_name_map import canonicalize

logger = logging.getLogger("edgebet.wc_standings_updater")

def update_group_standings() -> None:
    """
    Queries all finished FIFA World Cup 2026 group stage matches, computes points/GD/GF,
    upserts them into wc_group_standings, appends matches to the historical CSV, and
    invalidates ELO/Poisson cache.
    """
    standings = {} # (group_letter, team_name) -> stats
    
    # 1. Initialize standings for all 48 teams
    for group_letter, teams in list_groups().items():
        for team in teams:
            standings[(group_letter, team.key)] = {
                "matches_played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0
            }

    finished_matches = []
    
    # 2. Query finished group matches
    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT home_team, away_team, home_score, away_score, kickoff, match_group, tournament_phase
                FROM fixtures
                WHERE league_slug = 'fifa-world-cup'
                  AND tournament_phase = 'group_stage'
                  AND status = 'finished'
                """
            )
            rows = cur.fetchall()
            for r in rows:
                home = r["home_team"] if hasattr(r, "keys") else r[0]
                away = r["away_team"] if hasattr(r, "keys") else r[1]
                hs = r["home_score"] if hasattr(r, "keys") else r[2]
                as_ = r["away_score"] if hasattr(r, "keys") else r[3]
                ko = r["kickoff"] if hasattr(r, "keys") else r[4]
                group = r["match_group"] if hasattr(r, "keys") else r[5]
                
                if hs is None or as_ is None or not group:
                    continue
                    
                hs, as_ = int(hs), int(as_)
                finished_matches.append({
                    "home": home, "away": away, "home_score": hs, "away_score": as_,
                    "kickoff": ko, "group": group
                })
                
                # Accumulate stats
                h_stats = standings.setdefault((group, home), {
                    "matches_played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0
                })
                a_stats = standings.setdefault((group, away), {
                    "matches_played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0
                })
                
                h_stats["matches_played"] += 1
                a_stats["matches_played"] += 1
                h_stats["goals_for"] += hs
                h_stats["goals_against"] += as_
                a_stats["goals_for"] += as_
                a_stats["goals_against"] += hs
                
                if hs > as_:
                    h_stats["wins"] += 1
                    h_stats["points"] += 3
                    a_stats["losses"] += 1
                elif hs < as_:
                    a_stats["wins"] += 1
                    a_stats["points"] += 3
                    h_stats["losses"] += 1
                else:
                    h_stats["draws"] += 1
                    h_stats["points"] += 1
                    a_stats["draws"] += 1
                    a_stats["points"] += 1
    except Exception as exc:
        logger.error("[wc_standings_updater] DB error querying finished fixtures: %s", exc)
        return

    # 3. Upsert standings into database
    try:
        with connect() as cur:
            for (group_letter, team_name), stats in standings.items():
                cur.execute(
                    """
                    INSERT INTO wc_group_standings (
                        group_letter, team_name, matches_played, wins, draws, losses, 
                        goals_for, goals_against, points, last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (group_letter, team_name) DO UPDATE SET
                        matches_played = EXCLUDED.matches_played,
                        wins = EXCLUDED.wins,
                        draws = EXCLUDED.draws,
                        losses = EXCLUDED.losses,
                        goals_for = EXCLUDED.goals_for,
                        goals_against = EXCLUDED.goals_against,
                        points = EXCLUDED.points,
                        last_updated = CURRENT_TIMESTAMP
                    """,
                    (
                        group_letter, team_name, stats["matches_played"], stats["wins"], stats["draws"], stats["losses"],
                        stats["goals_for"], stats["goals_against"], stats["points"]
                    )
                )
    except Exception as exc:
        logger.error("[wc_standings_updater] DB error upserting standings: %s", exc)

    # 4. Append finished matches to national_teams_history.csv
    if finished_matches:
        try:
            from data.national_team_loader import HISTORY_CSV, CSV_COLUMNS, read_history
            existing = read_history()
            existing_keys = {(r["home_team"], r["away_team"], r["date"]) for r in existing}
            
            new_rows = []
            for m in finished_matches:
                # Format date to YYYY-MM-DD
                ko_date = m["kickoff"]
                if isinstance(ko_date, datetime):
                    date_str = ko_date.strftime("%Y-%m-%d")
                else:
                    date_str = str(ko_date)[:10]
                    
                key = (m["home"], m["away"], date_str)
                if key not in existing_keys:
                    new_rows.append({
                        "date": date_str, "home_team": m["home"], "away_team": m["away"],
                        "home_goals": m["home_score"], "away_goals": m["away_score"],
                        "competition": "FIFA World Cup 2026", "source": "odds_api_scores"
                    })
                    
            if new_rows:
                logger.info("[wc_standings_updater] Appending %d new finished matches to national team history", len(new_rows))
                with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                    for r in new_rows:
                        writer.writerow({k: r.get(k, "") for k in CSV_COLUMNS})
        except Exception as exc:
            logger.error("[wc_standings_updater] Error appending matches to history CSV: %s", exc)

    # 5. Invalidate ELO/Poisson model cache in router
    try:
        import api.world_cup_router as wr
        wr._model_ready = False
        logger.info("[wc_standings_updater] Cleared world cup router model cache.")
    except Exception as exc:
        logger.warning("[wc_standings_updater] Failed to invalidate router model cache: %s", exc)


def get_standings_for_group(group_letter: str) -> list[dict]:
    """
    Returns sorted standings for a single group.
    Sorting criteria: Points desc -> GD (GF - GA) desc -> GF desc.
    """
    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT team_name, matches_played, wins, draws, losses, goals_for, goals_against, points
                FROM wc_group_standings
                WHERE group_letter = %s
                """,
                (group_letter,)
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("[wc_standings_updater] DB error fetching standings: %s", exc)
        rows = []

    out = []
    # Map teams to include flags from world_cup
    teams_list = list_groups().get(group_letter, [])
    flag_map = {t.key: t.flag for t in teams_list}
    name_map = {t.key: t.name for t in teams_list}

    for r in rows:
        team_key = r["team_name"] if hasattr(r, "keys") else r[0]
        mp = r["matches_played"] if hasattr(r, "keys") else r[1]
        w = r["wins"] if hasattr(r, "keys") else r[2]
        d = r["draws"] if hasattr(r, "keys") else r[3]
        l = r["losses"] if hasattr(r, "keys") else r[4]
        gf = r["goals_for"] if hasattr(r, "keys") else r[5]
        ga = r["goals_against"] if hasattr(r, "keys") else r[6]
        pts = r["points"] if hasattr(r, "keys") else r[7]
        
        out.append({
            "team": name_map.get(team_key, team_key),
            "key": team_key,
            "flag": flag_map.get(team_key, "⚽"),
            "played": mp,
            "won": w,
            "drawn": d,
            "lost": l,
            "gf": gf,
            "ga": ga,
            "gd": gf - ga,
            "points": pts
        })
        
    # Sort standings: Points desc -> Goal Difference desc -> Goals For desc
    out.sort(key=lambda x: (x["points"], x["gd"], x["gf"]), reverse=True)
    return out
