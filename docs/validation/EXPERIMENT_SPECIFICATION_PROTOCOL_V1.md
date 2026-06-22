# Experiment Specification Protocol V1

## Freezing Process

Every experiment follows this lifecycle:

```
DRAFT → FROZEN → RUNNING → COMPLETED | FAILED | INVALIDATED
```

### Rules
1. An experiment **must** be registered before any computation.
2. A specification **must** be frozen before execution starts.
3. Once frozen, the specification **must not** be modified.
4. Modifications create a new `experiment_version`.
5. Original experiments **must not** be overwritten.

### Required Fields

| Field | Description |
|-------|-------------|
| `experiment_id` | Unique identifier |
| `experiment_version` | Version string (new version for modified specs) |
| `created_at` | Timestamp of specification creation |
| `research_question` | The question this experiment answers |
| `dataset_id` | Which dataset to use |
| `time_horizons` | Prediction horizons to evaluate |
| `baseline_set` | Baselines to compare against |
| `split_method` | How to partition time series |
| `primary_metrics` | Success criteria metrics |
| `maximum_trials` | Cap on parameter search iterations |
| `seed` | Random seed for reproducibility |

### Multiple Testing Declaration

Each experiment must declare:
- `multiple_testing_family` — What family of comparisons this belongs to
- `number_of_comparisons` — How many independent tests are performed
- `correction_method` — Bonferroni, Holm, or Benjamini-Hochberg

### Prohibited Actions
- Overwriting an existing experiment
- Modifying a frozen specification
- Deleting failed experiments
- Tuning parameters on holdout data
- Switching benchmarks after experiment completion
