# Point-in-Time Validation Protocol V1

## Core Rule

In the specified `as_of_time`, using only information available at that time, determine whether a strategy or market judgment provides a stable information increment over explicit baselines.

## Key Concepts

### As-Known-Then
The model can only use data that was published, first seen, or retrieved before the prediction time. The `available_to_model_at` timestamp is the max of `published_at`, `first_seen_at`, and `retrieved_at`.

### Revision Handling
- Real-time judgments use original release values, not later revisions.
- Post-hoc evaluations may compare original vs. revised values.
- Revised values cannot back-fill into features used at prediction time.

### Vintage Tracking
The system supports four vintage modes:
- `original_release` — First published value
- `first_revision` — First corrected value
- `as_known_then` — Best available at a specific point in time
- `current_best` — Latest available value (for evaluation only, not features)

### Label Maturity
Labels are only observable after their `matures_at` timestamp. Predictions cannot use information from labels that were already observable at prediction time.

### Leakage Detection
The system detects 15+ forms of information leakage:
1. Feature timestamp after prediction time
2. Post-event prices in features
3. Revised values treated as original
4. Mature label state used before maturity
5. Post-hoc event summaries as features
6. Future regime definitions
7. Full-sample statistics computed on future data
8. Target field appearing in feature set
9. Same event cluster across train/test splits
10. Source dependence groups crossing splits
11. Benchmark switched after experiment start
12. Holdout reused for parameter selection
13. Flat threshold changed after seeing results
14. Event window selected post-hoc
15. Exclusion of unfavorable events after seeing results
