"""Expectation baseline and gap calculation."""
from typing import Optional
from market_radar.cognition.contracts import ExpectationState, ExpectationType

def calculate_gap(
    expected: Optional[float],
    actual: Optional[float],
    range_low: Optional[float] = None,
    range_high: Optional[float] = None,
) -> ExpectationState:
    state = ExpectationState()
    if expected is not None and actual is not None:
        state.expectation_type = ExpectationType.CONSENSUS_VALUE.value
        state.expected_value = expected
        state.actual_reported_value = actual
        state.signed_surprise = actual - expected
        state.absolute_surprise = abs(actual - expected)
        if expected != 0:
            state.surprise_pct = ((actual - expected) / abs(expected)) * 100.0
        state.confidence = "medium"
        if range_low is not None and range_high is not None:
            state.expected_range_low = range_low
            state.expected_range_high = range_high
            if range_low <= actual <= range_high:
                state.signed_surprise = 0.0
                state.absolute_surprise = 0.0
                state.surprise_pct = 0.0
    if state.expectation_type == ExpectationType.UNAVAILABLE.value:
        state.limitations.append("no_defensible_baseline")
    return state

def detect_stale(baseline_timestamp: str, current_time: str, max_age_hours: float = 168.0) -> bool:
    from datetime import datetime, timezone
    try:
        bt = datetime.fromisoformat(baseline_timestamp)
        ct = datetime.fromisoformat(current_time)
        return (ct - bt).total_seconds() > max_age_hours * 3600
    except:
        return True
