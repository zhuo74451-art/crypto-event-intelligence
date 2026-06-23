"""Core CPI strategy — core inflation transmission to BTC (Fed-preferred inflation measure)."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_core_cpi",
        strategy_version="1.0.0",
        strategy_family="us_core_cpi",
        strategy_name="US Core CPI Strategy",
        supported_event_families=["us_core_cpi"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["actual_initial_core", "consensus_core_value", "prior_core_value", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["inflation_trend_3m", "services_inflation_trend"],
        required_confirmation_fields=["yield_2y_change", "yield_10y_change", "dollar_index_change", "nasdaq_change"],
        valid_regimes=["inflation_dominant", "liquidity_dominant"],
        invalid_regimes=["risk_off_stress", "growth_dominant"],
        trigger_rules={
            "core_surprise_available": "actual_initial_core and consensus_core_value are both present",
            "core_surprise_significant": "abs(actual_initial_core - consensus_core_value) / consensus_std > 0.2",
        },
        confirmation_rules={
            "yield_curve_response": "2y yield rises on core upside surprise, falls on downside",
            "dollar_response": "DXY confirms yield direction",
            "nasdaq_response": "NASDAQ falls on core upside surprise (rate-sensitive)",
            "btc_correlation": "BTC moves with NASDAQ direction on core surprise",
        },
        invalidation_rules={
            "bond_market_ignores": "yields unchanged despite significant core surprise",
            "dollar_contradicts": "dollar moves opposite to yield direction",
            "subsequent_revision_reverses": "revised core CPI reverses initial surprise sign",
        },
        expiration_rules={
            "intraday_expiry": "1 hour after release",
            "short_term_expiry": "24 hours after release",
            "medium_term_expiry": "5 days after release",
        },
        abstention_rules=[
            "core_consensus_missing",
            "core_initial_unverifiable",
            "headline_and_core_conflict",
            "point_in_time_grade_low",
        ],
        transmission_paths=[
            "core_cpi_surprise -> fed_rate_path -> yield_2y -> dollar -> risk_assets -> btc",
            "core_cpi_surprise -> real_rates -> growth_expectations -> equity_valuation -> btc",
        ],
        alternative_explanations=[
            "core_cpi_less_volatile_than_headline_market_may_discount",
            "fed_forward_guidance_already_accounted_for_sticky_core",
            "market_focus_on_supercore_or_services_inflation_instead",
        ],
        known_failure_modes=[
            "btc_mines_different_signal_from_core_vs_headline_divergence",
            "monthly_core_noise_masks_trend_during_regime_transition",
            "simultaneous_fomc_event_distorts_core_cpi_reaction",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
