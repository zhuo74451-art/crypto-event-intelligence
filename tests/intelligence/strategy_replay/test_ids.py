"""Test deterministic ID generation and ordering independence."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.contracts import deterministic_id


def test_id_order_independence():
    id_ab = deterministic_id("test", ["a", "b", "c"])
    id_cb = deterministic_id("test", ["c", "b", "a"])
    id_ba = deterministic_id("test", ["b", "a", "c"])
    assert id_ab == id_cb == id_ba, f"IDs differ: {id_ab} vs {id_cb} vs {id_ba}"
    print(f"  OK: Order independence")


def test_id_different_inputs():
    id1 = deterministic_id("test", ["event_1", "strat_a"])
    id2 = deterministic_id("test", ["event_1", "strat_b"])
    assert id1 != id2, "Different inputs must produce different IDs"
    print(f"  OK: Different inputs produce different IDs")


def test_id_prefix():
    id1 = deterministic_id("hyp", ["a", "b"])
    id2 = deterministic_id("rr", ["a", "b"])
    assert id1.startswith("hyp_"), f"Wrong prefix: {id1}"
    assert id2.startswith("rr_"), f"Wrong prefix: {id2}"
    print(f"  OK: Correct prefixes")


if __name__ == "__main__":
    test_id_order_independence()
    test_id_different_inputs()
    test_id_prefix()
    print("\nAll ID tests passed!")
