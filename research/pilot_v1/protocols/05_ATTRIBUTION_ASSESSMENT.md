# Protocol 05: Attribution Assessment

**对应决策: 5**

## Eight Dimensions

| Dimension | Evaluates |
|-----------|-----------|
| temporal_ordering | Did the event precede the price move? |
| temporal_proximity | How close in time were event and reaction? |
| benchmark_relative_materiality | Was the move significant vs benchmark? |
| asset_specificity | Did only the expected asset move? |
| mechanism_consistency | Is there a plausible causal mechanism? |
| interference_and_separability | Can effects be separated from other events? |
| alternative_explanations | How many alternative explanations exist? |
| robustness | Does the result hold under sensitivity checks? |

Each dimension value: `supports`, `weakens`, `unknown`, `not_applicable`.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| not_assessable | Cannot assess due to data gaps |
| descriptive_reaction_only | Price moved, but no assignment possible |
| insufficient_evidence | Evidence too weak for any conclusion |
| attribution_compatible | Attribution is possible but not confirmed |
| limited_attribution_support | Some evidence supports, but significant uncertainty |
| not_supported_in_registered_window | The registered window does not support attribution |
| cluster_level_association | Association only at cluster level |

**Single-case verdict MUST NOT exceed `limited_attribution_support`.**

## Prohibitions

- No numeric attribution scores
- No confidence probabilities
- No contribution percentages
- No win rates
- No buy/sell/long/short/action recommendations
