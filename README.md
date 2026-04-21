# Edgebet

Premium AI-powered football betting analytics. Three probability layers (ML model + Polymarket + Bet365) synthesized by Claude into actionable picks.

See [SPEC.md](SPEC.md) for full product specification and [Claude.md](Claude.md) for agent instructions.

## Project layout

```
/app                      Next.js 14 App Router
  page.tsx                Homepage
  layout.tsx              Root layout (fonts + AuthProvider)
  globals.css             CSS variables + Tailwind directives
  /login/page.tsx         Login (4 mock providers)
  /dashboard              Protected area
    layout.tsx            Client-side auth gate
    page.tsx              Picks + metrics fetched from FastAPI
/components
  /picks/PickCard.tsx     ML/Poly/BK source pills + AI reasoning
/contexts/AuthContext.tsx localStorage-backed mock auth
/lib/api                  Backend fetch client (client.ts, picks.ts)
/types/index.ts           Pick, Metrics, ProbabilityTriplet, etc.
/login                    Stitch design reference (SVG + styles)
/python                   Backend (FastAPI + ML)
  /api/main.py            FastAPI entry (/health, /picks/today, /metrics)
  /data/loader.py         football-data.co.uk CSV loader
  /features               engineering.py, elo.py, polymarket.py
  /models/train.py        Ensemble training + walk-forward backtest
  claude_analysis.py      Claude API wrapper
  pipeline.py             ML pipeline orchestrator
  requirements.txt
```

## Run locally

### 1. Environment

```bash
cp .env.example .env
# Fill ANTHROPIC_API_KEY (only needed for Claude-powered picks)
```

### 2. Backend (FastAPI)

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Health check: <http://localhost:8000/health>
Docs: <http://localhost:8000/docs>

### 3. Frontend (Next.js)

In a separate terminal from the project root:

```bash
npm install
npm run dev
```

Open <http://localhost:3000>. The login page lives at `/login`, the dashboard at `/dashboard`.

Commands:

```
npm run dev         # Next dev server on port 3000
npm run build       # Production build
npm run start       # Serve production build
npm run lint        # next lint
npm run typecheck   # tsc --noEmit
```

## Current status

- Mock auth (localStorage) + protected `/dashboard` route via client-side auth gate
- FastAPI serves mock picks at `/picks/today` and `/metrics` — real ML pipeline exists but is not yet wired to the API
- ML pipeline (`python/pipeline.py`) trains an ensemble with TimeSeriesSplit — run via `python pipeline.py` from inside `python/`

## Next phases

1. Wire `pipeline.py` output into `/picks/today` (replace mock fixtures)
2. Persist picks + results (SQLite first, Postgres when schema stabilizes)
3. Bankroll tracker page
4. Stripe integration for Pro/VIP tiers
5. Telegram bot for alerts
6. Containerization (Docker Compose) once the team or deploy requires it

## Rules

- **ML validation:** always `TimeSeriesSplit`, never `train_test_split`. All rolling features must use `.shift(1)`.
- **Styling:** CSS variables from `app/globals.css` — never hardcode colors. Sora for UI, JetBrains Mono for numeric values.
- **Copy:** sentence case, Spanish in user-facing strings, no soccer clichés.
