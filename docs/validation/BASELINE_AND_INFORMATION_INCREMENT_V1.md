# Baseline and Information Increment V1

## Why Compare Against Simple Baselines?

A prediction model may appear accurate, but its value depends on whether it provides information **beyond** what trivial methods already capture. Without baseline comparison, one cannot distinguish genuine predictive skill from accidental correlation, regime-specific patterns, or random chance.

## The 10 Required Baselines

| ID | Name | Description |
|----|------|-------------|
| B1 | Always Neutral | Always predicts flat/unknown |
| B2 | Random Prior | Fixed probabilities from training distribution |
| B3 | Event Type Prior | Per-event-type historical distribution |
| B4 | Simple Sentiment Rule | Rule-based word list (no LLM) |
| B5 | Price Momentum | Pre-event price trend only |
| B6 | Funding Rule | Funding rate status only |
| B7 | OI Rule | Open interest change only |
| B8 | Static Macro Rule | Predefined macro direction rules |
| B9 | Regime-only Prior | Market regime only, no event content |
| B10 | Last-known Hit Rate | Historical event-type hit rate |

## Rules

1. Every baseline must be Point-in-Time compliant.
2. Baselines must not be deliberately weakened to make the candidate look better.
3. All baseline results must be reported — not just the worst-performing ones.
4. If a candidate cannot consistently beat B1 (Neutral), it provides zero information increment.

## Information Increment Scale

| Level | Meaning |
|-------|---------|
| none | No measurable improvement over best baseline |
| uncertain | Mixed results, weak signal |
| weak | Marginal improvement in some metrics |
| moderate | Consistent improvement across multiple metrics |
| strong | Robust improvement across regimes and metrics |
