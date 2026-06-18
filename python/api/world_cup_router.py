"""
Edgebet — endpoint público del dashboard del Mundial 2026.

GET /world-cup/dashboard devuelve la vista por grupo (A–L) con probabilidades
estimadas y estadísticas por selección.

Honestidad de datos (regla dura del proyecto):
  - Las probabilidades 1X2 se derivan del ELO curado de selecciones (modelo
    propio), por eso CADA selección se marca `estimated: true`.
  - Los campos estadísticos (goles por partido, BTTS, córners, tarjetas,
    posesión, remates, forma, dato caliente, resultados del Mundial) NO tienen
    fuente real hoy: match_stats y predictions están vacías y no hay histórico
    de selecciones. Se devuelven como `null` y el frontend los muestra como "—".
    NUNCA se inventan números.
  - Los resultados de partidos del Mundial salen de `fixtures` (status=finished)
    si existen; si no, `null`.

No requiere autenticación (endpoint público de solo lectura).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from api.db import connect
from api.world_cup import list_groups, team_elo, WCTeam
from api.poisson_predictor import get_national_predictor

router = APIRouter(prefix="/world-cup", tags=["world-cup"])
logger = logging.getLogger("edgebet.worldcup")

# Reparto base de empates para mapear la expectativa ELO (0..1) a 1X2.
_DRAW_BASE = 0.24

# Estado del modelo (perezoso): se refresca el CSV y se ajusta Poisson en la
# primera petición, luego se cachea. _elo_map se deriva del histórico si existe.
_model_ready = False
_model_csv_mtime: float | None = None
_elo_map: dict[str, float] | None = None


def _ensure_model() -> None:
    """Refresca el histórico (si tiene >24h) y ajusta el predictor Poisson.

    Se reajusta automáticamente cuando cambia el mtime del CSV (p.ej. tras el
    refresh diario del scheduler), así el dashboard recoge datos nuevos sin
    reiniciar el proceso. Sin datos, todo cae a ELO de forma honesta. No crashea.
    """
    global _model_ready, _elo_map, _model_csv_mtime
    from data.national_team_loader import HISTORY_CSV
    try:
        cur_mtime = HISTORY_CSV.stat().st_mtime if HISTORY_CSV.exists() else None
    except OSError:
        cur_mtime = None
    if _model_ready and cur_mtime == _model_csv_mtime:
        return
    try:
        from data.national_team_loader import refresh_if_stale
        refresh_if_stale(max_age_hours=24)
    except Exception as exc:
        logger.warning("[worldcup] refresh histórico falló: %s", exc)
    try:
        from features.elo import load_national_team_history, compute_national_elo_from_history
        df = load_national_team_history()
        get_national_predictor().fit_national_teams(df)
        _elo_map = compute_national_elo_from_history(df) if len(df) > 0 else None
    except Exception as exc:
        logger.warning("[worldcup] fit Poisson/ELO falló: %s", exc)
        _elo_map = None
    # Re-stat tras el posible refresh para no reajustar en la próxima petición.
    try:
        _model_csv_mtime = HISTORY_CSV.stat().st_mtime if HISTORY_CSV.exists() else None
    except OSError:
        _model_csv_mtime = None
    _model_ready = True


def _elo_of(key: str) -> float:
    """ELO de una selección: del histórico si está disponible, si no el curado."""
    if _elo_map and key in _elo_map:
        return float(_elo_map[key])
    return team_elo(key)


def _neutral_1x2(elo_team: float, elo_opp: float) -> tuple[float, float, float]:
    """Probabilidad neutral (sin ventaja de localía) win/draw/loss desde ELO."""
    e = 1.0 / (1.0 + 10 ** ((elo_opp - elo_team) / 400.0))
    win = e * (1.0 - _DRAW_BASE)
    loss = (1.0 - e) * (1.0 - _DRAW_BASE)
    return win, _DRAW_BASE, loss


def _team_probs(team: WCTeam, group: list[WCTeam]) -> tuple[dict[str, int], str]:
    """Probabilidad media de la selección contra sus 3 rivales de grupo.

    Intenta Poisson histórico; si no todos los enfrentamientos tienen datos
    reales, cae a ELO. Devuelve (pct, data_source).
    """
    opps = [t for t in group if t.key != team.key]
    if not opps:
        return {"win": 33, "draw": 34, "loss": 33}, "elo_estimate"

    predictor = get_national_predictor()
    elo_team = _elo_of(team.key)
    w = d = l = 0.0
    for opp in opps:
        r = predictor.predict(team.key, opp.key)
        if r.get("data_source") == "poisson_historical":
            w += r["home"]; d += r["draw"]; l += r["away"]
        else:
            # La dupla no tiene datos suficientes → ELO neutral para ese rival.
            pw, pd, pl = _neutral_1x2(elo_team, _elo_of(opp.key))
            w += pw; d += pd; l += pl
    n = len(opps)
    pct = _to_pct({"win": w / n, "draw": d / n, "loss": l / n})

    # La selección es "Poisson histórico" si SU propia fuerza viene de partidos
    # reales (≥3), aunque algún rival de grupo no tenga datos (ese cruce usó ELO).
    data_source = "poisson_historical" if predictor.has_team_data(team.key) else "elo_estimate"
    return pct, data_source


def _to_pct(probs: dict[str, float]) -> dict[str, int]:
    """Convierte floats (~suma 1) a enteros que suman exactamente 100."""
    raw = {k: v * 100.0 for k, v in probs.items()}
    ints = {k: int(round(v)) for k, v in raw.items()}
    diff = 100 - sum(ints.values())
    if diff != 0:
        kmax = max(ints, key=lambda k: raw[k])
        ints[kmax] += diff
    return ints


def _overall_signal(prob_win: int | None, form: list[str] | None) -> str:
    """green/yellow/red. Verde requiere 3+ victorias en los últimos 5 partidos
    del Mundial; sin esos resultados (form null) sigue siendo inalcanzable —
    comportamiento honesto hasta que haya partidos jugados."""
    wins = sum(1 for r in (form or []) if r == "W")
    losses = sum(1 for r in (form or []) if r == "L")
    if prob_win is not None and prob_win >= 48 and wins >= 3:
        return "green"
    if (prob_win is not None and prob_win < 22) or losses >= 3:
        return "red"
    return "yellow"


def _load_finished_wc_results() -> dict[str, dict]:
    """Último resultado terminado del Mundial por selección (key canónica).

    Devuelve {} si no hay partidos terminados. Nunca inventa resultados.
    """
    results: dict[str, dict] = {}
    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT home_team, away_team, home_score, away_score, kickoff
                FROM fixtures
                WHERE status = 'finished'
                  AND (
                    league_slug LIKE '%world%' OR league_slug LIKE '%fifa%'
                    OR league_slug = 'FIFA World Cup 2026'
                  )
                ORDER BY kickoff ASC
                """
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning("[worldcup] no pude leer fixtures terminados: %s", exc)
        return results

    for r in rows:
        home = r["home_team"] if hasattr(r, "keys") else r[0]
        away = r["away_team"] if hasattr(r, "keys") else r[1]
        hs = r["home_score"] if hasattr(r, "keys") else r[2]
        as_ = r["away_score"] if hasattr(r, "keys") else r[3]
        if hs is None or as_ is None:
            continue
        hs, as_ = int(hs), int(as_)
        # Iteramos en orden ascendente, así el último que escribimos es el más reciente.
        results[home] = {"result": "W" if hs > as_ else "D" if hs == as_ else "L", "score": f"{hs}-{as_}"}
        results[away] = {"result": "W" if as_ > hs else "D" if as_ == hs else "L", "score": f"{as_}-{hs}"}
    return results


