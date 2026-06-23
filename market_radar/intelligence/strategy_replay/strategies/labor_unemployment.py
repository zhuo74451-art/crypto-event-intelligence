"""Unemployment Rate strategy — labor slack transmission to BTC."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_unemployment_rate",
        strategy_version="1.0.0",
        strategy_family="us_unemployment_rate",
        strategy_name="US Unemployment Rate Strategy",
        supported_event_families=["us_unemployment_rate"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["actual_unemployment", "consensus_unemployment", "prior_unemployment", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["growth_trend_3m", "labor_market_tightness"],
        required_confirmation_fields=["yield_2y_change", "dollar_index_change", "sp500_change"],
        valid_regimes=["growth_dominant", "risk_off_stress", "liquidity_dominant", "mixed_uncertain"],
        invalid_regimes=["inflation_dominant"],
        trigger_rules={
            "unemployment_available": "actual_unemployment and consensus_unemployment are both present",
            "unemployment_surprise_detected": "actual_unemployment != consensus_unemployment",
        },
        confirmation_rules={
            "yield_fall_on_rise": "yields fall when unemployment rises (rate cut expectations)",
            "dollar_weakens_on_rise": "DXY weakens on higher unemployment",
            "sp500_positive_on_low_unemployment": "SP500 rises when unemployment below consensus",
            "sp500_negative_on_high_unemployment": "SP500 falls when unemployment above consensus",
        },
        invalidation_rules={
            "yield_does_not_respond": "yields unchanged despite unemployment surprise",
            "labor_force_participation_confounds": "participation rate change explains the move",
            "nfp_and_unemployment_conflict": "NFP and unemployment tell opposite stories",
        },
        expiration_rules={
            "intraday_expiry": "1 hour after release",
            "short_term_expiry": "24 hours after release",
            "medium_term_expiry": "7 days after release",
        },
        abstention_rules=[
            "unemployment_consensus_missing",
            "unemployment_initial_unverifiable",
            "participation_rate_change_larger_than_unemployment_change",
            "household_survey_and_establishment_survey_divergence",
        ],
        transmission_paths=[
            "unemployment_surprise -> rate_cut_expectations -> yield_2y -> dollar -> risk_assets -> btc",
            "unemployment_surprise -> recession_fears -> risk_off -> btc_sold_for_liquidity",
        ],
        alternative_explanations=[
            "unemployment_lagging_indicator_market_may_discount",
            "labor_force_exodus_artificially_lowers_unemployment_rate",
            "part_time_for_economic_reasons_broader_than_u3_headline",
        ],
        known_failure_modes=[
            "btc_treats_low_unemployment_as_rate_hike_risk_not_economic_strength",
            "u3_versus_u6_divergence_confuses_market_reaction",
            "simultaneous_nfp_release_dominates_unemployment_signal",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
