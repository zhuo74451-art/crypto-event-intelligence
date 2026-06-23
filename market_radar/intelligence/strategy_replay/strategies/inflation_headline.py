"""Headline CPI strategy — inflation surprise transmission to BTC."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_cpi",
        strategy_version="1.0.0",
        strategy_family="us_cpi",
        strategy_name="US CPI Headline Strategy",
        supported_event_families=["us_cpi"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["actual_initial", "consensus_value", "prior_value", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["inflation_trend_3m", "yield_2y_trend_1w"],
        required_confirmation_fields=["yield_2y_change", "dollar_index_change", "nasdaq_change"],
        valid_regimes=["inflation_dominant", "liquidity_dominant", "mixed_uncertain"],
        invalid_regimes=["risk_off_stress"],
        trigger_rules={
            "surprise_available": "actual_initial and consensus_value are both present",
            "surprise_significant": "abs(actual_initial - consensus_value) / consensus_std > 0.3",
        },
        confirmation_rules={
            "yield_direction": "2y yield moves in same direction as inflation surprise",
            "dollar_direction": "DXY moves in same direction as inflation surprise",
            "equity_reaction": "NASDAQ moves opposite to inflation surprise (risk-off)",
        },
        invalidation_rules={
            "reverse_yield": "2y yield moves opposite to inflation surprise",
            "data_revision_contradicts": "subsequent revision reverses the initial surprise direction",
            "regime_mismatch": "current regime is risk_off_stress and surprise is positive",
        },
        expiration_rules={
            "intraday_expiry": "1 hour after release",
            "short_term_expiry": "24 hours after release",
            "medium_term_expiry": "7 days after release",
        },
        abstention_rules=[
            "consensus_missing",
            "consensus_after_release",
            "point_in_time_grade_low",
            "initial_value_unverifiable",
            "event_time_unreliable",
        ],
        transmission_paths=[
            "cpi_surprise -> rate_expectations -> yield_2y -> dollar_index -> risk_appetite -> btc",
            "cpi_surprise -> real_rates -> gold -> btc_correlation_trade",
        ],
        alternative_explanations=[
            "inflation_surprise_already_priced_by_forward_market",
            "liquidity_dominant_regime_overrides_inflation_signal",
            "simultaneous_geopolitical_event_confounds_reaction",
        ],
        known_failure_modes=[
            "surprise_direction_correct_but_btc_moves_inversely_due_to_liquidations",
            "nasdaq_and_btc_decouple_during_market_open_anomaly",
            "weekend_release_with_thin_liquidity_distorts_first_reaction",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
