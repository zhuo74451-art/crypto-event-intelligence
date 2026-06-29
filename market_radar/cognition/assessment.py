"""Assessment, calibration and abstention."""
from market_radar.cognition.contracts import Assessment, Abstention, AbstentionCode, sha256_id

def build_assessment(event_id, event_title, lifecycle_state, expectation_gap, market_verdict, confidence_components, transmission_path_ids, evidence_ids):
    oc = sum(confidence_components.values()) / max(len(confidence_components), 1)
    return Assessment(assessment_id=sha256_id(["assessment", event_id]), event_id=event_id, event_summary=event_title[:200], lifecycle_state=lifecycle_state, expectation_gap=expectation_gap, market_confirmation=market_verdict, transmission_paths=transmission_path_ids, confidence_components=confidence_components, overall_confidence=round(oc, 4), supporting_evidence_ids=list(evidence_ids), not_trading_instruction=True)

def should_abstain(expectation_available, market_data_available, unresolved_conflicts, stale):
    if not expectation_available: return Abstention(code=AbstentionCode.EXPECTATION_UNAVAILABLE.value, reason="No defensible expectation baseline")
    if not market_data_available: return Abstention(code=AbstentionCode.MARKET_DATA_UNAVAILABLE.value, reason="Market data unavailable")
    if unresolved_conflicts: return Abstention(code=AbstentionCode.UNRESOLVED_SOURCE_CONFLICT.value, reason="Unresolved source conflicts")
    if stale: return Abstention(code=AbstentionCode.STALE_EVIDENCE.value, reason="Evidence stale")
    return None