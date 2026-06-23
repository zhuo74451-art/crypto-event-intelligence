"""Test abstention system triggers and record completeness."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.abstention import should_abstain, build_abstention_record


def test_abstain_no_consensus():
    skip, reasons = should_abstain(consensus_available=False)
    assert skip, "Should abstain without consensus"
    assert "consensus_missing" in reasons
    print(f"  OK: Abstain without consensus")


def test_abstain_post_event_consensus():
    skip, reasons = should_abstain(consensus_available=True, consensus_before_event=False)
    assert skip, "Should abstain with post-event consensus"
    assert "consensus_after_release" in reasons
    print(f"  OK: Abstain with post-event consensus")


def test_abstain_low_pit_grade():
    skip, reasons = should_abstain(point_in_time_grade="low")
    assert skip, "Should abstain with low PIT grade"
    assert "point_in_time_grade_low" in reasons
    print(f"  OK: Abstain with low PIT grade")


def test_no_abstain_with_all_data():
    skip, reasons = should_abstain(
        consensus_available=True, consensus_before_event=True,
        point_in_time_grade="high", initial_value_verifiable=True,
        event_time_reliable=True, market_window_available=True,
        regime_available=True, transmission_data_complete=True)
    assert not skip, f"Should not abstain with all data, got reasons: {reasons}"
    print(f"  OK: No abstain with complete data")


def test_build_record():
    a = build_abstention_record("e1", "s1", "si1", ["consensus_missing"],
                                 information_cutoff_utc="2024-01-01T00:00:00Z")
    assert a.abstention_id.startswith("abstain_")
    assert len(a.reason_codes) == 1
    print(f"  OK: Build abstention record")


if __name__ == "__main__":
    test_abstain_no_consensus()
    test_abstain_post_event_consensus()
    test_abstain_low_pit_grade()
    test_no_abstain_with_all_data()
    test_build_record()
    print("\nAll abstention tests passed!")
