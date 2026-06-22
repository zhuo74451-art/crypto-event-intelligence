# Contract Reference V1

## SchemaVersion

Fields: major (int), minor (int), patch (int)
Invariants: is_compatible_with checks major equality and minor >= consumer.minor

## DataAvailability

Status: available | missing | conflicting | stale | not_applicable | unsupported
Each status provides a factory method and explicit reason.

## IntelligenceID

Prefix-based IDs with deterministic hash generation.
Prefixes: src_, evi_, evt_, trn_, reg_, str_, sti_, hyp_, arb_, asm_, cal_

## EvidenceItem

Fields: evidence_id, claim, source_id, source_role, independence_group, 5 timestamps, is_primary, verification_status, retraction_status

## EvidenceBundle

Fields: bundle_id, items[], status (BundleStatus), bundle_verdict (VerificationStatus)

## EventEntity

Fields: event_id, event_family, title, entities[], assets[], current_state, previous_state, state_version, parent_event_id, revision_of, reversal_of

## EventTransition

Fields: transition_id, event_id, from_state, to_state, transition_type, transition_time, first_seen_at, evidence_refs[]

## RegimeDimension

Fields: dimension (RegimeDimensionType), probabilities (dict[str, float]), pre_normalization, is_normalized
Validates: all probs in [0,1], sum ~1.0 when normalized

## RegimeSnapshot

Fields: regime_id, as_of_time, dimensions (dict[str, RegimeDimension]), source_refs[]

## StrategyPack

Fields: strategy_id, name, version, origin, thesis, logic (4 directions), invalidation_conditions, etc.
Invariants: Must have abstention_logic and invalidation_conditions

## StrategyInstance

Fields: instance_id, strategy_id, asset, time_horizon, state (StrategyInstanceState), transitions[]

## MarketHypothesis

Fields: hypothesis_id, event_id, strategy_instance_id, affected_assets[], causal_thesis, supporting_evidence[], contradicting_evidence[], expected_effect, alternative_explanations[], invalidation_conditions[], status, confidence_statement

## ConfidenceStatement

Types: qualitative, uncalibrated_score, empirical_interval, calibrated_probability
Invariants: calibrated requires CalibrationArtifactRef; uncalibrated requires production_probability=False

## MarketAssessment

Fields: assessment_id, event, evidence_state, event_state, regime_state, expectation_gap, transmission_summary, horizon_assessments[], overall_status, action_guidance, limitations[]
