"""Post-release reaction continuation strategy — exploratory pilot.
Evaluates whether the first 1h market reaction continues into 4h and 24h windows.
"""

from market_radar.intelligence.strategy_replay.contracts import StrategyDefinitionV1


def get_strategy_definition() -> StrategyDefinitionV1:
    return StrategyDefinitionV1(
        strategy_id="strat_post_release_reaction_continuation_v1",
        strategy_version="1.0.0",
        strategy_family="post_release_reaction_continuation",
        strategy_name="Post-Release Reaction Continuation V1",
        supported_event_families=["post_release_reaction_continuation"],
        supported_assets=["BTC", "ETH"],
        supported_horizons=["continuation_to_4h", "continuation_to_24h"],
        required_macro_fields=["signal_direction", "signal_return_pct", "signal_endpoint_time_utc"],
        required_market_fields=[],
        required_regime_fields=[],
        required_confirmation_fields=[],
        valid_regimes=[],
        invalid_regimes=[],
        trigger_rules={
            "signal_positive": "signal_direction == bullish",
            "signal_negative": "signal_direction == bearish",
        },
        confirmation_rules={},
        invalidation_rules={},
        expiration_rules={
            "continuation_to_4h": "4 hours after signal endpoint",
            "continuation_to_24h": "24 hours after signal endpoint",
        },
        abstention_rules=[
            "first_reaction_neutral",
            "signal_data_missing",
        ],
        transmission_paths=[
            "first_hour_reaction -> momentum -> continuation_to_4h",
            "first_hour_reaction -> trend -> continuation_to_24h",
        ],
        alternative_explanations=[
            "first_reaction_overreaction_reverses",
            "subsequent_macro_event_confounds_continuation",
        ],
        known_failure_modes=[
            "coarse_hourly_alignment_masks_precise_reversal_time",
            "small_pilot_sample_limits_generalizability",
        ],
        confidence_representation="exploratory",
        calibration_required_for_probability=True,
    )
