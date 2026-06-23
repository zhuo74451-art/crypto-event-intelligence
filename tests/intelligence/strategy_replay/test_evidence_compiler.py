"""Test evidence compiler supporting/opposing evidence."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.evidence_compiler import compile_evidence


def test_supporting_evidence():
    r = compile_evidence(macro_release={"event_id": "e1", "initial_value": 3.5},
                          macro_consensus={"event_id": "e1", "value": 3.0, "provider": "bloomberg"},
                          surprise_value=0.5)
    assert r["supporting_count"] >= 3
    assert r["verdict"] == "supported"
    print(f"  OK: Supporting evidence compiled ({r['supporting_count']} items)")


def test_opposing_evidence_pit():
    r = compile_evidence(point_in_time_quality="low")
    assert r["opposing_count"] >= 1
    print(f"  OK: Opposing evidence for low PIT quality")


def test_conflicting_evidence():
    r = compile_evidence(macro_release={"event_id": "e1", "initial_value": 3.5},
                          macro_consensus={"event_id": "e1", "value": 3.0, "provider": "bloomberg"},
                          surprise_value=0.5, spot_confirmation={"confirmed": False, "direction": "bearish", "quality": "medium"})
    assert r["verdict"] == "conflicting"
    print(f"  OK: Conflicting evidence detected")


if __name__ == "__main__":
    test_supporting_evidence()
    test_opposing_evidence_pit()
    test_conflicting_evidence()
    print("\nAll evidence compiler tests passed!")
