# Existing Validation Asset Audit V1

## Scope

Audit of all existing data, scripts, fixtures, and results relevant to historical validation.

## Assessment Scale

- **POINT_IN_TIME_SAFE** — Suitable for formal validation under strict Point-in-Time rules.
- **USABLE_WITH_RESTRICTIONS** — Useful for exploration or development but has known Point-in-Time limitations.
- **FIXTURE_ONLY** — May be used for testing framework behavior, not for strategy claims.
- **REFERENCE_ONLY** — Historical artifact, no validation use.
- **REJECT_FOR_VALIDATION** — Contains known leakage or data quality issues that preclude validation use.

---

## Asset Inventory

### 1. Week 1 Data (`data/`, `research/`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Week 1 raw research dataset | `REFERENCE_ONLY` | Five-sample proof-of-concept; no Point-in-Time guarantees, no revision tracking, no source manifests |
| Week 1 price providers | `REFERENCE_ONLY` | Historical research scripts, no reproducible pipeline |
| week1_price_providers test | `FIXTURE_ONLY` | Tests price-provider adapters, not validation logic |

### 2. Historical Event Data (`market_radar/intelligence_feed/`, `data/`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Event intelligence clustering | `REJECT_FOR_VALIDATION` | Probabilistic dedup not suitable for verification; no identity tracking |
| Narrative dedup output | `REJECT_FOR_VALIDATION` | Uses full corpus for dedup — future leak risk |
| Historical event CSV/SQLite | `USABLE_WITH_RESTRICTIONS` | May contain useful timestamps but has no revision/vintage metadata |

### 3. Price Backfill (`market_radar/shared/event_price_backfill.py`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| `event_price_backfill.py` | `FIXTURE_ONLY` | Helper for fixture construction; uses latest-available price, not Point-in-Time |
| Price backfill tests | `FIXTURE_ONLY` | Test adapter behavior, not validation logic |

### 4. Abnormal Return Calculations

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Existing abnormal return computations | `REJECT_FOR_VALIDATION` | No consistent benchmark selection, no Point-in-Time benchmark prices |

### 5. Benchmark Definitions

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Hardcoded benchmark references | `REJECT_FOR_VALIDATION` | Not frozen per experiment, not Point-in-Time |

### 6. Event Time Handling

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Event time extraction | `USABLE_WITH_RESTRICTIONS` | Exists but lacks `published_at` vs `effective_at` distinction |
| Broadcast time tracking | `USABLE_WITH_RESTRICTIONS` | Partial; no formal `first_seen_at` or `available_to_model_at` |

### 7. Revision Data

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Revision tracking | `REJECT_FOR_VALIDATION` | No revision guard implementation; cannot distinguish original vs revised values |

### 8. Data Maturity

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Label/event maturity mechanism | `REJECT_FOR_VALIDATION` | Does not exist — full `immature/mature/disputed` lifecycle needs building |

### 9. Label Definitions

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Existing event outcome labels | `REJECT_FOR_VALIDATION` | No separation between input and label, no maturity concept, no Flat/unknown states |

### 10. Event Deduplication

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Dedup in intelligence_feed | `REJECT_FOR_VALIDATION` | Probabilistic, not identity-based; no `event_cluster_id` or `source_dependence_group` |

### 11. Multi-Source Deduplication

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Multi-source handling | `REJECT_FOR_VALIDATION` | No independence tracking; same upstream story across 10 sites would count as 10 samples |

### 12. Future Data Risk

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| All existing event datasets | `REJECT_FOR_VALIDATION` | No Point-in-Time guard; cannot guarantee features don't use future data |

### 13. Market Regime Fields

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Regime classification | `REJECT_FOR_VALIDATION` | May use future data for regime computation; no forward-looking regime guard |

### 14. Existing Backtest Scripts (`scripts/`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Run scripts v110-v119 | `REFERENCE_ONLY` | Historical run artifacts, not reproducible validation |
| Validation/audit scripts | `FIXTURE_ONLY` | May contain useful scaffolding patterns |

### 15. Existing Test Fixtures (`fixtures/`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| Shared test fixtures | `FIXTURE_ONLY` | Good for testing pipeline behavior, not for strategy claims |

### 16. QA Framework (`qa/`)

| Asset | Classification | Rationale |
|-------|---------------|-----------|
| QA scanners | `FIXTURE_ONLY` | Read-only scanners useful for validation gating but not validation datasets |

---

## Summary

| Classification | Count |
|---------------|-------|
| POINT_IN_TIME_SAFE | 0 |
| USABLE_WITH_RESTRICTIONS | 2 |
| FIXTURE_ONLY | 5 |
| REFERENCE_ONLY | 3 |
| REJECT_FOR_VALIDATION | 10 |

## Conclusion

No existing asset qualifies as `POINT_IN_TIME_SAFE`. The validation workbench must build a completely new Point-in-Time data pipeline. Existing assets are useful only as:
- Development fixtures (for testing the workbench itself)
- Reference implementations (to understand what not to do)
- Price adapter integration (for fetching test data)