def _build_team_obj(team: WCTeam, group: list[WCTeam], wc_results: dict[str, dict]) -> dict:
    probs, data_source = _team_probs(team, group)
    last = wc_results.get(team.key)
    is_real = data_source == "poisson_historical"

    # Campos sin fuente de datos real → null (el frontend muestra "—").
    gf = gc = btts = corners_for = corners_against = cards = possession = shots = None
    form_last5 = None
    hot_stat = None
    over25 = None
    corners_line = cards_line = None

    return {
        "team": team.name,
        "flag": team.flag,
        "confederation": team.confederation,
        "wc_result": last["result"] if last else None,
        "wc_score": last["score"] if last else None,
        # Probabilidades estimadas (promedio ELO sobre rivales de grupo).
        "prob_win": probs["win"],
        "prob_draw": probs["draw"],
        "prob_loss": probs["loss"],
        # Goles (sin histórico de selecciones → null).
        "gf_per_game": gf,
        "gc_per_game": gc,
        "over25_tendency": over25,
        # Mercado.
        "btts_pct": btts,
        "corners_for": corners_for,
        "corners_against": corners_against,
        "corners_line": corners_line,
        "cards_avg": cards,
        "cards_line": cards_line,
        # Estilo.
        "possession_avg": possession,
        "shots_on_target": shots,
        # Forma.
        "form_last5": form_last5,
        # Dato caliente.
        "hot_stat": hot_stat,
        # Señal combinada.
        "overall_signal": _overall_signal(probs["win"], form_last5),
        # Origen del dato: poisson_historical (real) o elo_estimate (fallback).
        "data_source": data_source,
        # estimated=false solo cuando hay Poisson histórico real.
        "estimated": not is_real,
    }


