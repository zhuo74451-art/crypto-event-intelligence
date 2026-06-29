"""Confirmation, contradiction and invalidation engine."""
from typing import Any, Dict, List, Optional
from market_radar.cognition.contracts import ConfirmationState, Verdict, utc_now

def evaluate_price_direction(
    pre_price: Optional[float],
    post_price: Optional[float],
    threshold_pct: float = 1.0,
) -> ConfirmationState:
    state = ConfirmationState(dimension="price_direction")
    if pre_price is None or post_price is None or pre_price == 0:
        state.verdict = Verdict.UNAVAILABLE.value
        state.limitations.append("price_data_unavailable")
        return state
    change_pct = ((post_price - pre_price) / abs(pre_price)) * 100.0
    state.measured_value = change_pct
    state.threshold = threshold_pct
    if abs(change_pct) < threshold_pct:
        state.verdict = Verdict.NEUTRAL.value
        state.reason_code = "change_below_threshold"
    elif change_pct > 0:
        state.verdict = Verdict.SUPPORTS.value
        state.reason_code = "positive_direction"
    else:
        state.verdict = Verdict.CONTRADICTS.value
        state.reason_code = "negative_direction"
    return state

def evaluate_volume_expansion(
    volume: Optional[float],
    baseline_volume: Optional[float],
    expansion_threshold: float = 1.5,
) -> ConfirmationState:
    state = ConfirmationState(dimension="volume_expansion")
    if volume is None or baseline_volume is None or baseline_volume == 0:
        state.verdict = Verdict.UNAVAILABLE.value
        state.limitations.append("volume_data_unavailable")
        return state
    ratio = volume / baseline_volume
    state.measured_value = ratio
    state.threshold = expansion_threshold
    if ratio >= expansion_threshold:
        state.verdict = Verdict.SUPPORTS.value
        state.reason_code = "volume_expansion_above_threshold"
    else:
        state.verdict = Verdict.NEUTRAL.value
        state.reason_code = "volume_normal"
    return state
