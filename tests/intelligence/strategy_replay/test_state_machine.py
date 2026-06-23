"""Test state machine transitions and terminal states."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.state_machine import (
    compute_next_state, can_transition, is_terminal, validate_transition_sequence
)


def test_candidate_to_triggered():
    s = compute_next_state("candidate", has_surprise=True, has_macro_inputs=True)
    assert s == "triggered", f"Expected triggered, got {s}"
    print(f"  OK: candidate -> triggered")


def test_candidate_insufficient():
    s = compute_next_state("candidate", missing_critical_inputs=True)
    assert s == "insufficient_evidence", f"Expected insufficient_evidence, got {s}"
    print(f"  OK: candidate -> insufficient_evidence")


def test_triggered_to_confirmed():
    s = compute_next_state("triggered", has_surprise=True, has_macro_inputs=True,
                            has_market_data=True, has_cross_asset_confirmation=True)
    assert s == "confirmed", f"Expected confirmed, got {s}"
    print(f"  OK: triggered -> confirmed")


def test_triggered_to_awaiting():
    s = compute_next_state("triggered", has_surprise=True, has_macro_inputs=True,
                            has_market_data=True, has_cross_asset_confirmation=False)
    assert s == "awaiting_confirmation", f"Expected awaiting_confirmation, got {s}"
    print(f"  OK: triggered -> awaiting_confirmation")


def test_invalidated_terminal():
    s = compute_next_state("confirmed", has_contradiction=True)
    assert s == "invalidated", f"Expected invalidated, got {s}"
    assert is_terminal("invalidated"), "invalidated should be terminal"
    print(f"  OK: confirmed -> invalidated (terminal)")


def test_expired_terminal():
    s = compute_next_state("candidate", is_expired=True)
    assert s == "expired", f"Expected expired, got {s}"
    assert is_terminal("expired"), "expired should be terminal"
    print(f"  OK: expired is terminal")


def test_cycle_candidate():
    s = compute_next_state("candidate")
    assert s == "candidate", f"Should stay candidate when no inputs, got {s}"
    print(f"  OK: candidate stays candidate without inputs")


def test_transition_invalid():
    assert not can_transition("candidate", "supported"), "candidate->supported should be invalid"
    assert not can_transition("expired", "candidate"), "expired->candidate should be invalid"
    print(f"  OK: Invalid transitions rejected")


if __name__ == "__main__":
    test_candidate_to_triggered()
    test_candidate_insufficient()
    test_triggered_to_confirmed()
    test_triggered_to_awaiting()
    test_invalidated_terminal()
    test_expired_terminal()
    test_cycle_candidate()
    test_transition_invalid()
    print("\nAll state machine tests passed!")
