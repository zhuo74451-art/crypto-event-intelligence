"""Nonfarm Payrolls strategy — labor demand transmission to BTC."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_nonfarm_payrolls",
        strategy_version="1.0.0",
        strategy_family="us_nonfarm_payrolls",
        strategy_name="US Nonfarm Payrolls Strategy",
        supported_event_families=["us_nonfarm_payrolls"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["actual_nfp", "consensus_nfp", "prior_nfp", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["growth_trend_3m", "yield_2y_trend_1w"],
        required_confirmation_fields=["yield_2y_change", "yield_10y_change", "dollar_index_change", "sp500_change"],
        valid_regimes=["growth_dominant", "risk_on_expansion", "liquidity_dominant"],
        invalid_regimes=["risk_off_stress"],
        trigger_rules={
            "nfp_available": "actual_nfp and consensus_nfp are both present",
            "nfp_surprise_significant": "abs(actual_nfp - consensus_nfp) > 50000",
        },
        confirmation_rules={
            "yield_rise_on_beat": "2y yield rises on NFP beat (strong economy)",
            "yield_fall_on_miss": "2y yield falls on NFP miss (weak economy)",
            "dollar_confirms": "DXY follows yield direction",
            "sp500_risk_appetite": "SP500 rises on NFP beat, falls on miss",
        },
        invalidation_rules={
            "dollar_moves_opposite_yield": "DXY disconnects from yield signal",
            "sp500_and_yield_conflict": "SP500 rises but yields fall (growth scare not priced)",
            "prior_month_revision_reverses": "large prior revision changes the labor picture",
        },
        expiration_rules={
            "intraday_expiry": "1 hour after release",
            "short_term_expiry": "24 hours after release",
            "medium_term_expiry": "7 days after release",
        },
        abstention_rules=[
            "nfp_consensus_missing",
            "nfp_initial_unverifiable",
            "prior_month_revision_exceeds_current_surprise",
            "holiday_or_weather_distortion_suspected",
        ],
        transmission_paths=[
            "nfp_surprise -> growth_expectations -> yield_2y -> dollar -> sp500 -> btc",
            "nfp_surprise -> labor_market_tightness -> wage_growth -> inflation_expectations -> fed_path -> btc",
        ],
        alternative_explanations=[
            "payrolls_volatile_month_to_month_market_may_discount_one_print",
            "wage_component_more_important_than_headline_nfp",
            "participation_rate_change_confounds_nfp_interpretation",
        ],
        known_failure_modes=[
            "btc_trades_on_wage_data_instead_of_headline_nfp",
            "government_shutdown_or_weather_distorts_nfp",
            "prior_month_revision_larger_than_current_surprise_flips_narrative",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