def _build_top_picks(groups: dict[str, list[WCTeam]], teams_by_name: dict[str, dict]) -> list[dict]:
    """Top 6 por (prob_win·0.4 + gf·10·0.3 + victorias_ult5·0.3). Sin gf/forma
    reales, el ranking queda dominado por la probabilidad estimada (ELO)."""
    scored = []
    for group in groups.values():
        for team in group:
            obj = teams_by_name[team.name]
            gf = obj["gf_per_game"] or 0
            form = obj["form_last5"] or []
            wins = sum(1 for r in form if r == "W")
            score = (obj["prob_win"] or 0) * 0.4 + gf * 10 * 0.3 + wins * 0.3
            scored.append((score, team, obj))

    scored.sort(key=lambda x: x[0], reverse=True)
    labels = ["Favorito", "Favorito", "Contendiente", "Contendiente", "Dark Horse", "Dark Horse"]
    out = []
    for i, (_score, team, obj) in enumerate(scored[:6]):
        if obj.get("data_source") == "poisson_historical":
            hot = f"Victoria media estimada {obj['prob_win']}% · Poisson histórico"
        else:
            hot = f"ELO {_elo_of(team.key):.0f} · victoria media estimada {obj['prob_win']}% (sin stats de partido)"
        out.append({
            "rank": i + 1,
            "team": team.name,
            "flag": team.flag,
            "label": labels[i] if i < len(labels) else "Sorpresa",
            "hot_stat": hot,
            "signal": obj["overall_signal"],
        })
    return out


@router.get("/dashboard")
def world_cup_dashboard() -> dict:
    _ensure_model()
    groups = list_groups()
    wc_results = _load_finished_wc_results()

    out_groups = []
    teams_by_name: dict[str, dict] = {}
    any_real = False
    for letter, group in groups.items():
        team_objs = []
        for team in group:
            obj = _build_team_obj(team, group, wc_results)
            if obj.get("data_source") == "poisson_historical":
                any_real = True
            teams_by_name[team.name] = obj
            team_objs.append(obj)
        out_groups.append({"group": letter, "teams": team_objs})

    top_picks = _build_top_picks(groups, teams_by_name)

    # Etiqueta de modelo dinámica para el frontend (footer/disclaimer).
    model_label = "Poisson histórico" if any_real else "Estimación ELO"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_label": model_label,
        "groups": out_groups,
        "top_picks": top_picks,
    }


# ============================================================================
# Forma reciente + H2H de selecciones (lee national_teams_history.csv).
# Cache en memoria con TTL de 1h — NO se re-lee el CSV en cada request.
# ============================================================================
import time as _time

_HISTORY_CACHE: dict = {"rows": None, "ts": 0.0}
_HISTORY_TTL = 3600  # 1 hora


def _history_rows() -> list[dict]:
    now = _time.time()
    if _HISTORY_CACHE["rows"] is not None and (now - _HISTORY_CACHE["ts"]) < _HISTORY_TTL:
        return _HISTORY_CACHE["rows"]
    try:
        from data.national_team_loader import read_history
        rows = read_history()
    except Exception as exc:
        logger.warning("[worldcup] no pude leer histórico de selecciones: %s", exc)
        rows = []
    _HISTORY_CACHE["rows"] = rows
    _HISTORY_CACHE["ts"] = now
    return rows


