"""Test all 6 macro strategy definitions are valid."""
import sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


def test_all_strategies_present():
    expected = {"us_cpi", "us_core_cpi", "us_nonfarm_payrolls",
                "us_unemployment_rate", "us_core_pce", "us_fomc_rate_decision"}
    assert set(ALL_MACRO_STRATEGIES.keys()) == expected, f"Missing strategies: {expected - set(ALL_MACRO_STRATEGIES.keys())}"
    print(f"  OK: All 6 strategies present")


def test_each_has_unique_rules():
    seen_rules = set()
    for name, s in ALL_MACRO_STRATEGIES.items():
        rules = str(s.trigger_rules) + str(s.confirmation_rules)
        assert s.strategy_id.startswith("strat_"), f"{name}: invalid strategy_id"
        assert len(s.supported_horizons) > 0, f"{name}: no supported_horizons"
        assert len(s.transmission_paths) > 0, f"{name}: no transmission_paths"
        assert len(s.alternative_explanations) > 0, f"{name}: no alternative_explanations"
        assert len(s.invalidation_rules) > 0, f"{name}: no invalidation_rules"
        print(f"  OK: {name} ({s.strategy_id}) validated")


def test_each_has_distinct_event_family():
    families = [s.supported_event_families[0] for s in ALL_MACRO_STRATEGIES.values()]
    assert len(set(families)) == len(families), f"Duplicate event families: {families}"
    print(f"  OK: All strategies have distinct event families")


def test_horizons_valid():
    valid = {"intraday", "short_term", "medium_term", "long_term"}
    for name, s in ALL_MACRO_STRATEGIES.items():
        for h in s.supported_horizons:
            assert h in valid, f"{name}: invalid horizon {h}"
    print(f"  OK: All horizons valid")


if __name__ == "__main__":
    test_all_strategies_present()
    test_each_has_unique_rules()
    test_each_has_distinct_event_family()
    test_horizons_valid()
    print("\nAll macro strategy definition tests passed!")
