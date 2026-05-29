# v0.5 Event Return Statistical Validation

This report tests whether grouped abnormal returns look distinguishable from zero.
It is a research validation step, not a trading signal.

## Method
- Group column: `event_type`
- Metric prefix: `abnormal_vs_btc`
- Minimum sample threshold: `10`
- Bootstrap rounds: `2000`
- Sign-flip permutation rounds: `5000`
- Multiple-testing correction: Bonferroni and Benjamini-Hochberg FDR.

## FDR-Significant Candidates
_No rows._

## Directional Candidates Before FDR
_No rows._

## Small-Sample Buckets
| group_value | window | sample_count | mean | reliability_label |
| --- | --- | --- | --- | --- |
| hack_security | 1h | 8 | 0.001381 | too_small |
| other | 1h | 5 | -0.001623 | too_small |
| halving | 1h | 3 | 0.000000 | too_small |
| institutional_flow | 1h | 3 | 0.000000 | too_small |
| network_upgrade | 1h | 3 | -0.000421 | too_small |
| token_unlock | 1h | 3 | 0.000147 | too_small |
| staking_governance | 1h | 2 | -0.000375 | too_small |
| hack_security | 24h | 8 | -0.002579 | too_small |
| other | 24h | 5 | 0.000348 | too_small |
| halving | 24h | 3 | 0.000000 | too_small |
| institutional_flow | 24h | 3 | 0.000000 | too_small |
| network_upgrade | 24h | 3 | 0.001334 | too_small |
| token_unlock | 24h | 3 | -0.007309 | too_small |
| staking_governance | 24h | 2 | -0.007946 | too_small |
| hack_security | 4h | 8 | 0.004005 | too_small |
| other | 4h | 5 | 0.002348 | too_small |
| halving | 4h | 3 | 0.000000 | too_small |
| institutional_flow | 4h | 3 | 0.000000 | too_small |
| network_upgrade | 4h | 3 | 0.001607 | too_small |
| token_unlock | 4h | 3 | 0.000618 | too_small |
| staking_governance | 4h | 2 | 0.000613 | too_small |
| hack_security | 72h | 8 | -0.002648 | too_small |
| other | 72h | 5 | 0.006548 | too_small |
| halving | 72h | 3 | 0.000000 | too_small |
| institutional_flow | 72h | 3 | 0.000000 | too_small |
| network_upgrade | 72h | 3 | 0.000589 | too_small |
| token_unlock | 72h | 3 | -0.005572 | too_small |
| staking_governance | 72h | 2 | -0.007456 | too_small |

## Interpretation Rules
- Buckets below the minimum sample threshold should not be used as conclusions.
- A positive mean without an interval excluding zero is only descriptive.
- A significant raw p-value that fails FDR should be treated as possible multiple-testing noise.
- Event types such as `other` should be split before drawing any research conclusion.