def get_team_form(team_name: str, n: int = 10) -> dict:
    """Forma reciente de una selección desde el histórico (últimos n partidos)."""
    from data.team_name_map import canonicalize
    key = canonicalize(team_name)
    rows = [r for r in _history_rows() if r.get("home_team") == key or r.get("away_team") == key]
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    rows = rows[:n]

    form: list[str] = []
    wins = draws = losses = 0
    gf = ga = btts = over25 = 0
    recent: list[dict] = []
    for r in rows:
        is_home = r.get("home_team") == key
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        tg, og = (hg, ag) if is_home else (ag, hg)
        res = "W" if tg > og else ("D" if tg == og else "L")
        form.append(res)
        wins += res == "W"; draws += res == "D"; losses += res == "L"
        gf += tg; ga += og
        btts += hg > 0 and ag > 0
        over25 += (hg + ag) > 2.5
        if len(recent) < 5:
            recent.append({
                "date": r.get("date"), "home_team": r.get("home_team"), "away_team": r.get("away_team"),
                "home_goals": hg, "away_goals": ag, "competition": r.get("competition", ""),
                "result_for_team": res,
            })

    cnt = len(rows)
    return {
        "team": key,
        "matches_found": cnt,
        "form_last5": form[:5],
        "wins": wins, "draws": draws, "losses": losses,
        "gf_per_game": round(gf / cnt, 2) if cnt else 0.0,
        "gc_per_game": round(ga / cnt, 2) if cnt else 0.0,
        "btts_pct": round(btts / cnt * 100, 1) if cnt else 0.0,
        "over25_pct": round(over25 / cnt * 100, 1) if cnt else 0.0,
        "recent_matches": recent,
    }


def get_h2h(home_team: str, away_team: str, n: int = 5) -> dict:
    """Enfrentamientos directos entre dos selecciones (resultado desde el local)."""
    from data.team_name_map import canonicalize
    hk, ak = canonicalize(home_team), canonicalize(away_team)
    rows = [
        r for r in _history_rows()
        if {r.get("home_team"), r.get("away_team")} == {hk, ak}
    ]
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    rows = rows[:n]

    matches: list[dict] = []
    for r in rows:
        if r.get("home_team") == hk:
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
        else:
            hg, ag = int(r["away_goals"]), int(r["home_goals"])
        res = "W" if hg > ag else ("D" if hg == ag else "L")
        matches.append({
            "date": r.get("date"), "home_team": hk, "away_team": ak,
            "home_goals": hg, "away_goals": ag, "competition": r.get("competition", ""),
            "result_for_home": res,
        })
    return {"matches": matches, "found": len(matches)}


def _team_stats_pickshape(team_name: str, logo: str | None) -> dict:
    """Mapea get_team_form() a la forma TeamStats que consume el pick detail."""
    f = get_team_form(team_name, n=5)
    last5 = [
        {
            "date": m["date"],
            "home": m["home_team"], "away": m["away_team"],
            "score": f'{m["home_goals"]}-{m["away_goals"]}',
            "result": m["result_for_team"],
        }
        for m in f["recent_matches"]
    ]
    gf = sum(int(m["home_goals"]) if m["home_team"] == f["team"] else int(m["away_goals"]) for m in f["recent_matches"])
    ga = sum(int(m["away_goals"]) if m["home_team"] == f["team"] else int(m["home_goals"]) for m in f["recent_matches"])
    wins = sum(1 for m in f["recent_matches"] if m["result_for_team"] == "W")
    draws = sum(1 for m in f["recent_matches"] if m["result_for_team"] == "D")
    losses = sum(1 for m in f["recent_matches"] if m["result_for_team"] == "L")
    return {
        "team": team_name,
        "logo": logo,
        "form": "".join(f["form_last5"]),
        "elo": round(_elo_of(f["team"])),
        "last_5": last5,
        "aggregates": {"wins": wins, "draws": draws, "losses": losses,
                       "goals_for": gf, "goals_against": ga},
    }


def wc_pick_stats(home_team: str, away_team: str,
                  home_logo: str | None = None, away_logo: str | None = None) -> dict:
    """PickStatsResponse {h2h, home_stats, away_stats} para un partido del Mundial,
    construido desde el histórico real de selecciones."""
    h2h_raw = get_h2h(home_team, away_team, n=5)
    h2h = [
        {
            "date": m["date"], "home": m["home_team"], "away": m["away_team"],
            "homeLogo": home_logo, "awayLogo": away_logo,
            "score": f'{m["home_goals"]}-{m["away_goals"]}', "result": m["result_for_home"],
        }
        for m in h2h_raw["matches"]
    ]
    return {
        "h2h": h2h,
        "home_stats": _team_stats_pickshape(home_team, home_logo),
        "away_stats": _team_stats_pickshape(away_team, away_logo),
    }


@router.get("/team-stats/{team_name}")
def team_stats_endpoint(team_name: str) -> dict:
    return get_team_form(team_name, n=10)


