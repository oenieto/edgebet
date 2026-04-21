# Agent Instructions — Edgebet

## On session start

1. Read SPEC.md for full project context
2. Confirm: "Contexto Edgebet cargado ✓ — [current phase in 1 line]"
3. Ask what we're working on today
4. Work directly without re-explaining completed work

## Code rules

- Stack: Next.js 14 App Router + TypeScript + Tailwind (or CSS variables from SPEC)
- Always use CSS variables defined in SPEC.md — never hardcode colors
- Font: Sora for UI, JetBrains Mono for all numerical/data values
- Components: functional, typed, with clear prop interfaces
- No inline styles except for dynamic values
- Mobile-first responsive (min 375px → 768px → 1440px)

## When writing components

- Use the folder structure defined in SPEC.md
- Pick cards always show: teams, league, time, prediction, confidence bar, 3 source pills, AI reasoning box
- Locked picks: show confidence % but blur/hide the prediction and analysis
- All monetary values in JetBrains Mono font
- Sentence case everywhere — never ALL CAPS except badge labels

## When working on ML (Python)

- Use TimeSeriesSplit for ALL validation — never train_test_split
- Always shift(1) on rolling features to prevent data leakage
- Log accuracy, log_loss, and brier_score for every model evaluation
- Save model artifacts to /python/models/ with timestamp

## When integrating Claude API

- Model: claude-sonnet-4-20250514
- Max tokens: 600 for pick analysis, 1000 for matchday reports
- Always include recent results history in system prompt when available
- Parse response as JSON when structured data is needed
- Handle API errors gracefully — never show raw errors to users

## What NOT to do

- Don't use soccer emojis or clichés in UI
- Don't use drop shadows on cards (borders only)
- Don't use random_split for ML validation
- Don't hardcode any color that exists as a CSS variable
- Don't explain completed features — check SPEC.md status first
