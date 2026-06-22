"""
Validation Compiler — maps Lane D validation results into the research cognition layer.

Mapping rules (from §21):
  pipeline_verified         → observed
  historical_in_sample_only → insufficient_evidence
  historical_walkforward_mixed → contested
  historical_walkforward_supported → supported (with limitations note)
  holdout_failed            → contradicted or rejected
  insufficient_sample       → insufficient_evidence
  leakage_blocked           → rejected
  calibration_unavailable   → calibration_status: unavailable
"""

from dataclasses import asdict
from typing import List, Optional, Tuple

from market_radar.intelligence.research.contracts import ResearchClaimV1


# Mapping from Lane D validation result labels to claim status
VALIDATION_TO_CLAIM_STATUS = {
    "pipeline_verified": "observed",
    "historical_in_sample_only": "insufficient_evidence",
    "historical_walkforward_mixed": "contested",
    "historical_walkforward_supported": "supported",
    "holdout_failed": "contradicted",
    "leakage_blocked": "rejected",
    "insufficient_sample": "insufficient_evidence",
}

VALIDATION_TO_LIMITATIONS = {
    "historical_in_sample_only": [
        "historical support only",
        "walkforward validation not available",
    ],
    "historical_walkforward_supported": [
        "historical support only",
        "live shadow not available",
    ],
    "holdout_failed": [
        "holdout sample failed",
        "strategy does not generalize to out-of-sample period",
    ],
    "insufficient_sample": [
        "sample size insufficient for reliable conclusion",
    ],
    "leakage_blocked": [
        "future information leakage detected",
        "claim invalidated by PIT violation",
    ],
}


def compile_claim_from_validation(
    validation_result: dict,
    strategy_id: str,
    event_family: str,
    subject: str,
    predicate: str,
    object: str,
    asset: Optional[str] = None,
    time_horizon: Optional[str] = None,
    regime: Optional[str] = None,
) -> ResearchClaimV1:
    """
    Compile a research claim from a Lane D validation result dict.

    Expected validation_result keys:
        - status: str (one of VALIDATION_TO_CLAIM_STATUS keys)
        - strategy_id: str
        - total_events: int
        - walkforward_result: str (optional)
        - holdout_result: str (optional)
        - calibration_status: str (optional)
    """
    status_label = validation_result.get("status", "insufficient_sample")
    claim_status = VALIDATION_TO_CLAIM_STATUS.get(status_label, "insufficient_evidence")
    limitations = VALIDATION_TO_LIMITATIONS.get(status_label, [])

    calibration_status = validation_result.get("calibration_status", "unavailable")

    claim = ResearchClaimV1(
        subject=subject,
        predicate=predicate,
        object=object,
        claim_type="validation_result",
        claim_status=claim_status,
        asset=asset,
        event_family=event_family,
        strategy_id=strategy_id,
        time_horizon=time_horizon,
        regime=regime,
        validation_status=status_label,
        calibration_status=calibration_status,
        limitations=limitations,
        source_lane_refs=["lane_d"],
    )
    return claim


def compile_claims_batch(
    validation_results: List[dict],
    strategy_map: dict,
) -> List[ResearchClaimV1]:
    """
    Batch-compile multiple validation results into research claims.
    strategy_map: {strategy_id: {subject, predicate, object, asset, event_family, ...}}
    """
    claims = []
    for result in validation_results:
        sid = result.get("strategy_id")
        if sid not in strategy_map:
            continue
        base = strategy_map[sid]
        claim = compile_claim_from_validation(
            validation_result=result,
            strategy_id=sid,
            event_family=base.get("event_family", "macro"),
            subject=base.get("subject", "unknown"),
            predicate=base.get("predicate", "associated_with"),
            object=base.get("object", "unknown"),
            asset=base.get("asset"),
            time_horizon=base.get("time_horizon"),
            regime=base.get("regime"),
        )
        claims.append(claim)
    return claims
