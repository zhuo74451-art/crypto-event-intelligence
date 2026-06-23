"""Test regime classifier deterministic rules."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.regime_classifier import classify_regime


def test_inflation_dominant():
    r = classify_regime(cpi_trend_3m=0.04, yield_2y_trend_1w=0.01)
    assert r.regime == "inflation_dominant", f"Expected inflation_dominant, got {r.regime}"
    print(f"  OK: inflation_dominant")


def test_growth_dominant():
    r = classify_regime(nfp_trend_3m=200000, unemployment_trend_3m=-0.002, yield_2y_trend_1w=0.01)
    assert r.regime == "growth_dominant", f"Expected growth_dominant, got {r.regime}"
    print(f"  OK: growth_dominant")


def test_risk_off():
    r = classify_regime(sp500_trend_1w=-0.05, btc_volatility_1w=0.08)
    assert r.regime == "risk_off_stress", f"Expected risk_off_stress, got {r.regime}"
    print(f"  OK: risk_off_stress")


def test_risk_on():
    r = classify_regime(sp500_trend_1w=0.03, btc_volatility_1w=0.02)
    assert r.regime == "risk_on_expansion", f"Expected risk_on_expansion, got {r.regime}"
    print(f"  OK: risk_on_expansion")


def test_liquidity_dominant():
    r = classify_regime(yield_2y_trend_1w=-0.02, dxy_trend_1w=-0.01)
    assert r.regime == "liquidity_dominant", f"Expected liquidity_dominant, got {r.regime}"
    print(f"  OK: liquidity_dominant")


def test_fallback():
    r = classify_regime()
    assert r.regime == "mixed_uncertain", f"Expected mixed_uncertain, got {r.regime}"
    print(f"  OK: fallback to mixed_uncertain")


if __name__ == "__main__":
    test_inflation_dominant()
    test_growth_dominant()
    test_risk_off()
    test_risk_on()
    test_liquidity_dominant()
    test_fallback()
    print("\nAll regime classifier tests passed!")
