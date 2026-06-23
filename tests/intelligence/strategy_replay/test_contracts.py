"""Test contracts: IDs, serialization, and schema compliance."""
import json, sys, hashlib
sys.path.insert(0, ".")

from market_radar.intelligence.strategy_replay.contracts import (
    StrategyDefinitionV1, StrategyHypothesisV1, StrategyReplayResultV1,
    AbstentionRecordV1, KernelInputPackageV1, deterministic_id,
    StrategyState, MarketConfirmation,
)


def test_deterministic_id():
    id1 = deterministic_id("strat", ["a", "b"])
    id2 = deterministic_id("strat", ["a", "b"])
    id3 = deterministic_id("strat", ["b", "a"])
    assert id1 == id2, "Same inputs produce same ID"
    assert id2 == id3, "Sorted inputs produce same ID"
    assert id1.startswith("strat_"), "ID has correct prefix"
    print(f"  OK: deterministic_id is deterministic ({id1})")


def test_hypothesis_id_deterministic():
    h1 = StrategyHypothesisV1(
        hypothesis_id=deterministic_id("hyp", ["strat_a", "evt_1", "intraday"]),
        strategy_id="strat_a", event_id="evt_1", time_horizon="intraday")
    h2 = StrategyHypothesisV1(
        hypothesis_id=deterministic_id("hyp", ["strat_a", "evt_1", "intraday"]),
        strategy_id="strat_a", event_id="evt_1", time_horizon="intraday")
    assert h1.hypothesis_id == h2.hypothesis_id
    print(f"  OK: Same hypothesis IDs")


def test_strategy_definition_roundtrip():
    d = StrategyDefinitionV1(strategy_id="strat_test", strategy_family="test",
                              supported_horizons=["intraday", "short_term"])
    dd = d.to_dict()
    assert dd["strategy_id"] == "strat_test"
    d2 = StrategyDefinitionV1.from_dict(dd)
    assert d2.strategy_id == d.strategy_id
    assert d2.supported_horizons == d.supported_horizons
    print(f"  OK: StrategyDefinition roundtrip")


def test_replay_result_required_fields():
    r = StrategyReplayResultV1(
        replay_result_id="rr_test", event_id="e1", strategy_id="s1",
        strategy_instance_id="si1", replay_status="completed",
        strategy_state="triggered", generated_at_utc="2024-01-01T00:00:00Z")
    assert r.replay_result_id == "rr_test"
    assert r.strategy_state == "triggered"
    print(f"  OK: ReplayResult required fields")


def test_abstention_record():
    a = AbstentionRecordV1(
        abstention_id="abs_test", event_id="e1", strategy_id="s1",
        strategy_instance_id="si1", reason_codes=["consensus_missing"],
        information_cutoff_utc="2024-01-01T00:00:00Z")
    assert len(a.reason_codes) == 1
    assert a.reason_codes[0] == "consensus_missing"
    print(f"  OK: AbstentionRecord")


def test_kernel_package():
    kp = KernelInputPackageV1(
        kernel_package_id="kp_test", event_id="e1",
        hypotheses=[{"id": "h1"}],
        hypothesis_contexts={"h1": {"field": "val"}},
        evidence_state={}, regime_state={},
        source_strategy_ids=["s1"],
        information_cutoff_utc="2024-01-01T00:00:00Z",
        contract_versions={"strategy_replay": "1.0.0"})
    assert kp.kernel_package_id == "kp_test"
    assert len(kp.hypotheses) == 1
    print(f"  OK: KernelInputPackage")


if __name__ == "__main__":
    test_deterministic_id()
    test_hypothesis_id_deterministic()
    test_strategy_definition_roundtrip()
    test_replay_result_required_fields()
    test_abstention_record()
    test_kernel_package()
    print("\nAll contract tests passed!")
