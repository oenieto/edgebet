"""
Performance metrics time-series generator.

Produces realistic synthetic data for the performance dashboard
until the settlement engine (Sprint 3) provides real resolved picks.
Once settlement is live, replace `_synthetic_*` functions with DB queries.
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, timedelta


def build_performance_series(days: int = 30) -> dict:
    """Return accuracy_series, roi_series, and league_breakdown."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    accuracy_series = []
    roi_series = []
    cumulative_roi = 0.0

    for i in range(days):
        d = start + timedelta(days=i)
        day_seed = _day_hash(d)

        # Accuracy oscillates around 61% with realistic variance
        base_acc = 0.61 + 0.04 * math.sin(day_seed * 0.7) + 0.02 * math.cos(day_seed * 1.3)
        acc = max(0.45, min(0.78, base_acc))

        # Daily ROI: positive bias (~+0.8%/day) with variance
        daily_roi = 0.008 + 0.015 * math.sin(day_seed * 2.1) + 0.005 * math.cos(day_seed * 0.9)
        cumulative_roi += daily_roi

        picks_count = 8 + int(4 * abs(math.sin(day_seed * 1.1)))

        accuracy_series.append({
            "date": d.isoformat(),
            "accuracy": round(acc, 4),
            "picks_resolved": picks_count,
        })
        roi_series.append({
            "date": d.isoformat(),
            "daily_roi": round(daily_roi, 4),
            "cumulative_roi": round(cumulative_roi, 4),
        })

    league_breakdown = _league_breakdown(today)

    return {
        "period_days": days,
        "accuracy_series": accuracy_series,
        "roi_series": roi_series,
        "league_breakdown": league_breakdown,
        "summary": {
            "avg_accuracy": round(sum(a["accuracy"] for a in accuracy_series) / len(accuracy_series), 4),
            "total_roi": round(cumulative_roi, 4),
            "total_picks": sum(a["picks_resolved"] for a in accuracy_series),
            "best_day": max(accuracy_series, key=lambda x: x["accuracy"])["date"],
            "worst_day": min(accuracy_series, key=lambda x: x["accuracy"])["date"],
        },
    }


def _league_breakdown(ref_date: date) -> list[dict]:
    """Hit rate by league — synthetic but stable per day."""
    leagues = [
        ("premier_league", "Premier League", 0.63),
        ("la_liga", "La Liga", 0.59),
        ("bundesliga", "Bundesliga", 0.62),
        ("serie_a", "Serie A", 0.58),
        ("ligue_1", "Ligue 1", 0.56),
        ("champions_league", "Champions League", 0.65),
    ]
    seed = _day_hash(ref_date)
    result = []
    for slug, name, base_acc in leagues:
        league_seed = int(hashlib.md5(f"{slug}{ref_date}".encode()).hexdigest()[:8], 16) % 1000 / 1000
        acc = base_acc + 0.03 * math.sin(league_seed * 6.28)
        picks = 15 + int(10 * league_seed)
        result.append({
            "slug": slug,
            "name": name,
            "accuracy": round(acc, 4),
            "picks_resolved": picks,
            "roi": round((acc - 0.52) * 0.8, 4),
        })
    return sorted(result, key=lambda x: x["accuracy"], reverse=True)


def _day_hash(d: date) -> float:
    """Deterministic float 0-1 from a date (stable across runs)."""
    h = hashlib.md5(d.isoformat().encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF
