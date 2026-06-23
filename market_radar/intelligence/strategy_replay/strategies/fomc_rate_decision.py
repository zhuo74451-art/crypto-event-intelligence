"""FOMC Rate Decision strategy — Fed policy transmission to BTC."""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_us_fomc_rate_decision",
        strategy_version="1.0.0",
        strategy_family="us_fomc_rate_decision",
        strategy_name="FOMC Rate Decision Strategy",
        supported_event_families=["us_fomc_rate_decision"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["intraday", "short_term", "medium_term"],
        required_macro_fields=["rate_decision", "prior_rate", "dots_median", "release_time_utc"],
        required_market_fields=["btc_usdt_price_window_pre", "btc_usdt_price_window_post_1h"],
        required_regime_fields=["fed_watch_rate_probability", "inflation_trend_3m", "growth_trend_3m"],
        required_confirmation_fields=["yield_2y_change", "yield_10y_change", "dollar_index_change", "sp500_change", "nasdaq_change"],
        valid_regimes=["inflation_dominant", "growth_dominant", "liquidity_dominant", "risk_on_expansion", "mixed_uncertain"],
        invalid_regimes=[],
        trigger_rules={
            "decision_available": "rate_decision is present",
            "decision_surprise": "rate_decision differs from fed_watch_implied_rate",
            "dots_change_detected": "dots_median changed from prior SEP",
        },
        confirmation_rules={
            "yield_immediate_reaction": "2y yield moves in direction of rate decision surprise",
            "dollar_confirms": "DXY follows yield direction",
            "equity_risk_appetite": "SP500 moves inversely to rate hike, positively to rate cut",
            "btc_correlation": "BTC moves with SP500 direction",
        },
        invalidation_rules={
            "forward_guidance_contradicts": "dot plot and press conference tell opposite story",
            "market_already_priced": "no significant market move despite decision (fully priced in)",
            "press_conference_reverses": "Powell remarks reverse the initial rate decision signal",
        },
        expiration_rules={
            "intraday_expiry": "3 hours after release (including press conference)",
            "short_term_expiry": "48 hours after release",
            "medium_term_expiry": "until next FOMC meeting",
        },
        abstention_rules=[
            "rate_decision_time_unreliable",
            "dots_median_unavailable",
            "fomc_statement_unavailable",
            "press_conference_transcript_unavailable",
        ],
        transmission_paths=[
            "rate_decision -> fed_funds_rate_path -> yield_2y -> dollar -> risk_assets -> btc",
            "dot_plot_change -> terminal_rate_expectations -> long_end_yields -> equity_valuation -> btc",
            "press_conference_tone -> forward_guidance -> market_pricing_adjustment -> btc",
        ],
        alternative_explanations=[
            "market_was_focused_on_dots_not_the_rate_hike_itself",
            "dissenting_vote_signals_internal_division_weakens_signal",
            "press_conference_dominates_the_initial_statement_reaction",
        ],
        known_failure_modes=[
            "btc_mines_during_fomc_can_produce_anomalous_first_reaction",
            "btc_decouples_from_equities_during_fomc_as_correlation_breaks",
            "liquidity_trap_during_fomc_exaggerates_or_dampens_moves",
        ],
        confidence_representation="directional",
        calibration_required_for_probability=True,
    )
