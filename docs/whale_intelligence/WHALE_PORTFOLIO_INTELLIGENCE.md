# Whale Portfolio Intelligence

## Overview

Extends the W2 Whale Domain from single-address, single-position change detection
to multi-address portfolio-level intelligence. All computation is deterministic,
no AI, no network (unit tests), no wallet credentials.

## Architecture

```
portfolio_models.py      — Data models (WhalePortfolioSnapshot, etc.)
portfolio_metrics.py     — Pure metric computation functions
portfolio_risk.py        — 12 portfolio risk rules (PR1-PR12)
portfolio_coordination.py — Coordinated behavior detection
portfolio_change.py      — Portfolio-level change detection
portfolio_engine.py      — Orchestrator (analyze_portfolio)
portfolio_summary.py     — Interpretation layer (FACT/DERIVED_METRIC/RULE_TRIGGER)
```

## Metrics

| Metric | Formula |
|--------|---------|
| Gross Exposure | Σ \|position_value_usd\| |
| Net Exposure | Long Σ - Short Σ |
| Long/Short Ratio | Long Σ / Short Σ (inf if short=0, None if both 0) |
| Top-N Concentration | Σ Top N values / Gross |
| HHI | Σ (value_i / Gross)² |
| Weighted Leverage | Σ (value × leverage) / Σ value |
| Weighted Liq Distance | Σ (value × liq_dist_pct) / Σ value |
| Liq Cluster 2%/5% | Count + value of positions within 2%/5% of liq |

## Risk Rules (PR1-PR12)

| Rule | Threshold | Severity |
|------|-----------|----------|
| PR1: High Gross Exposure | > $10M | medium |
| PR2: Net Direction Concentration | > 80% in one direction | high |
| PR3: Single Coin Concentration | > 50% in one coin | high |
| PR4: Single Address Concentration | > 70% in one address | medium |
| PR5: High Weighted Leverage | > 10x | high |
| PR6: Liquidation Cluster 2% | 2+ positions within 2% | critical |
| PR7: Liquidation Cluster 5% | 2+ positions within 5% | high |
| PR8: Cross-Whale Same Direction | 2+ whales same coin/direction | info |
| PR9: Cross-Whale Direction Flip | 2+ whales flip same coin | info |
| PR10: Rapid Exposure Expansion | > 20% gross expansion | medium |
| PR11: Data Stale | > 48h old data | low |
| PR12: Data Incomplete | Missing mark/liq prices | low |

## Coordinated Behavior

Detects time-correlated on-chain patterns WITHOUT claiming collusion:

- **Coordinated Build**: 2+ addresses increasing same coin/direction in <6h
- **Coordinated Reduction**: 2+ addresses reducing same coin/direction in <6h  
- **Coordinated Flip**: 2+ addresses flipping same coin in <6h
- **Divergent Behavior**: Opposing directions on same coin in <6h
- **Liquidation Cluster**: 2+ addresses within 5% of liquidation

## Interpretation Output Types

- `[FACT]` — Directly observed data point
- `[DERIVED_METRIC]` — Computed from facts
- `[RULE_TRIGGER]` — Risk rule threshold exceeded
- `[INTERPRETATION_LIMIT]` — Known constraint or caveat

## Corpus V2

100+ deterministic cases covering portfolio structure, metrics, risk rules,
coordinated behavior, changes, entities, and edge cases.

## Sequence

1. Build portfolio intelligence modules
2. 85 new deterministic tests
3. 127 original W2 tests preserved
4. Documentation
5. Commit → Push → Verify
