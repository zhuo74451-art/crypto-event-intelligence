"""Core PCE strategy — Fed-preferred inflation gauge transmission to BTC."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_core_pce",
        strategy_version="1.0.0",
        strategy_family="us_core_pce",
        strategy_name="US Core PCE Strategy",
        supported_event_families=["us_core_pce"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["actual_core_pce", "consensus_core_pce", "prior_core_pce", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["inflation_trend_3m", "fed_watch_rate_probability"],
        required_confirmation_fields=["yield_2y_change", "yield_10y_change", "dollar_index_change", "nasdaq_change"],
        valid_regimes=["inflation_dominant", "liquidity_dominant", "mixed_uncertain"],
        invalid_regimes=["risk_off_stress"],
        trigger_rules={
            "pce_available": "actual_core_pce and consensus_core_pce are both present",
            "pce_surprise_significant": "abs(actual_core_pce - consensus_core_pce) > 0.1",
        },
        confirmation_rules={
            "yield_sensitivity": "2y yield responds to core PCE surprise (fed path adjustment)",
            "dollar_reaction": "DXY confirms the rate path signal",
            "nasdaq_valuation": "NASDAQ moves inversely to core PCE (duration risk)",
            "btc_as_risk_asset": "BTC follows NASDAQ direction",
        },
        invalidation_rules={
            "fed_already_priced": "fed funds futures show no change despite PCE surprise",
            "personal_income_or_spending_contradicts": "income/spending data tells opposite story",
            "yield_curve_flattens_unexpectedly": "2s10s inverts more on high PCE (recession signal)",
        },
        expiration_rules={
            "intraday_expiry": "1 hour after release",
            "short_term_expiry": "24 hours after release",
            "medium_term_expiry": "5 days after release",
        },
        abstention_rules=[
            "pce_consensus_missing",
            "pce_initial_unverifiable",
            "pce_and_cpi_divergence_exceeds_normal_range",
            "monthly_pce_volatility_high_noise_ratio",
        ],
        transmission_paths=[
            "core_pce_surprise -> fed_policy_path -> yield_2y -> dollar -> risk_assets -> btc",
            "core_pce_surprise -> real_rates -> gold -> btc_as_digital_gold",
        ],
        alternative_explanations=[
            "pce_less_volatile_than_cpi_market_reaction_usually_muted",
            "fed_has_signaled_tolerance_for_above_target_pce",
            "personal_income_data_may_dominate_pce_release_day",
        ],
        known_failure_modes=[
            "pce_published_same_day_as_personal_income_confounds",
            "monthly_pce_revisions_can_change_the_narrative",
            "btc_decouples_from_nasdaq_on_pce_days",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
