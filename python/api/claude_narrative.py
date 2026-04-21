"""
Edgebet — capa Claude (narrativa) en producción.

Envoltorio fino sobre `claude_analysis.analyze_match` con:
  - cache TTL en memoria (evitar duplicados dentro del mismo matchday)
  - fallback silencioso si no hay API key / créditos / error de red
  - builder de reasoning enriquecido a partir del JSON de Claude
"""
from __future__ import annotations

import hashlib
import os
import time
from typing import Optional

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6h — suficiente para un matchday completo
_cache: dict[str, tuple[float, dict]] = {}


def _cache_key(home: str, away: str, league: str, ml_probs: dict, bk_probs: dict) -> str:
    raw = f"{home}|{away}|{league}|{round(ml_probs.get('home',0),3)}|{round(bk_probs.get('home',0),3)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _prune_cache() -> None:
    now = time.time()
    stale = [k for k, (ts, _) in _cache.items() if now - ts > CACHE_TTL_SECONDS]
    for k in stale:
        _cache.pop(k, None)


def claude_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _call_claude(
    home: str,
    away: str,
    league: str,
    home_form: dict,
    away_form: dict,
    ml_probs: dict,
    bookmaker_probs: dict,
    polymarket_probs: Optional[dict],
    poly_liquidity: float,
    poly_volume_24h: float,
) -> Optional[dict]:
    try:
        from claude_analysis import analyze_match  # import tardío; puede tardar por ssl
        return analyze_match(
            home_team=home,
            away_team=away,
            league=league,
            home_form=home_form,
            away_form=away_form,
            ml_probs=ml_probs,
            bookmaker_probs=bookmaker_probs,
            polymarket_probs=polymarket_probs,
            poly_liquidity=poly_liquidity,
            poly_volume_24h=poly_volume_24h,
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "credit" in msg or "api_key" in msg or "401" in msg:
            print(f"[claude] deshabilitado ({type(exc).__name__})")
        else:
            print(f"[claude] falló ({type(exc).__name__}): {exc}")
        return None


def generate_narrative(
    home: str,
    away: str,
    league: str,
    home_form: dict,
    away_form: dict,
    ml_probs: dict,
    bookmaker_probs: dict,
    polymarket_probs: Optional[dict] = None,
    poly_liquidity: float = 0.0,
    poly_volume_24h: float = 0.0,
) -> Optional[dict]:
    """
    Devuelve el JSON estructurado de Claude ({prediction, confidence, reasoning,
    key_factors, risks, suggested_stake_pct, divergence_flag, divergence_note}),
    o None si no se pudo generar.
    """
    if not claude_enabled():
        return None

    _prune_cache()
    key = _cache_key(home, away, league, ml_probs, bookmaker_probs)
    cached = _cache.get(key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    result = _call_claude(
        home=home,
        away=away,
        league=league,
        home_form=home_form,
        away_form=away_form,
        ml_probs=ml_probs,
        bookmaker_probs=bookmaker_probs,
        polymarket_probs=polymarket_probs,
        poly_liquidity=poly_liquidity,
        poly_volume_24h=poly_volume_24h,
    )
    if not result or result.get("error"):
        return None
    _cache[key] = (time.time(), result)
    return result


def merge_narrative_into_pick(pick: dict, narrative: Optional[dict]) -> dict:
    """Inyecta el análisis de Claude en el pick, respetando el fallback determinista."""
    if not narrative:
        return pick

    reasoning_parts: list[str] = []
    if narrative.get("reasoning"):
        reasoning_parts.append(str(narrative["reasoning"]).strip())
    if narrative.get("divergence_note"):
        reasoning_parts.append(str(narrative["divergence_note"]).strip())
    if narrative.get("key_factors"):
        factors = [str(f).strip() for f in narrative["key_factors"] if f]
        if factors:
            reasoning_parts.append("Factores clave: " + "; ".join(factors[:3]) + ".")
    if narrative.get("risks"):
        risks = [str(r).strip() for r in narrative["risks"] if r]
        if risks:
            reasoning_parts.append("Riesgos: " + "; ".join(risks[:2]) + ".")

    if reasoning_parts:
        pick["aiReasoning"] = " ".join(reasoning_parts)

    if isinstance(narrative.get("confidence"), (int, float)):
        pick["confidence"] = int(round(float(narrative["confidence"])))

    if isinstance(narrative.get("suggested_stake_pct"), (int, float)):
        stake = float(narrative["suggested_stake_pct"])
        det_stake = float(pick.get("suggestedStake", 0))
        # Combinamos conservadoramente: el mínimo entre Claude y determinista
        if det_stake > 0:
            pick["suggestedStake"] = round(min(stake, det_stake), 2)
        else:
            pick["suggestedStake"] = round(stake, 2)

    pick["claudeAnalysis"] = narrative
    return pick
