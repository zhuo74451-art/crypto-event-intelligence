# Protocol 05: Attribution Assessment

**对应决策: 5**

## Hard Gates

Seven hard gates must ALL be `pass` before `attribution_compatible` or `limited_attribution_support` verdict can be given.

| Gate | Description |
|------|-------------|
| research_eligibility | The Research Unit passed eligibility screening |
| event_evidence | Sufficient evidence exists for the event |
| usable_t0 | A usable t0 can be established |
| pre_outcome_registration | Registration was completed before Outcome reveal |
| valid_outcome_measurement | Outcome measurement is valid |
| benchmark_validity | Benchmark selection is valid |
| separability | The event effect can be separated from interference |

Each gate supports: `pass`, `fail`, `unknown`.

If any gate is not `pass`, the verdict MUST be one of:
- `not_assessable`
- `descriptive_reaction_only`
- `insufficient_evidence`
- `not_supported_in_registered_window`
- `cluster_level_association`

`attribution_compatible` and `limited_attribution_support` are ONLY permitted when ALL seven gates are `pass`.

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
