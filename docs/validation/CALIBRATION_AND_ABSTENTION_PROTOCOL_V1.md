# Calibration and Abstention Protocol V1

## What Is Calibrated Probability?

A probability is calibrated if events predicted with probability `p%` occur approximately `p%` of the time. For example, if a model predicts "70% chance of up," then roughly 70 of 100 such predictions should result in an upward move.

## Why Subjective Confidence Is Not Probability

Human (or LLM) confidence assessments are not inherently calibrated. A statement like "I'm 80% confident" does not mean events with that label occur 80% of the time. Calibration is an empirical property that must be measured and corrected.

## Calibration Set

Calibration must be fit on a **dedicated calibration set** that is:
- Separate from the training set
- Separate from the test/holdout set
- Large enough for reliable binning (minimum 10 samples recommended)

## Supported Methods

| Method | Description |
|--------|-------------|
| NoCalibration | Scores used as-is (not valid probabilities) |
| HistogramBinning | Divide scores into bins, map to empirical frequencies |
| PlattScaling | Logistic regression on scores |
| IsotonicRegression | Monotonic non-parametric mapping |

## Calibration Artifact

Every calibration must produce a saved artifact containing:
- Method, model, dataset identifiers
- Fit period and sample size
- Metrics before and after calibration
- Artifact fingerprint (bound to model, data, and features)

**Without an artifact, scores default to `uncalibrated_score` and cannot be presented as probabilities.**

## Abstention / Selective Prediction

Abstention allows the model to say "I don't know" when evidence is insufficient. This is evaluated through:

### Key Metrics
- **Coverage:** Fraction of predictions where the model did not abstain
- **Abstention Rate:** Fraction of cases where the model abstained
- **Selective Accuracy:** Accuracy on non-abstained predictions only
- **Risk-Coverage Curve:** Error rate vs. coverage trade-off

### Rules
1. Abstention thresholds **must** be chosen on the validation set, not the holdout.
2. 100% abstention **is not** a successful strategy — coverage must be reported.
3. Selective accuracy **must** be compared against the never-abstain baseline.
4. All coverage levels **must** be reported, not just the best one.
