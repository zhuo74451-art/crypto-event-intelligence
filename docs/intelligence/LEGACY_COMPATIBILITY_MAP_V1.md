# Legacy Compatibility Map V1

## Observation → EvidenceItem

| Legacy Field | New Field | Quality |
|-------------|-----------|---------|
| observation_id | evidence_id (prefix evi_legacy_) | derived_map |
| source | source_id | direct_map |
| source_type | source_role | direct_map |
| observed_at | published_at, retrieved_at | direct_map |
| affected_assets | Part of EventEntity.assets | derived_map |
| evidence[].ref | content_hash | lossy_map |
| data_quality | (no direct equivalent) | unsupported |
| normalized_payload.title | claim | lossy_map |

## Signal → StrategyInstance + MarketHypothesis

| Legacy Field | New Field | Quality |
|-------------|-----------|---------|
| signal_id | instance_id/hypothesis_id (prefix sti_legacy_/hyp_legacy_) | derived_map |
| title | causal_thesis | direct_map |
| affected_assets | affected_assets | direct_map |
| direction | expected_effect | lossy_map |
| confidence | ConfidenceStatement (uncalibrated) | lossy_map |
| status | StrategyInstanceState | derived_map |
| evidence[] | current_evidence_refs | direct_map |
| trading_relevance | (no equivalent) | unsupported |
| news_quality | (no equivalent) | unsupported |
| invalidation_reason | supported via lifecycle | direct_map |

## Key Losses

1. Legacy `confidence` has no calibration artifact → cannot be calibrated_probability
2. Legacy `direction` has no structured logic → cannot reconstruct strategy thesis
3. Legacy `trading_relevance` and `news_quality` are unsupported in new model
4. Legacy Signal has no Strategy Pack backing → instance is a structural placeholder
