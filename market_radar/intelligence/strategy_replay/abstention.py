"""Abstention system — first-class abstention records for insufficient evidence."""
from __future__ import annotations
from typing import Optional
from .contracts import AbstentionRecordV1, deterministic_id

REASON_CATEGORIES = {
    "consensus_missing": "Consensus estimate not available before event",
    "consensus_after_release": "Consensus published after event release time",
    "point_in_time_grade_low": "Point-in-time data quality grade is low or unusable",
    "initial_value_unverifiable": "Initial release value cannot be confirmed",
    "event_time_unreliable": "Event release timestamp cannot be verified",
    "market_window_insufficient": "Market window coverage insufficient",
    "traditional_market_closed": "Traditional markets closed, cross-asset unavailable",
    "regime_missing": "Regime classification cannot be determined",
    "transmission_path_missing": "Key transmission path data missing",
    "transmission_path_conflict": "Transmission path signals are conflicting",
    "derivatives_only": "Only derivatives confirmation available",
    "provider_source_inconsistent": "Key provider sources are inconsistent",
}


def should_abstain(
    consensus_available: bool = False,
    consensus_before_event: bool = True,
    point_in_time_grade: str = "medium",
    initial_value_verifiable: bool = True,
    event_time_reliable: bool = True,
    market_window_available: bool = True,
    traditional_markets_open: bool = True,
    regime_available: bool = True,
    transmission_data_complete: bool = True,
    transmission_path_coherent: bool = True,
    has_spot_confirmation: bool = False,
    has_cross_asset_confirmation: bool = False,
    has_derivatives_only: bool = False,
) -> tuple[bool, list[str]]:
    """Determine if replay should abstain."""
    reasons = []
    if not consensus_available: reasons.append("consensus_missing")
    if not consensus_before_event: reasons.append("consensus_after_release")
    if point_in_time_grade in ("low", "unusable"): reasons.append("point_in_time_grade_low")
    if not initial_value_verifiable: reasons.append("initial_value_unverifiable")
    if not event_time_reliable: reasons.append("event_time_unreliable")
    if not market_window_available: reasons.append("market_window_insufficient")
    if not traditional_markets_open and not has_spot_confirmation: reasons.append("traditional_market_closed")
    if not regime_available: reasons.append("regime_missing")
    if not transmission_data_complete: reasons.append("transmission_path_missing")
    if not transmission_path_coherent: reasons.append("transmission_path_conflict")
    if has_derivatives_only and not has_spot_confirmation and not has_cross_asset_confirmation: reasons.append("derivatives_only")
    return (len(reasons) > 0, reasons)


def build_abstention_record(
    event_id: str, strategy_id: str, strategy_instance_id: str,
    reason_codes: list[str],
    missing_inputs: Optional[list[str]] = None,
    point_in_time_quality: str = "",
    information_cutoff_utc: str = "",
) -> AbstentionRecordV1:
    """Build a structured abstention record."""
    abstention_id = deterministic_id("abstain", [event_id, strategy_instance_id] + reason_codes)
    return AbstentionRecordV1(
        abstention_id=abstention_id, event_id=event_id,
        strategy_id=strategy_id, strategy_instance_id=strategy_instance_id,
        reason_codes=reason_codes, missing_inputs=missing_inputs or [],
        point_in_time_quality=point_in_time_quality,
        information_cutoff_utc=information_cutoff_utc,
    )
