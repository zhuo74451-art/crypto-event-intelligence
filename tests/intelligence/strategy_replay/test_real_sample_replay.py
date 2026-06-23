"""Test replay with real historical event samples (hardcoded)."""
import sys, json
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.replay_engine import run_event_replay
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


REAL_SAMPLES = [
    {"event_id": "cpi_2024_01_real", "event_family": "us_cpi",
     "initial_value": 3.4, "release_time_utc": "2024-01-11T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "cpi_2023_06_real", "event_family": "us_cpi",
     "initial_value": 3.0, "release_time_utc": "2023-06-13T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "nfp_2024_01_real", "event_family": "us_nonfarm_payrolls",
     "initial_value": 216000, "release_time_utc": "2024-01-05T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "fomc_2023_07_real", "event_family": "us_fomc_rate_decision",
     "initial_value": 5.50, "release_time_utc": "2023-07-26T18:00:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "fomc_2024_01_real", "event_family": "us_fomc_rate_decision",
     "initial_value": 5.50, "release_time_utc": "2024-01-31T19:00:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "core_pce_2024_01_real", "event_family": "us_core_pce",
     "initial_value": 2.8, "release_time_utc": "2024-02-29T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "unemp_2024_02_real", "event_family": "us_unemployment_rate",
     "initial_value": 3.9, "release_time_utc": "2024-02-02T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "cpi_2024_02_real", "event_family": "us_cpi",
     "initial_value": 3.2, "release_time_utc": "2024-02-13T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "nfp_2024_02_real", "event_family": "us_nonfarm_payrolls",
     "initial_value": 275000, "release_time_utc": "2024-03-08T13:30:00Z",
     "point_in_time_grade": "high"},
    {"event_id": "core_cpi_2024_01_real", "event_family": "us_core_cpi",
     "initial_value": 3.9, "release_time_utc": "2024-01-11T13:30:00Z",
     "point_in_time_grade": "high"},
]


def test_real_sample_replay():
    strategies = list(ALL_MACRO_STRATEGIES.values())
    total_results = 0
    total_hypotheses = 0
    abstention_count = 0

    for event in REAL_SAMPLES:
        consensus = {"event_id": event["event_id"], "value": event.get("initial_value", 0),
                      "published_at_utc": "2024-01-01T00:00:00Z", "provider": "bloomberg"}
        result = run_event_replay(
            event_record=event,
            consensus_record=consensus,
            market_window={"btc_price_pre": 45000, "btc_price_post_1h": 45200},
            strategy_definitions=strategies,
        )

        if "error" in result:
            print(f"  Error for {event['event_id']}: {result['error']}")
            continue

        total_results += len(result.get("results", []))
        total_hypotheses += len(result.get("hypotheses", []))
        abstention_count += len(result.get("abstentions", []))

    assert total_results >= 5, f"Expected >=5 results, got {total_results}"
    assert total_hypotheses >= 5, f"Expected >=5 hypotheses, got {total_hypotheses}"
    print(f"  Events: {len(REAL_SAMPLES)}")
    print(f"  Results: {total_results}")
    print(f"  Hypotheses: {total_hypotheses}")
    print(f"  Abstentions: {abstention_count}")
    print(f"  OK: Real sample replay produces valid outputs")


if __name__ == "__main__":
    test_real_sample_replay()
    print("\nAll real sample replay tests passed!")
