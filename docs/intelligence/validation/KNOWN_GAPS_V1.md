# Known Gaps V1

1. **Lane C data not yet consumed** - waiting for Lane C integration manifest
2. **No real validation events** - pipeline needs replay results to produce actual metrics
3. **Calibration unavailable** - requires 100+ directional events for empirical binning
4. **JSON schemas are minimal** - need full field-level constraints
5. **Only 30 tests** - target is 25+ test functions, current count: 30
6. **No drift baseline comparison** - PSI thresholds not yet established
7. **No bootstrap cached results** - 1000 resamples require data