@router.get("/h2h")
def h2h_endpoint(home: str, away: str) -> dict:
    return get_h2h(home, away, n=5)


def get_poisson_predictions(home_team: str, away_team: str) -> dict:
    """
    Computes expected goals lambdas, Dixon-Coles outcome probabilities,
    and argmax of score matrix for WC fixtures.
    """
    from api.poisson_predictor import get_national_predictor
    from api.poisson_markets import _poisson_pmf, _dc_tau
    pred = get_national_predictor()
    
    # Ensure predictor model is fitted
    if not pred.fitted:
        try:
            from features.elo import load_national_team_history
            df = load_national_team_history()
            pred.fit_national_teams(df)
        except Exception:
            pass

    has_data = pred.has_team_data(home_team) and pred.has_team_data(away_team)
    if has_data:
        lam_home = pred.league_avg * pred.national_attack[home_team] * pred.national_defense[away_team] * pred.home_factor
        lam_away = pred.league_avg * pred.national_attack[away_team] * pred.national_defense[home_team]
    else:
        # Fallback approximation based on ELO
        elo_h = _elo_of(home_team)
        elo_a = _elo_of(away_team)
        diff = elo_h - elo_a
        lam_home = max(1.35 + diff / 400.0, 0.2)
        lam_away = max(1.35 - diff / 400.0, 0.2)

    # Compute score matrix and find argmax (most likely score)
    max_p = -1.0
    best_score = "1-1"
    for i in range(6):
        for j in range(6):
            p = _dc_tau(i, j, lam_home, lam_away, -0.1) * _poisson_pmf(i, lam_home) * _poisson_pmf(j, lam_away)
            if p > max_p:
                max_p = p
                best_score = f"{i}-{j}"

    if has_data:
        res = pred.predict(home_team, away_team)
        ph, pd, pa = res["home"], res["draw"], res["away"]
    else:
        ph, pd, pa = _neutral_1x2(_elo_of(home_team), _elo_of(away_team))

    return {
        "predicted_home_goals": round(lam_home, 2),
        "predicted_away_goals": round(lam_away, 2),
        "predicted_most_likely_score": best_score,
        "prob_home": round(ph, 4),
        "prob_draw": round(pd, 4),
        "prob_away": round(pa, 4)
    }


