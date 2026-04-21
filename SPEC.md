# Edgebet — Project Specification

## What is Edgebet

Premium AI-powered football betting analytics platform. Combines three probability layers to generate picks with reasoning, not just numbers.

### Three-layer system

1. **ML Model** (XGBoost + ELO + xG proxy) — 40% weight
2. **Polymarket** (blockchain prediction markets, Gamma API) — 35% weight
3. **Bet365 odds** (normalized implied probabilities) — 25% weight
4. **Claude API** — final synthesis layer, generates natural language analysis

Key insight: when the three sources diverge significantly, that's the "edge". Claude analyzes those divergences.

---

## Business Model

| Tier         | Price  | Features                                                 |
| ------------ | ------ | -------------------------------------------------------- |
| Free         | $0     | 2–3 picks/week, basic analysis                           |
| Pro          | $19/mo | All picks + full AI analysis + bankroll tracker + alerts |
| VIP          | $49/mo | Pro + high-confidence picks (>75%) + private Discord     |
| Pay-per-pick | $5–15  | Individual premium pick unlock                           |

Community channels: Instagram (educational content), Telegram (automated alerts), Discord (Pro/VIP community)

---

## Tech Stack

```
Frontend web:    React + Next.js 14 (App Router)
Frontend mobile: React Native (Phase 2)
Backend:         Python + FastAPI
Database:        PostgreSQL
ML:              Python — XGBoost, scikit-learn, pandas, numpy
AI:              Claude API (claude-sonnet-4-20250514)
Football data:   football-data.co.uk + API-Football
Markets:         Polymarket Gamma API (public, no auth)
Payments:        Stripe
Notifications:   Telegram Bot API + Web Push
```

---

## Visual Identity

```
Name:          Edgebet ("Edge" bold + "bet" light, same font)
Primary:       #6366F1 (indigo)
Success:       #10B981 (emerald green)
Warning:       #F59E0B (amber)
Danger:        #EF4444 (red)
Dark bg:       #0F172A
Light bg:      #F8F9FF
Card bg:       #FFFFFF
Font display:  Sora (Google Fonts)
Font mono:     JetBrains Mono
Style:         Fintech premium — no soccer clichés
```

---

## Project Status

### ✅ Done

- Complete visual design (login, homepage, dashboard, onboarding wizard)
- Brand identity (Edgebet, indigo/emerald palette, Sora font)
- Full user flow mapped (login → onboarding → personalized plan → dashboard)
- Navigable mockups of all main views
- Login page code (from Stitch)
- Homepage code (from Stitch)
- System architecture documented
- Business model defined

### 🔄 In Progress

- Web implementation in Google Antigravity
- Next.js project structure setup

### ⏳ Pending

- ML data pipeline (football-data.co.uk loader)
- Feature engineering (ELO, xG proxy, rolling averages, H2H)
- XGBoost model training with backtesting
- Polymarket Gamma API integration
- Claude API integration for analysis
- Three-layer picks system
- Bankroll tracker with smart alerts
- Stripe payment system
- Telegram bot
- React Native mobile app

---

## Folder Structure

```
/app
  /page.tsx              → public homepage
  /login/page.tsx        → login
  /dashboard/page.tsx    → dashboard (protected)
  /picks/page.tsx        → picks view
  /bankroll/page.tsx     → bankroll tracker
  /historial/page.tsx    → history (auditable)
  /perfil/page.tsx       → user profile
/components
  /ui/                   → base components (Button, Card, Badge, etc.)
  /picks/                → PickCard, PickList, ConfidenceBar
  /bankroll/             → BankrollTracker, SparkLine, AlertBanner
  /onboarding/           → wizard steps
/lib
  /api/                  → API calls (football data, Polymarket)
  /ml/                   → Python ML model integration
  /claude/               → Claude API wrapper
  /stripe/               → payment integration
/styles
  /globals.css           → CSS variables + reset
/python
  /data/                 → data loaders
  /features/             → feature engineering
  /models/               → ML models
  /api/                  → FastAPI endpoints
```

---

## CSS Variables (always use these)

```css
:root {
  --ind: #6366f1;
  --ind-d: #4f46e5;
  --ind-l: #e0e7ff;
  --ind-ll: #f0f1ff;
  --em: #10b981;
  --em-d: #059669;
  --em-l: #d1fae5;
  --dk: #0f172a;
  --dk2: #1e293b;
  --lt: #f8f9ff;
  --lt2: #f1f5f9;
  --tx: #0f172a;
  --tx2: #475569;
  --tx3: #94a3b8;
  --am: #f59e0b;
  --am-l: #fef3c7;
  --rd: #ef4444;
  --rd-l: #fee2e2;
  --font: "Sora", sans-serif;
  --mono: "JetBrains Mono", monospace;
  --r: 12px;
  --rlg: 16px;
  --rpill: 999px;
}
```

---

## ML Architecture

### Features per match

- Rolling averages last 5 games: goals, shots, corners, cards
- ELO ratings (updated after each match, home advantage +65)
- xG proxy: `HST*0.30 + (HS-HST)*0.03`
- Fatigue: rest days between matches (capped at 30)
- H2H: last 5 head-to-head results
- Bet365 normalized probabilities (margin removed)
- Polymarket contract prices (price = probability)

### Divergence features (most valuable)

- KL-divergence between Bet365 and Polymarket
- Absolute difference per outcome (H/D/A)
- sources_agree flag: do all three agree on favorite?
- Weighted blend: `0.40*ML + 0.35*Poly + 0.25*BK`

### Validation

- ALWAYS use TimeSeriesSplit — never random split (prevents data leakage)
- Target: accuracy >55%, log loss <1.0
- Walk-forward backtest: 500 match initial window, 38-match steps

---

## Claude API System Prompt (use in backend)

```
You are the Edgebet analysis engine. Synthesize data from three probability sources
(ML model, Polymarket, Bet365) into clear, honest, actionable analysis in Spanish.

For each pick, always provide:
1. Main prediction + confidence (0-100%)
2. Divergence analysis: do the 3 sources agree?
3. Max 3 key supporting factors
4. Max 2 main risks
5. Suggested stake (Kelly simplified as % of bankroll)

Rules: be direct, no filler, max 120 words, never guarantee results,
respond in Spanish, use JSON format when requested.
```
