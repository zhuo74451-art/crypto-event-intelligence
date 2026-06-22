# Golden Experiments Report V1

## Purpose

Golden experiments verify that the validation framework behaves correctly. They do **not** demonstrate that any strategy is effective for production.

## Experiments

### G1: Always Neutral
- **Purpose:** Verify baseline metrics work with zero-predictive models
- **Expected:** Accuracy = proportion of majority class; all confidence = 0

### G2: Random Prior
- **Purpose:** Verify that random models do not consistently beat baselines
- **Expected:** Variable metrics, no stable out-performance

### G3: Event Type Prior
- **Purpose:** Verify that event-type history provides basic information
- **Expected:** Marginal improvement over random

### G4: Simple Sentiment Rule
- **Purpose:** Verify sentiment-vs-outcome correlation detection
- **Expected:** Weak to moderate correlation

### G5: Momentum Baseline
- **Purpose:** Verify momentum-only signal detection
- **Expected:** Works in trending regimes, fails in mean-reverting

### G6: Funding-only
- **Purpose:** Verify funding rate as standalone predictor
- **Expected:** Weak signal, regime-dependent

### G7: OI-only
- **Purpose:** Verify OI change as standalone predictor
- **Expected:** Weak signal, not independent

### G8: Static Macro Rules
- **Purpose:** Verify macro regime prediction
- **Expected:** Works only when macro state aligns

### G9: Leakage Failure (future price)
- **Purpose:** Verify that leakage detection invalidates the experiment
- **Expected:** `FUTURE_INFORMATION_LEAK` → status `INVALIDATED`

### G10: Holdout Overfitting
- **Purpose:** Verify that holdout-based tuning is rejected
- **Expected:** `HOLDOUT_REUSED_FOR_SELECTION` → experiment rejected

## Status

These golden experiments are placeholders for the framework's behavioral verification. They become executable when a real dataset (synthetic or historical) is connected to the validation pipeline.
