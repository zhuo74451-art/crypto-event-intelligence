"""Forced flow strategy — exploratory. Forced flow strategy"""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_forced_flow",
        strategy_version="1.0.0",
        strategy_family="forced_flow",
        strategy_name="Forced Flow Strategy",
        supported_event_families=["forced_flow"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["event_type", "announcement_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=[],
        required_confirmation_fields=[],
        valid_regimes=["risk_on_expansion", "mixed_uncertain"],
        invalid_regimes=["risk_off_stress"],
        trigger_rules={"event_detected": "event_type is recognized"},
        confirmation_rules={"btc_reaction": "BTC moves in expected direction"},
        invalidation_rules={"no_reaction": "BTC does not move significantly"},
        expiration_rules={
            "intraday_expiry": "2 hours after announcement",
            "short_term_expiry": "48 hours after announcement",
            "medium_term_expiry": "7 days after announcement",
        },
        abstention_rules=["unverifiable_source", "event_time_unreliable"],
        transmission_paths=["event -> market_sentiment -> btc"],
        alternative_explanations=["event_already_priced"],
        known_failure_modes=["market_ignores_event"],
        confidence_representation="exploratory",
        calibration_required_for_probability=True,
    )
