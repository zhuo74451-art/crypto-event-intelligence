# VALIDATION INTEGRATION REQUIREMENTS V1

## Per-Prediction Output
- prediction_id, strategy_version, release_event_id
- prediction_as_of_time
- event_cluster_id, source_dependence_group
- proposal (with direction, horizons, abstention reason)
- label_specification for verification

## Constraints
- No future data in prediction_as_of_time
- Revision creates new prediction, doesn't overwrite
- Baseline comparators provided
