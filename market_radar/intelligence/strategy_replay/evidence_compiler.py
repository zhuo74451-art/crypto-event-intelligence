"""Evidence compiler — compiles supporting and opposing evidence for hypotheses."""
from __future__ import annotations
from typing import Any, Optional


def compile_evidence(
    macro_release: Optional[dict] = None,
    macro_consensus: Optional[dict] = None,
    surprise_value: Optional[float] = None,
    regime_result: Optional[dict] = None,
    spot_confirmation: Optional[dict] = None,
    cross_asset_confirmation: Optional[dict] = None,
    derivatives_confirmation: Optional[dict] = None,
    revision_context: Optional[dict] = None,
    point_in_time_quality: str = "medium",
) -> dict[str, Any]:
    """Compile supporting and opposing evidence for a hypothesis."""
    supporting = []
    opposing = []

    if macro_release:
        supporting.append({"type": "macro_release", "event_id": macro_release.get("event_id", ""),
                           "quality": "high" if macro_release.get("initial_value") else "medium"})
    if macro_consensus:
        supporting.append({"type": "consensus", "event_id": macro_consensus.get("event_id", ""),
                           "provider": macro_consensus.get("provider", ""), "quality": "high"})
    if surprise_value is not None:
        supporting.append({"type": "surprise", "value": surprise_value,
                           "quality": "high" if abs(surprise_value) > 0.3 else "medium"})
    if regime_result:
        supporting.append({"type": "regime", "regime": regime_result.get("regime", ""),
                           "rule_id": regime_result.get("rule_id", ""), "quality": regime_result.get("quality", "medium")})
    if spot_confirmation and spot_confirmation.get("confirmed"):
        supporting.append({"type": "spot_reaction", "direction": spot_confirmation["direction"],
                           "magnitude_pct": spot_confirmation["magnitude_pct"], "quality": spot_confirmation["quality"]})
    elif spot_confirmation and not spot_confirmation.get("confirmed"):
        opposing.append({"type": "unconfirmed_spot_reaction", "quality": spot_confirmation.get("quality", "low")})

    if cross_asset_confirmation:
        cl = cross_asset_confirmation.get("confirmation_level", "missing")
        if cl in ("spot_cross_asset_confirmed", "cross_asset_confirmed"):
            supporting.append({"type": "cross_asset", "confirmation_level": cl, "quality": "high"})
        elif cl == "contradicting":
            opposing.append({"type": "conflicting_cross_asset", "quality": "medium"})

    if derivatives_confirmation and derivatives_confirmation.get("derivatives_only"):
        supporting.append({"type": "derivatives", "quality": "low", "note": "derivatives only"})

    if revision_context and revision_context.get("has_revisions", False):
        opposing.append({"type": "revision_uncertainty", "quality": "low"})

    if point_in_time_quality in ("low", "unusable"):
        opposing.append({"type": "weak_point_in_time_quality", "grade": point_in_time_quality, "quality": "low"})

    return {
        "supporting": supporting, "opposing": opposing,
        "supporting_count": len(supporting), "opposing_count": len(opposing),
        "quality": "high" if len(supporting) >= 3 and len(opposing) == 0 else "medium" if len(supporting) >= 2 else "low",
        "verdict": "supported" if len(supporting) >= 2 and len(opposing) == 0 else "conflicting" if len(opposing) > 0 else "insufficient",
    }
