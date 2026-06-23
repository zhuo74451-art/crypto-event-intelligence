"""Test replay clock point-in-time enforcement."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.replay_clock import (
    ReplayCutoffs, build_default_cutoffs, is_post_event_consensus,
    is_future_revision, is_future_information
)


def test_cutoffs_ordering():
    c = build_default_cutoffs("2024-01-15T13:30:00Z")
    violations = c.validate_ordering()
    assert len(violations) == 0, f"Ordering violations: {violations}"
    print(f"  OK: Cutoffs properly ordered")


def test_post_event_consensus():
    assert is_post_event_consensus("2024-01-15T14:00:00Z", "2024-01-15T13:30:00Z"), "Consensus after event should be flagged"
    assert not is_post_event_consensus("2024-01-15T12:00:00Z", "2024-01-15T13:30:00Z"), "Consensus before event is OK"
    print(f"  OK: Post-event consensus detection")


def test_future_revision():
    assert is_future_revision("2024-01-16T00:00:00Z", "2024-01-15T13:29:00Z"), "Revision after cutoff should be flagged"
    assert not is_future_revision("2024-01-15T12:00:00Z", "2024-01-15T13:29:00Z"), "Revision before cutoff is OK"
    print(f"  OK: Future revision detection")


def test_future_information():
    assert is_future_information("2024-01-15T14:00:00Z", "2024-01-15T13:29:00Z"), "Info after cutoff should be flagged"
    assert not is_future_information("2024-01-15T12:00:00Z", "2024-01-15T13:29:00Z"), "Info before cutoff is OK"
    print(f"  OK: Future information detection")


def test_data_availability():
    c = build_default_cutoffs("2024-01-15T13:30:00Z")
    assert c.is_data_available("2024-01-15T12:00:00Z"), "Data before event should be available"
    assert not c.is_data_available("2024-01-15T13:31:00Z"), "Data after event should not be available as input"
    print(f"  OK: Data availability check")


if __name__ == "__main__":
    test_cutoffs_ordering()
    test_post_event_consensus()
    test_future_revision()
    test_future_information()
    test_data_availability()
    print("\nAll replay clock tests passed!")
