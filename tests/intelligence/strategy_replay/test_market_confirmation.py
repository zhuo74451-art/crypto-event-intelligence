"""Test market confirmation module."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.market_confirmation import (
    evaluate_spot_confirmation, evaluate_cross_asset_confirmation, evaluate_derivatives_confirmation
)


def test_spot_confirmation_bullish():
    r = evaluate_spot_confirmation(btc_pre_price=100.0, btc_post_price=102.0, expected_direction="bullish")
    assert r["confirmed"], "Should be confirmed"
    assert r["direction"] == "bullish"
    print(f"  OK: Spot bullish confirmation")


def test_spot_confirmation_missing():
    r = evaluate_spot_confirmation()
    assert not r["confirmed"]
    assert r["quality"] == "missing"
    print(f"  OK: Spot missing data -> not confirmed")


def test_cross_asset_risk_off():
    r = evaluate_cross_asset_confirmation(yield_2y_change=0.01, dxy_change=0.005, sp500_change=-0.01,
                                           expected_risk_direction="risk_off")
    assert r["confirmation_level"] in ("spot_cross_asset_confirmed", "cross_asset_confirmed", "partial")
    print(f"  OK: Cross-asset risk-off confirmation: {r['confirmation_level']}")


def test_derivatives_only():
    r = evaluate_derivatives_confirmation(funding_rate_change=0.001, oi_change_pct=0.05)
    assert r["derivatives_only"]
    print(f"  OK: Derivatives only flag")


if __name__ == "__main__":
    test_spot_confirmation_bullish()
    test_spot_confirmation_missing()
    test_cross_asset_risk_off()
    test_derivatives_only()
    print("\nAll market confirmation tests passed!")
