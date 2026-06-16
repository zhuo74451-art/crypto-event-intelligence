# Protocol 06: Sample Pre-registration and Partitions

**对应决策: 6**

## Partitions

| Partition | Usage |
|-----------|-------|
| Development | Week 1 five samples. Permanent members. NOT counted in Pilot statistics. |
| Calibration | Used for protocol refinement before holdout evaluation. |
| Holdout | Prospective evaluation set. Not examined until protocol is frozen. |

## Pre-registration

All Pilot-eligible Research Units MUST have a pre-registered Registration Record before Outcome data is computed or revealed. Registration includes:

- Research unit and candidate references
- Target asset and benchmark
- Selected clock and t0
- Primary window
- Pre-event movement check
- Sensitivity benchmarks
- Data partition assignment
- Git commit and file SHA timestamp

## Prohibition

Development Set observations MUST NOT be counted in Pilot accuracy, success rate, or any aggregate Pilot statistic.