@router.get("/fixtures")
def get_wc_fixtures(group: str | None = None, status: str | None = None, date: str | None = None) -> dict:
    _ensure_model()
    
    from api.world_cup import all_teams
    team_flags = {t.key: t.flag for t in all_teams()}
    
    query = """
        SELECT id, external_id, home_team, away_team, kickoff, status, 
               tournament_phase, match_group, round_number, home_score, away_score
        FROM fixtures
        WHERE league_slug = 'fifa-world-cup'
    """
    params = []
    
    if group:
        query += " AND match_group = %s"
        params.append(group.upper())
    if status:
        if status in ("scheduled", "finished"):
            query += " AND status = %s"
            params.append(status)
            
    try:
        with connect() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("[worldcup] DB error fetching fixtures: %s", exc)
        return {"fixtures": [], "total": 0}
        
    fixtures_list = []
    now = datetime.now(timezone.utc)
    
    for r in rows:
        fid = r["id"] if hasattr(r, "keys") else r[0]
        ext_id = r["external_id"] if hasattr(r, "keys") else r[1]
        home = r["home_team"] if hasattr(r, "keys") else r[2]
        away = r["away_team"] if hasattr(r, "keys") else r[3]
        ko = r["kickoff"] if hasattr(r, "keys") else r[4]
        stat = r["status"] if hasattr(r, "keys") else r[5]
        phase = r["tournament_phase"] if hasattr(r, "keys") else r[6]
        m_group = r["match_group"] if hasattr(r, "keys") else r[7]
        round_num = r["round_number"] if hasattr(r, "keys") else r[8]
        hs = r["home_score"] if hasattr(r, "keys") else r[9]
        as_ = r["away_score"] if hasattr(r, "keys") else r[10]
        
        # Parse kickoff datetime
        if isinstance(ko, str):
            if ko.endswith("Z"):
                ko = ko[:-1] + "+00:00"
            ko_dt = datetime.fromisoformat(ko).astimezone(timezone.utc)
        elif isinstance(ko, datetime):
            ko_dt = ko.astimezone(timezone.utc)
        else:
            ko_dt = now

        # Date filtering
        if date == "today":
            if ko_dt.date() != now.date():
                continue
        elif date == "upcoming":
            if ko_dt < now:
                continue
        elif date == "past":
            if ko_dt >= now:
                continue
                
        # Get Poisson predictions and ELO probabilities
        pred_data = get_poisson_predictions(home, away)
        
        # Get latest odds from snapshots
        best_odds = {"home": None, "draw": None, "away": None}
        try:
            with connect() as cur_odds:
                cur_odds.execute(
                    """
                    SELECT home_odds, draw_odds, away_odds
                    FROM odds_snapshots
                    WHERE fixture_id = %s
                    ORDER BY captured_at DESC
                    LIMIT 1
                    """,
                    (fid,)
                )
                row_odds = cur_odds.fetchone()
                if row_odds:
                    best_odds["home"] = row_odds["home_odds"] if hasattr(row_odds, "keys") else row_odds[0]
                    best_odds["draw"] = row_odds["draw_odds"] if hasattr(row_odds, "keys") else row_odds[1]
                    best_odds["away"] = row_odds["away_odds"] if hasattr(row_odds, "keys") else row_odds[2]
        except Exception:
            pass

        fixtures_list.append({
            "id": fid,
            "external_id": ext_id,
            "home_team": home,
            "home_flag": team_flags.get(home, "⚽"),
            "away_team": away,
            "away_flag": team_flags.get(away, "⚽"),
            "match_date": ko_dt.isoformat(),
            "status": stat,
            "tournament_phase": phase,
            "match_group": m_group,
            "round_number": round_num,
            "home_goals": hs,
            "away_goals": as_,
            "predicted_home_goals": pred_data["predicted_home_goals"],
            "predicted_away_goals": pred_data["predicted_away_goals"],
            "predicted_most_likely_score": pred_data["predicted_most_likely_score"],
            "prob_home": pred_data["prob_home"],
            "prob_draw": pred_data["prob_draw"],
            "prob_away": pred_data["prob_away"],
            "best_odds_home": best_odds["home"],
            "best_odds_draw": best_odds["draw"],
            "best_odds_away": best_odds["away"],
            "home_form": get_team_form(home)["form_last5"],
            "away_form": get_team_form(away)["form_last5"]
        })
        
    fixtures_list.sort(key=lambda x: x["match_date"])
    return {
        "fixtures": fixtures_list,
        "total": len(fixtures_list)
    }


@router.get("/predictions")
def get_wc_predictions() -> list[dict]:
    from api.picks_service import get_todays_picks
    picks = get_todays_picks(league_slug="fifa-world-cup")
    
    enriched_picks = []
    for p in picks:
        # copy dict to avoid changing cache
        p_copy = dict(p)
        home = p_copy["homeTeam"]
        away = p_copy["awayTeam"]
        p_copy["home_form"] = get_team_form(home)["form_last5"]
        p_copy["away_form"] = get_team_form(away)["form_last5"]
        p_copy["h2h"] = get_h2h(home, away, n=3)["matches"]
        enriched_picks.append(p_copy)
        
    return enriched_picks


@router.get("/standings")
def get_wc_standings() -> dict:
    from data.wc_standings_updater import get_standings_for_group
    groups_standings = {}
    for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        groups_standings[letter] = get_standings_for_group(letter)
        
    return {
        "groups": groups_standings,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


@router.get("/standings/{group_letter}")
def get_wc_group_standings(group_letter: str) -> list[dict]:
    from data.wc_standings_updater import get_standings_for_group
    return get_standings_for_group(group_letter.upper())


@router.get("/live")
def get_wc_live() -> dict:
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    three_hours_ago = now - timedelta(hours=3)
    
    try:
        with connect() as cur:
            cur.execute(
                """
                SELECT id, external_id, home_team, away_team, kickoff, status, match_group, round_number
                FROM fixtures
                WHERE league_slug = 'fifa-world-cup'
                  AND status != 'finished'
                  AND kickoff >= %s
                  AND kickoff <= %s
                """,
                (three_hours_ago.isoformat(), now.isoformat())
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("[worldcup] DB error fetching live: %s", exc)
        rows = []
        
    fixtures_list = []
    for r in rows:
        fixtures_list.append({
            "id": r["id"] if hasattr(r, "keys") else r[0],
            "external_id": r["external_id"] if hasattr(r, "keys") else r[1],
            "home_team": r["home_team"] if hasattr(r, "keys") else r[2],
            "away_team": r["away_team"] if hasattr(r, "keys") else r[3],
        })
        
    return {"fixtures": fixtures_list}
