"""
Edgebet — visualizaciones matplotlib.

Genera:
  - scatter de divergencia Bookmaker vs Polymarket (3 outcomes)
  - radar triple layer por partido (ML / Polymarket / Bet365)

Guardadas en /python/reports/figures/ con timestamp.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path(__file__).resolve().parent / "reports" / "figures"

# Paleta Edgebet (fintech premium)
COLOR_ML = "#6366F1"       # indigo
COLOR_POLY = "#10B981"     # emerald
COLOR_BK = "#F59E0B"       # amber
COLOR_HOME = "#10B981"
COLOR_DRAW = "#F59E0B"
COLOR_AWAY = "#EF4444"


def _ensure_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def plot_probability_divergence(
    picks: list[dict],
    save_name: str | None = None,
) -> Path | None:
    """
    Scatter bookmaker vs polymarket por outcome. Los puntos lejos de la
    diagonal indican divergencia → potencial edge.

    picks: lista de dicts con bkProb y polyProb (None se ignoran).
    """
    import matplotlib.pyplot as plt

    pairs = [p for p in picks if p.get("bkProb") and p.get("polyProb")]
    if not pairs:
        print("[viz] no hay picks con Polymarket para scatter")
        return None

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    outcomes = [("home", "Victoria local", COLOR_HOME),
                ("draw", "Empate", COLOR_DRAW),
                ("away", "Victoria visitante", COLOR_AWAY)]

    for ax, (key, title, color) in zip(axes, outcomes):
        bk = [p["bkProb"][key] for p in pairs]
        poly = [p["polyProb"][key] for p in pairs]
        ax.scatter(bk, poly, alpha=0.75, color=color, edgecolors="white", s=70)
        ax.plot([0, 1], [0, 1], "--", color="#94A3B8", linewidth=1, alpha=0.5)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.set_xlabel("Prob. Bet365", fontsize=10)
        ax.set_ylabel("Prob. Polymarket", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(alpha=0.15)

    fig.suptitle(
        "Divergencia Bet365 vs Polymarket — puntos alejados de la diagonal = edge",
        fontsize=13, y=1.02,
    )
    plt.tight_layout()

    out_dir = _ensure_dir()
    fname = save_name or f"divergence_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.png"
    path = out_dir / fname
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_triple_layer_radar(
    pick: dict,
    save_name: str | None = None,
) -> Path | None:
    """
    Radar por partido comparando ML / Polymarket / Bet365 sobre 3 outcomes.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    if not pick.get("mlProb") or not pick.get("bkProb"):
        print("[viz] pick sin probabilidades completas")
        return None

    labels = ["Local", "Empate", "Visitante"]
    keys = ["home", "draw", "away"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    def _close(values):
        return list(values) + [values[0]]

    ml_vals = _close([pick["mlProb"][k] for k in keys])
    bk_vals = _close([pick["bkProb"][k] for k in keys])
    poly_vals = _close([pick["polyProb"][k] for k in keys]) if pick.get("polyProb") else None

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    ax.plot(angles, ml_vals, color=COLOR_ML, linewidth=2, label="ML model")
    ax.fill(angles, ml_vals, color=COLOR_ML, alpha=0.18)
    ax.plot(angles, bk_vals, color=COLOR_BK, linewidth=2, label="Bet365")
    ax.fill(angles, bk_vals, color=COLOR_BK, alpha=0.15)
    if poly_vals:
        ax.plot(angles, poly_vals, color=COLOR_POLY, linewidth=2, label="Polymarket")
        ax.fill(angles, poly_vals, color=COLOR_POLY, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(["20%", "40%", "60%", "80%"], fontsize=8, color="#64748B")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.05), fontsize=10)

    title = pick.get("match", f"{pick.get('homeTeam','?')} vs {pick.get('awayTeam','?')}")
    ax.set_title(title, y=1.12, fontsize=14, fontweight="bold")

    out_dir = _ensure_dir()
    safe = title.replace(" ", "_").replace("/", "_")
    fname = save_name or f"radar_{safe}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.png"
    path = out_dir / fname
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_confidence_vs_ev(
    picks: list[dict],
    save_name: str | None = None,
) -> Path | None:
    """Vista agregada: confianza vs EV% por pick, color por tier."""
    import matplotlib.pyplot as plt

    if not picks:
        return None
    tier_colors = {"free": "#94A3B8", "premium": COLOR_ML, "vip": COLOR_POLY}
    fig, ax = plt.subplots(figsize=(10, 6))
    for tier, color in tier_colors.items():
        xs = [p["confidence"] for p in picks if p.get("status") == tier]
        ys = [p.get("evPct", 0) for p in picks if p.get("status") == tier]
        ax.scatter(xs, ys, color=color, label=tier.upper(), s=70, alpha=0.85, edgecolors="white")

    ax.axhline(0, color="#CBD5E1", linewidth=1)
    ax.axhline(8, color="#CBD5E1", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Confianza modelo (%)", fontsize=11)
    ax.set_ylabel("EV esperado (%)", fontsize=11)
    ax.set_title("Distribución de picks: confianza vs EV", fontsize=13, fontweight="bold")
    ax.grid(alpha=0.15)
    ax.legend()

    out_dir = _ensure_dir()
    fname = save_name or f"confidence_ev_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.png"
    path = out_dir / fname
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path
