"""
Edgebet — export de reportes de matchday a JSON + visualizaciones.

Uso:
    python python/reports.py

Crea:
    /python/reports/matchday_YYYYMMDD_HHMM.json      (picks completos)
    /python/reports/summary_YYYYMMDD_HHMM.json       (resumen agregado)
    /python/reports/figures/divergence_*.png
    /python/reports/figures/confidence_ev_*.png
    /python/reports/figures/radar_<match>_*.png (top 3 picks)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PY_ROOT = Path(__file__).resolve().parent
if str(PY_ROOT) not in sys.path:
    sys.path.insert(0, str(PY_ROOT))

REPORTS_DIR = PY_ROOT / "reports"


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")


def _summary(picks: list[dict]) -> dict:
    if not picks:
        return {"count": 0}

    by_tier: dict[str, int] = {}
    for p in picks:
        by_tier[p.get("status", "free")] = by_tier.get(p.get("status", "free"), 0) + 1

    recommended = [p for p in picks if p.get("evPct", 0) >= 5.0 and p.get("edgePp", 0) >= 3.0]
    avg_ev = sum(p.get("evPct", 0) for p in picks) / len(picks)
    top = sorted(picks, key=lambda p: p.get("evPct", 0), reverse=True)[:5]

    return {
        "count": len(picks),
        "by_tier": by_tier,
        "recommended_count": len(recommended),
        "avg_ev_pct": round(avg_ev, 2),
        "polymarket_coverage": sum(1 for p in picks if p.get("polyProb")),
        "sources_agree_count": sum(1 for p in picks if p.get("sourcesAgree")),
        "ensemble_used_count": sum(1 for p in picks if p.get("modelSource") == "ensemble"),
        "top_5_by_ev": [
            {
                "match": t["match"],
                "league": t["league"],
                "prediction": t["prediction"],
                "confidence": t["confidence"],
                "evPct": t.get("evPct"),
                "edgePp": t.get("edgePp"),
                "odds": t.get("odds"),
                "status": t.get("status"),
            }
            for t in top
        ],
    }


def export_matchday_report(picks: list[dict] | None = None) -> dict[str, Path]:
    """Genera JSON + figuras del matchday. Devuelve paths creados."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if picks is None:
        from api.picks_service import get_todays_picks
        picks = get_todays_picks()

    tag = _now_tag()
    out: dict[str, Path] = {}

    full_path = REPORTS_DIR / f"matchday_{tag}.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(
            {"generated_at": tag, "picks": picks},
            f, ensure_ascii=False, indent=2, default=str,
        )
    out["full"] = full_path

    summary_path = REPORTS_DIR / f"summary_{tag}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {"generated_at": tag, **_summary(picks)},
            f, ensure_ascii=False, indent=2, default=str,
        )
    out["summary"] = summary_path

    try:
        from visualizations import (
            plot_probability_divergence,
            plot_confidence_vs_ev,
            plot_triple_layer_radar,
        )
        div = plot_probability_divergence(picks, save_name=f"divergence_{tag}.png")
        if div:
            out["divergence"] = div

        conf = plot_confidence_vs_ev(picks, save_name=f"confidence_ev_{tag}.png")
        if conf:
            out["confidence_ev"] = conf

        top3 = sorted(picks, key=lambda p: p.get("evPct", 0), reverse=True)[:3]
        for i, pick in enumerate(top3, 1):
            slug = pick.get("match", f"match{i}").replace(" ", "_").replace("/", "_")
            r = plot_triple_layer_radar(pick, save_name=f"radar_{i}_{slug}_{tag}.png")
            if r:
                out[f"radar_{i}"] = r
    except Exception as exc:
        print(f"[reports] visualización falló: {exc}")

    return out


if __name__ == "__main__":
    paths = export_matchday_report()
    print("\n✓ Reporte generado:")
    for name, p in paths.items():
        print(f"  {name:15s} → {p}")
