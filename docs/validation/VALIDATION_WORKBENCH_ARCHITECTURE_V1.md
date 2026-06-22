# Validation Workbench Architecture V1

## Overview

The Historical Validation & Calibration Workbench is a framework for rigorously evaluating market predictions and strategies against historical data — ensuring Point-in-Time correctness, statistical validity, and transparency.

## Design Principles

1. **Point-in-Time First:** Every data element tracks when it was available to the model. Future information is strictly excluded.
2. **Immutable Datasets:** Once built, datasets have stable fingerprints. Modifications create new versions.
3. **Separation of Concerns:** Data integrity, prediction quality, calibration quality, and economic interpretation are evaluated separately.
4. **Explicit Baselines:** All strategies must be compared against predefined baselines before any effectiveness claim.
5. **Transparent Experimentation:** Every experiment has a frozen specification, a registered lifecycle, and preserved results (including failures).

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│                 Experiment Layer                  │
│  Registry │ Runner │ Specification │ Artifacts   │
├─────────────────────────────────────────────────┤
│               Evaluation Layer                   │
│  Bootstrap │ Multiple Testing │ Regime │ Robust │
├─────────────────────────────────────────────────┤
│           Calibration & Abstention Layer          │
│  Protocols │ Artifacts │ Selective Prediction    │
├─────────────────────────────────────────────────┤
│             Baseline & Metrics Layer              │
│  10 Baselines │ Classification │ Probabilistic   │
├─────────────────────────────────────────────────┤
│              Split & Walk-Forward Layer           │
│  Chronological │ Purged │ Expanding │ Rolling    │
├─────────────────────────────────────────────────┤
│              Labels & Dataset Layer               │
│  Return │ Direction │ Volatility │ Drawdown      │
├─────────────────────────────────────────────────┤
│           Point-in-Time Infrastructure            │
│  Availability Ledger │ Revision Guard │ Leakage  │
├─────────────────────────────────────────────────┤
│               Contract Layer                      │
│  Common │ Dataset │ Event │ Label │ Split │ ...  │
└─────────────────────────────────────────────────┘
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `contracts/` | Immutable data classes and enums for all validation objects |
| `point_in_time/` | Availability tracking, revision guards, leakage detectors |
| `datasets/` | Immutable dataset builder with fingerprinting |
| `labels/` | Return, direction, volatility, and event outcome label builders |
| `splits/` | Chronological, rolling, expanding, purged, and walk-forward splits |
| `baselines/` | 10 deterministic baselines for comparison |
| `metrics/` | Classification, probabilistic, calibration, and abstention metrics |
| `calibration/` | Score-to-probability calibration protocols |
| `evaluation/` | Bootstrap, multiple testing, robustness, regime slicing |
| `experiments/` | Registry, runners, reproducibility manifests |

## File Ownership

All code lives under:
- `market_radar/validation/` — Python modules
- `schemas/validation/v1/` — JSON schemas
- `tests/validation/` — Test suite (229+ tests)
- `scripts/validation/` — Utility scripts
- `experiments/validation/` — Experiment artifacts
- `fixtures/validation/` — Test fixtures
- `docs/validation/` — Documentation
