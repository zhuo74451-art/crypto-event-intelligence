"""Test kernel adapter conversion from Lane C to Kernel contracts."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.contracts import StrategyHypothesisV1, KernelInputPackageV1
from market_radar.intelligence.strategy_replay.kernel_adapter import (
    build_arbitration_context, build_market_hypothesis, compute_kernel_package_id
)


def test_build_arbitration_context():
    h = StrategyHypothesisV1(hypothesis_id="hyp_test", strategy_id="s1",
                              strategy_instance_id="si1", event_id="e1", asset="BTC",
                              time_horizon="intraday", expected_effect="bullish",
                              strategy_state="confirmed", market_confirmation="spot_confirmed",
                              transmission_signature="risk_on", transmission_coherence="coherent")
    ctx = build_arbitration_context(h, strategy_origin_group="us_cpi")
    assert ctx.hypothesis_id == "hyp_test"
    assert ctx.market_confirmation == "spot_confirmed"
    assert ctx.strategy_origin_group == "us_cpi"
    assert ctx.transmission_signature == "risk_on"
    print(f"  OK: Build arbitration context")


def test_build_market_hypothesis():
    h = StrategyHypothesisV1(hypothesis_id="hyp_test", strategy_id="s1",
                              strategy_instance_id="si1", event_id="e1", asset="BTC",
                              time_horizon="intraday", expected_effect="bullish",
                              strategy_state="candidate")
    mh = build_market_hypothesis(h)
    assert mh.hypothesis_id == "hyp_test"
    assert mh.event_id == "e1"
    assert "BTC" in mh.affected_assets
    print(f"  OK: Build market hypothesis")


def test_compute_kernel_package_id():
    kp_id = compute_kernel_package_id("e1", ["s1", "s2"], ["h1", "h2"])
    assert kp_id.startswith("kp_")
    kp_id2 = compute_kernel_package_id("e1", ["s2", "s1"], ["h2", "h1"])
    assert kp_id == kp_id2, "Order independence failed"
    print(f"  OK: Deterministic kernel package ID")


if __name__ == "__main__":
    test_build_arbitration_context()
    test_build_market_hypothesis()
    test_compute_kernel_package_id()
    print("\nAll kernel adapter tests passed!")
