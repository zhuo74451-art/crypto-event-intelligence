"""Test batch replay with mock events."""
import sys, json
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.replay_engine import run_batch_replay
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


SAMPLE_EVENTS = [
    {"event_id": "cpi_2024_01", "event_family": "us_cpi", "initial_value": 3.4, "consensus_value": 3.2,
     "release_time_utc": "2024-01-11T13:30:00Z", "point_in_time_grade": "high"},
    {"event_id": "nfp_2024_01", "event_family": "us_nonfarm_payrolls", "initial_value": 216000, "consensus_value": 170000,
     "release_time_utc": "2024-01-05T13:30:00Z", "point_in_time_grade": "high"},
    {"event_id": "unemp_2024_01", "event_family": "us_unemployment_rate", "initial_value": 3.7, "consensus_value": 3.8,
     "release_time_utc": "2024-01-05T13:30:00Z", "point_in_time_grade": "high"},
    {"event_id": "core_pce_2024_01", "event_family": "us_core_pce", "initial_value": 2.9, "consensus_value": 3.0,
     "release_time_utc": "2024-01-26T13:30:00Z", "point_in_time_grade": "high"},
    {"event_id": "fomc_2024_01", "event_family": "us_fomc_rate_decision", "initial_value": 5.50, "consensus_value": 5.50,
     "release_time_utc": "2024-01-31T19:00:00Z", "point_in_time_grade": "high"},
]


def test_batch_replay():
    strategies = list(ALL_MACRO_STRATEGIES.values())
    consensus_map = {e["event_id"]: {"event_id": e["event_id"], "value": e["consensus_value"],
                                      "published_at_utc": "2024-01-01T00:00:00Z", "provider": "bloomberg"}
                     for e in SAMPLE_EVENTS}

    market_window_map = {e["event_id"]: {"btc_price_pre": 45000, "btc_price_post_1h": 45200}
                             for e in SAMPLE_EVENTS}
    cross_asset_map = {e["event_id"]: {"yield_2y_change": 0.005, "dxy_change": 0.003, "sp500_change": -0.005}
                       for e in SAMPLE_EVENTS}

    result = run_batch_replay(events=SAMPLE_EVENTS, strategies=strategies, consensus_map=consensus_map,
                               market_window_map=market_window_map, cross_asset_map=cross_asset_map)

    assert result["processed_count"] >= 4, f"Expected >=4 processed, got {result['processed_count']}"
    assert len(result["results"]) >= 4, f"Expected >=4 results, got {len(result['results'])}"
    assert len(result["hypotheses"]) >= 8, f"Expected >=8 hypotheses, got {len(result['hypotheses'])}"

    # Check no duplicate result IDs
    result_ids = [r.replay_result_id for r in result["results"]]
    assert len(result_ids) == len(set(result_ids)), "Duplicate result IDs found"

    print(f"  Processed: {result['processed_count']}")
    print(f"  Results: {len(result['results'])}")
    print(f"  Hypotheses: {len(result['hypotheses'])}")
    print(f"  Kernel packages: {len(result['kernel_packages'])}")
    print(f"  OK: Batch replay produces valid outputs")


def test_idempotent_replay():
    strategies = list(ALL_MACRO_STRATEGIES.values())
    consensus_map = {e["event_id"]: {"event_id": e["event_id"], "value": e["consensus_value"],
                                      "published_at_utc": "2024-01-01T00:00:00Z", "provider": "bloomberg"}
                     for e in SAMPLE_EVENTS}

    result1 = run_batch_replay(events=[SAMPLE_EVENTS[0]], strategies=strategies, consensus_map=consensus_map)
    result2 = run_batch_replay(events=[SAMPLE_EVENTS[0]], strategies=strategies, consensus_map=consensus_map)

    ids1 = [r.replay_result_id for r in result1["results"]]
    ids2 = [r.replay_result_id for r in result2["results"]]
    assert ids1 == ids2, f"Idempotency failed: {ids1} != {ids2}"
    print(f"  OK: Idempotent replay produces same IDs")


if __name__ == "__main__":
    test_batch_replay()
    test_idempotent_replay()
    print("\nAll batch replay tests passed!")
