"""
Edgebet — FIFA World Cup 2026 fixture sync service.

Fetches real-time fixtures and odds from The Odds API, determines the tournament phase,
group, and round numbers, and handles upserting into the fixtures and odds_history tables.
Falls back to hardcoded fixtures if the API returns 0 events.
"""
from __future__ import annotations

import logging
import os
import requests
from datetime import datetime, timezone
from api.db import connect
from api.world_cup import list_groups, list_fixtures
from data.team_name_map import canonicalize

logger = logging.getLogger("edgebet.wc_fixture_sync")

def sync_wc_fixtures_from_odds_api() -> dict:
    """
    Syncs World Cup 2026 fixtures from The Odds API and upserts them.
    Also fetches h2h decimal odds and stores them in the odds_history table.
    """
    api_key = os.environ.get("EDGEBET_ODDS_API_KEY")
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    
    fixtures_synced = 0
    fixtures_with_odds = 0
    source = "odds_api"

    # Step A & B & C: Fetch events from The Odds API
    events = []
    if api_key:
        try:
            url = "https://api.odds-api.com/v4/sports/soccer_fifa_world_cup/events"
            resp = requests.get(url, params={"apiKey": api_key}, timeout=10)
            if resp.status_code == 200:
                events = resp.json()
            else:
                logger.warning("[wc_fixture_sync] Events API status code %d", resp.status_code)
        except Exception as exc:
            logger.warning("[wc_fixture_sync] Failed to fetch events from API: %s", exc)

    # Step B helper maps group letters
    group_map = {}
    for group_letter, teams in list_groups().items():
        for team in teams:
            group_map[team.key] = group_letter

    def get_phase_and_group(home_canon: str, away_canon: str, dt: datetime) -> tuple[str, str | None]:
        # Determine phase based on match date (Jun 11 - Jul 19 2026) in UTC
        m_d = (dt.month, dt.day)
        
        # Determine group
        g_home = group_map.get(home_canon)
        g_away = group_map.get(away_canon)
        group_letter = g_home if g_home == g_away else None
        
        if m_d < (7, 3):
            phase = "group_stage"
        elif (7, 3) <= m_d < (7, 6):
            phase = "round_of_32"
            group_letter = None  # Knockout has no groups
        elif (7, 6) <= m_d < (7, 9):
            phase = "round_of_16"
            group_letter = None
        elif (7, 9) <= m_d < (7, 13):
            phase = "quarter_final"
            group_letter = None
        elif (7, 14) <= m_d <= (7, 15):
            phase = "semi_final"
            group_letter = None
        elif m_d == (7, 18):
            phase = "third_place"
            group_letter = None
        elif m_d == (7, 19):
            phase = "final"
            group_letter = None
        else:
            # Fallback based on calendar if outside typical ranges
            phase = "group_stage"
            
        return phase, group_letter

    # DB Helper to upsert fixtures
    def upsert_fixtures(fixtures_to_save):
        nonlocal fixtures_synced
        with connect() as cur:
            for f in fixtures_to_save:
                # SQLite / PG compatible insert
                cur.execute(
                    """
                    INSERT INTO fixtures (
                        external_id, league_slug, home_team, away_team, kickoff, status, 
                        tournament_phase, match_group, round_number, home_score, away_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (external_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        tournament_phase = EXCLUDED.tournament_phase,
                        match_group = EXCLUDED.match_group,
                        round_number = EXCLUDED.round_number
                    WHERE fixtures.league_slug = 'fifa-world-cup'
                    """,
                    (
                        f["external_id"], "fifa-world-cup", f["home_team"], f["away_team"], f["kickoff"], f["status"],
                        f["tournament_phase"], f["match_group"], f["round_number"], f.get("home_score"), f.get("away_score")
                    )
                )
                fixtures_synced += 1

    # Step D: Fallback if API returns 0 events
    if not events:
        logger.info("Odds API returned 0 WC events — using hardcoded fallback")
        source = "hardcoded_fallback"
        fallback_fixtures = []
        
        # Fetch hardcoded list from world_cup.py
        for f in list_fixtures():
            # Format kickoff date: dd/mm/yyyy time HH:MM
            try:
                dt_str = f"{f.date} {f.time}"
                dt = datetime.strptime(dt_str, "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime(2026, 6, 11, 20, 0, tzinfo=timezone.utc)
                
            home_canon = canonicalize(f.home)
            away_canon = canonicalize(f.away)
            phase, match_group = get_phase_and_group(home_canon, away_canon, dt)
            
            # Simple round numbering logic for fallback group stage
            # We can use hardcoded mapping if known or fallback defaults
            round_num = 1
            
            fallback_fixtures.append({
                "external_id": f"fallback:{home_canon}:{away_canon}:{dt.strftime('%Y-%m-%d')}",
                "home_team": home_canon,
                "away_team": away_canon,
                "kickoff": dt.isoformat(),
                "status": "scheduled",
                "tournament_phase": phase,
                "match_group": match_group,
                "round_number": round_num,
                "home_score": None,
                "away_score": None
            })
            
        # Group fallback fixtures by match_group to assign correct round number for group stage
        group_fixtures = {}
        for f in fallback_fixtures:
            if f["tournament_phase"] == "group_stage" and f["match_group"]:
                group_fixtures.setdefault(f["match_group"], []).append(f)
                
        for group_letter, f_list in group_fixtures.items():
            f_list.sort(key=lambda x: x["kickoff"])
            for idx, f in enumerate(f_list):
                f["round_number"] = (idx // 2) + 1

        upsert_fixtures(fallback_fixtures)

    else:
        # We got real events from API, process them
        api_fixtures = []
        for e in events:
            ext_id = e["id"]
            home_canon = canonicalize(e["home_team"])
            away_canon = canonicalize(e["away_team"])
            
            try:
                # ISO commencement time string e.g. "2026-06-11T20:00:00Z"
                time_str = e["commence_time"]
                if time_str.endswith("Z"):
                    time_str = time_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(time_str).astimezone(timezone.utc)
            except Exception:
                dt = datetime(2026, 6, 11, 20, 0, tzinfo=timezone.utc)
                
            phase, match_group = get_phase_and_group(home_canon, away_canon, dt)
            
            api_fixtures.append({
                "external_id": ext_id,
                "home_team": home_canon,
                "away_team": away_canon,
                "kickoff": dt.isoformat(),
                "status": "scheduled",
                "tournament_phase": phase,
                "match_group": match_group,
                "round_number": 1,
                "home_score": None,
                "away_score": None
            })
            
        # Group stage sequence round numbers
        group_fixtures = {}
        for f in api_fixtures:
            if f["tournament_phase"] == "group_stage" and f["match_group"]:
                group_fixtures.setdefault(f["match_group"], []).append(f)
                
        for group_letter, f_list in group_fixtures.items():
            f_list.sort(key=lambda x: x["kickoff"])
            for idx, f in enumerate(f_list):
                f["round_number"] = (idx // 2) + 1
                
        upsert_fixtures(api_fixtures)

    # Step E: Fetch odds for each WC fixture
    if api_key and source == "odds_api":
        try:
            url_odds = "https://api.odds-api.com/v4/sports/soccer_fifa_world_cup/odds"
            params_odds = {"apiKey": api_key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"}
            resp_odds = requests.get(url_odds, params=params_odds, timeout=10)
            if resp_odds.status_code == 200:
                odds_data = resp_odds.json()
                now_ts = datetime.now(timezone.utc)
                
                with connect() as cur:
                    for event_odds in odds_data:
                        event_id = event_odds["id"]
                        home_t = canonicalize(event_odds["home_team"])
                        away_t = canonicalize(event_odds["away_team"])
                        bookmakers = event_odds.get("bookmakers", [])
                        
                        # Just log/insert for preferred bookies or the first available
                        for bk in bookmakers:
                            bk_key = bk["key"]
                            h2h_market = next((m for m in bk.get("markets", []) if m["key"] == "h2h"), None)
                            if h2h_market:
                                outcomes = h2h_market.get("outcomes", [])
                                for out in outcomes:
                                    outcome_name = out["name"]
                                    price = float(out["price"])
                                    
                                    # Map outcome name to market key
                                    if outcome_name == event_odds["home_team"]:
                                        market_name = "home"
                                    elif outcome_name == event_odds["away_team"]:
                                        market_name = "away"
                                    else:
                                        market_name = "draw"
                                        
                                    cur.execute(
                                        """
                                        INSERT INTO odds_history (event_id, bookmaker, market, odds_value, timestamp)
                                        VALUES (%s, %s, %s, %s, %s)
                                        """,
                                        (event_id, bk_key, market_name, price, now_ts)
                                    )
                                    fixtures_with_odds += 1
                                break # Limit to 1 bookmaker per event to keep history clean
            else:
                logger.warning("[wc_fixture_sync] Odds API status code %d", resp_odds.status_code)
        except Exception as exc:
            logger.warning("[wc_fixture_sync] Failed to fetch odds from API: %s", exc)

    return {
        "fixtures_synced": fixtures_synced,
        "fixtures_with_odds": fixtures_with_odds,
        "source": source,
        "timestamp": timestamp_iso
    }

def check_live_wc_scores() -> None:
    """
    Checks for finished WC matches in the last 3 hours and updates fixtures,
    standings, and settles pending bets.
    """
    api_key = os.environ.get("EDGEBET_ODDS_API_KEY")
    if not api_key:
        return

    from api.db import connect
    from data.wc_standings_updater import update_group_standings
    from api.settlement import settle_pending_picks
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    three_hours_ago = now - timedelta(hours=3)

    # 1. Find fixtures that need updating
    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT external_id, home_team, away_team
                FROM fixtures
                WHERE league_slug = 'fifa-world-cup'
                  AND status != 'finished'
                  AND kickoff >= %s
                  AND kickoff <= %s
                """,
                (three_hours_ago.isoformat(), now.isoformat())
            )
            rows = cur.fetchall()
            active_fixtures = []
            for r in rows:
                ext_id = r["external_id"] if hasattr(r, "keys") else r[0]
                home = r["home_team"] if hasattr(r, "keys") else r[1]
                away = r["away_team"] if hasattr(r, "keys") else r[2]
                active_fixtures.append((ext_id, home, away))
    except Exception as exc:
        logger.error("[wc_fixture_sync] DB error finding active fixtures: %s", exc)
        return

    if not active_fixtures:
        return

    logger.info("[wc_fixture_sync] Checking live scores for %d active matches", len(active_fixtures))

    # 2. Fetch scores from API
    try:
        url = "https://api.odds-api.com/v4/sports/soccer_fifa_world_cup/scores"
        resp = requests.get(url, params={"apiKey": api_key, "daysFrom": 3}, timeout=10)
        if resp.status_code != 200:
            logger.warning("[wc_fixture_sync] Scores API status code %d", resp.status_code)
            return
        scores_data = resp.json()
    except Exception as exc:
        logger.warning("[wc_fixture_sync] Failed to fetch scores from API: %s", exc)
        return

    # Map external_id to score info
    scores_by_id = {s["id"]: s for s in scores_data}

    any_updated = False
    for ext_id, home, away in active_fixtures:
        score_info = scores_by_id.get(ext_id)
        if not score_info:
            continue

        if score_info.get("completed", False):
            # Parse scores
            scores_list = score_info.get("scores")
            home_score = None
            away_score = None
            if scores_list:
                for s in scores_list:
                    if canonicalize(s["name"]) == canonicalize(home):
                        home_score = int(s["score"])
                    elif canonicalize(s["name"]) == canonicalize(away):
                        away_score = int(s["score"])

            if home_score is not None and away_score is not None:
                # Update fixture in DB
                try:
                    with connect() as cur:
                        cur.execute(
                            """
                            UPDATE fixtures
                            SET status = 'finished',
                                home_score = %s,
                                away_score = %s,
                                last_synced = CURRENT_TIMESTAMP
                            WHERE external_id = %s
                            """,
                            (home_score, away_score, ext_id)
                        )
                    logger.info("[wc_fixture_sync] Match %s vs %s finished: %d-%d", home, away, home_score, away_score)
                    any_updated = True
                except Exception as exc:
                    logger.error("[wc_fixture_sync] DB error updating fixture %s: %s", ext_id, exc)

    if any_updated:
        # Trigger update of standings and settlement of bets
        try:
            update_group_standings()
            settle_pending_picks()
            logger.info("[wc_fixture_sync] Standings updated and picks settled after match completion.")
        except Exception as exc:
            logger.error("[wc_fixture_sync] Error in post-sync update/settlement: %s", exc)
