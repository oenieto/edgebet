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
_elo_map: dict[str, float] | None = None


def _ensure_model() -> None:
    """Refresca el histórico (si tiene >24h) y ajusta el predictor Poisson una vez.

    Sin fuente de datos (caso actual), el CSV queda vacío, el Poisson no se
    ajusta y todo cae a ELO de forma honesta. No crashea nunca.
    """
    global _model_ready, _elo_map
    if _model_ready:
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
